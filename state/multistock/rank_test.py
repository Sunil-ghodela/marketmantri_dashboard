"""Weekly momentum rank-filter paper test — 10 liquid stocks.

Har cycle (default 15 trading din) boundary ke close pe 10 names ko
momentum-stage score se rank karo, top-5 lo (equal weight), next open pe
enter, cycle end close pe exit. Compare:
  - top5 15-din cycle
  - top5 5-din cycle (weekly)
  - top3 15-din cycle
  - all-10 equal weight (same cycles)
  - NIFTY index benchmark (same dates)
Gross + net (0.12% per name per cycle = entry+exit cost estimate).

Score (v1 momentum-stage): stagePoints + SMA50/SMA200 + RSI band, tie-break
1-month return. Lookahead-free: sab kuch boundary ke close tak ka data hai,
entry = next open.

Outputs: rank_cycles.csv, rank_summary.json, rank_equity.png
"""
import os
import sys
import json
import math

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import build_state as bs   # noqa: E402
import scenario            # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PRICES = os.path.join(HERE, 'stocks_prices.csv')
NIFTY = os.path.join(os.path.dirname(HERE), 'nifty_daily_state.csv')
OUT_CSV = os.path.join(HERE, 'rank_cycles.csv')
OUT_JSON = os.path.join(HERE, 'rank_summary.json')
OUT_PNG = os.path.join(HERE, 'rank_equity.png')

STAGE_PTS = {'ALL-ALIGN BULL': 4, 'STRONG-FLOW': 4, 'EARLY-UP': 3,
             'CHOP-UP': 2, 'CHOP-MID': 1, 'CHOP-DOWN': -1,
             'TOP-WARNING': 0, 'WEAK': -2, 'BEAR': -2, 'PANIC': -2.5,
             'WARMUP': np.nan}
COST = 0.0012  # per name per cycle (entry+exit ~0.12%)
START = '2015-01-01'


def prep():
    raw = pd.read_csv(PRICES, parse_dates=['Date'])
    cols = {}
    for sym, g in raw.groupby('symbol'):
        df = g.sort_values('Date').reset_index(drop=True).copy()
        df = bs.add_indicators(df)
        scenario.assign_scenarios(df)
        d = df.set_index('Date')
        for c in ['Close', 'Open']:
            cols[(c, sym)] = d[c]
        pts = d['scenario'].map(STAGE_PTS)
        cols[('stage', sym)] = pts
        cols[('rsib', sym)] = np.where((d['rsi14'] >= 55) & (d['rsi14'] <= 72), 1.0,
                                np.where((d['rsi14'] >= 45) & (d['rsi14'] < 55), 0.5, 0.0))
        cols[('s50', sym)] = (d['Close'] > d['sma50']).astype(float)
        cols[('s200', sym)] = (d['Close'] > d['sma200']).astype(float)
        cols[('r21', sym)] = d['Close'] / d['Close'].shift(21) - 1
        cols[('r63', sym)] = d['Close'] / d['Close'].shift(63) - 1
        cols[('r126', sym)] = d['Close'] / d['Close'].shift(126) - 1
    syms = sorted(raw['symbol'].unique())
    W = pd.DataFrame(cols)
    W.index = pd.to_datetime(W.index)
    W = W.sort_index()
    W = W[W.index >= START]
    # sirf woh din jab saare names ke paas score ho
    m = pd.concat([W[('s200', s)] for s in syms], axis=1)
    ok = m.notna().all(axis=1) & W[('stage', syms[0])].notna()
    return W[ok], syms


def score_matrix(W, syms):
    """DataFrame(dates x syms) momentum-stage score."""
    sc = pd.DataFrame({s: W[('stage', s)] for s in syms})
    out = sc.copy()
    for s in syms:
        out[s] = (sc[s] + W[('s50', s)] + W[('s200', s)] + W[('rsib', s)]).fillna(-9)
    return out


def blend_frame(W, syms, h, w_ret, w_stage=0.0):
    """Rank-blended score: w_ret * percentile(h-day return) + w_stage * percentile(stage pts)."""
    ret = pd.DataFrame({s: W[('r%d' % h, s)] for s in syms})
    stg = pd.DataFrame({s: W[('stage', s)] for s in syms})
    pr = lambda x: x.rank(axis=1, pct=True).fillna(0.5)
    return (w_ret * pr(ret) + w_stage * pr(stg)).fillna(0.0)


def run_cycles(W, syms, hold, topn, name, cost=True, score=None):
    global score_vals
    if score is None:
        score = score_vals
    dates = list(W.index)
    n = len(dates)
    cycles = []
    equity = [1.0]
    i0 = 0
    while i0 + hold < n:
        b0, b1 = i0, i0 + hold
        d0 = dates[b0]
        # rank at close d0
        row = score.loc[d0]
        order = row.sort_values(ascending=False)
        picks = list(order.index[:topn])
        # entry open b0+1 .. exit close b1
        rets = {}
        for s in syms:
            o = W[('Open', s)].iloc[b0 + 1]
            c = W[('Close', s)].iloc[b1]
            rets[s] = c / o - 1 if (o and o == o and o > 0) else np.nan
        gross = float(np.nanmean([rets[s] for s in picks]))
        all10 = float(np.nanmean([rets[s] for s in syms]))
        fee = COST * topn if cost else 0.0
        cycles.append({'cycle': len(cycles) + 1, 'start': d0.date().isoformat(),
                       'end': dates[b1].date().isoformat(),
                       'picks': '+'.join(picks),
                       'gross': round(gross * 100, 2),
                       'net': round((gross - fee) * 100, 2),
                       'all10': round(all10 * 100, 2),
                       'n_picks': topn})
        equity.append(equity[-1] * (1 + gross - fee))
        i0 = b1
    # last open cycle
    if i0 < n - 1:
        d0 = dates[i0]
        row = score_vals.loc[d0]
        picks = list(row.sort_values(ascending=False).index[:topn])
        cycles.append({'cycle': len(cycles) + 1, 'start': d0.date().isoformat(),
                       'end': dates[-1].date().isoformat(), 'picks': '+'.join(picks),
                       'gross': None, 'net': None, 'all10': None, 'n_picks': topn,
                       'open': True})
    eq = pd.Series(equity)
    ret = pd.DataFrame(cycles)
    yrs = (ret['end'].str.slice(0, 4) if not ret.empty else pd.Series(dtype=str))
    return {'name': name, 'cycles': ret, 'equity': eq, 'picks_last': picks}


def stats(res, W):
    cy = res['cycles']
    closed = cy[cy['gross'].notna()]
    eq = res['equity']
    total = eq.iloc[-1] - 1
    n = len(eq) - 1
    # cycle length in years approx via date span
    span_d = (pd.to_datetime(cy['end'].iloc[-1]) - pd.to_datetime(cy['start'].iloc[0])).days / 365.25
    cagr = (eq.iloc[-1] ** (1 / max(span_d, 0.1))) - 1 if eq.iloc[-1] > 0 else -1
    dd = float((eq / eq.cummax() - 1).min())
    return {'name': res['name'], 'total': round(100 * total, 1), 'cagr': round(100 * cagr, 1),
            'mdd': round(100 * dd, 1), 'cycles': len(closed),
            'span_years': round(span_d, 1),
            'win': round(100 * (closed['net'] > 0).mean(), 0) if len(closed) else None,
            'avg_net': round(closed['net'].mean(), 2) if len(closed) else None,
            'avg_gross': round(closed['gross'].mean(), 2) if len(closed) else None,
            'worst_cycle': round(closed['net'].min(), 1) if len(closed) else None,
            'last_picks': res['picks_last']}


def nifty_bench(W):
    nf = pd.read_csv(NIFTY, parse_dates=['Date']).set_index('Date')['Close']
    nf = nf.reindex(W.index).ffill()
    return nf


def main():
    global score_vals
    W, syms = prep()
    score_vals = score_matrix(W, syms)

    res15 = run_cycles(W, syms, 15, 5, 'TOP5 · 15-din hold')
    res5 = run_cycles(W, syms, 5, 5, 'TOP5 · weekly (5-din)')
    res3 = run_cycles(W, syms, 15, 3, 'TOP3 · 15-din hold')
    res10 = run_cycles(W, syms, 15, 10, 'ALL-10 · 15-din')
    res_m63 = run_cycles(W, syms, 21, 5, 'TOP5 · 1mo hold, 3mo-mom mix',
                         score=blend_frame(W, syms, 63, 0.6, 0.4))
    res_m126 = run_cycles(W, syms, 21, 5, 'TOP5 · 1mo hold, 6mo-mom mix',
                          score=blend_frame(W, syms, 126, 0.6, 0.4))
    res_pure = run_cycles(W, syms, 21, 5, 'TOP5 · 1mo hold, pure 3mo-mom',
                          score=blend_frame(W, syms, 63, 1.0, 0.0))
    nf = nifty_bench(W)
    # index cycle-aligned: same boundaries as 15d
    nf_cycles = []
    eq = [1.0]
    dates = list(W.index)
    i0 = 0
    while i0 + 15 < len(dates):
        r = nf.iloc[i0 + 15] / nf.iloc[i0 + 1] - 1
        nf_cycles.append(r)
        eq.append(eq[-1] * (1 + r))
        i0 += 15
    nf_res = {'name': 'NIFTY index (benchmark)', 'cycles': pd.DataFrame({
        'gross': [round(100 * x, 2) for x in nf_cycles]}),
        'equity': pd.Series(eq), 'picks_last': []}

    print('%-24s %7s %6s %7s %5s %6s %8s %7s' % ('strategy', 'total', 'CAGR', 'MDD', 'win', 'avgnet', 'worst', 'cycles'))
    summary = []
    for r in (res15, res5, res3, res10, res_m63, res_m126, res_pure):
        s = stats(r, W)
        summary.append(s)
        print('%-32s %+6.1f%% %5.1f%% %6.1f%% %4.0f%% %+6.2f  %+6.1f  %5d' % (
            s['name'], s['total'], s['cagr'], s['mdd'], s['win'] if s['win'] is not None else 0,
            s['avg_net'], s['worst_cycle'], s['cycles']))
    # NIFTY
    tot = (nf_res['equity'].iloc[-1] - 1)
    span = (W.index[-1] - W.index[0]).days / 365.25
    print('%-24s %+6.1f%% %5.1f%%  (same period buy-hold)' % ('NIFTY index (benchmark)', 100 * tot,
         100 * (nf_res['equity'].iloc[-1] ** (1 / span) - 1)))

    # yearly table for TOP5-15d net
    cy = res15['cycles'].copy()
    cy['year'] = pd.to_datetime(cy['end']).dt.year
    y = cy[cy['net'].notna()].groupby('year')['net'].agg(['count', 'sum', 'mean'])
    print('\nTOP5-15d yearly (net %):')
    print(y.round(1).to_string())

    # latest picks (direction)
    print('\nAaj (4 Sep 2026) ka rank order:')
    row = score_vals.iloc[-1].sort_values(ascending=False)
    for s, v in row.items():
        stg = W[('stage', s)].iloc[-1]
        print(f'  {s:<11} score {v:+.1f}  stage {stg}')

    # chart
    fig, ax = plt.subplots(figsize=(11, 6.5))
    ax.set_facecolor('#0f172a'); fig.patch.set_facecolor('#0f172a')
    colors = {'TOP5 · 15-din hold': '#22c55e', 'TOP5 · weekly (5-din)': '#38bdf8',
              'TOP3 · 15-din hold': '#eab308', 'ALL-10 · 15-din': '#94a3b8',
              'TOP5 · 1mo hold, 3mo-mom mix': '#a3e635',
              'TOP5 · 1mo hold, 6mo-mom mix': '#f472b6',
              'TOP5 · 1mo hold, pure 3mo-mom': '#facc15',
              'NIFTY index (benchmark)': '#ef4444'}
    for r in (res15, res5, res3, res10, res_m63, res_m126, res_pure):
        e = r['equity']
        ax.plot(range(len(e)), e * 100, lw=2, label=r['name'], color=colors[r['name']])
    eqn = nf_res['equity']
    ax.plot(range(len(eqn)), eqn * 100, lw=1.6, ls='--', color=colors['NIFTY index (benchmark)'],
            label='NIFTY index (benchmark)')
    ax.set_title('10 liquid stocks — momentum rank filter (stage-score, top-5, 15-din hold)',
                 color='#f8fafc', fontsize=13, fontweight='bold')
    ax.set_ylabel('Equity (₹100 start, %)', color='#94a3b8', fontsize=10)
    ax.legend(facecolor='#0f172a', edgecolor='#334155', labelcolor='#e2e8f0', fontsize=9)
    ax.grid(alpha=0.2, color='#334155')
    for sp in ['top', 'right']:
        ax.spines[sp].set_visible(False)
    ax.tick_params(colors='#94a3b8')
    fig.text(0.99, 0.01, 'Net of 0.12%/name/cycle · 2015-2026 · in-sample (context, proof nahi) · Yahoo .NS',
             color='#64748b', fontsize=8.5, ha='right')
    plt.savefig(OUT_PNG, dpi=130, bbox_inches='tight', facecolor='#0f172a')
    plt.close(fig)
    res15['cycles'].to_csv(OUT_CSV, index=False)
    meta = {'top5_15d': summary[0], 'top5_weekly': summary[1], 'top3_15d': summary[2],
            'all10': summary[3], 'm63_1mo': summary[4], 'm126_1mo': summary[5],
            'pure3mo_1mo': summary[6], 'nifty_total_pct': round(100 * tot, 1),
            'latest_rank': {s: {'score': round(float(v), 1),
                                'stage': str(W[('stage', s)].iloc[-1])}
                            for s, v in row.items()}}
    json.dump(meta, open(OUT_JSON, 'w'), indent=1, default=str)
    print('\nsaved ->', OUT_CSV, OUT_JSON, OUT_PNG)


if __name__ == '__main__':
    main()
