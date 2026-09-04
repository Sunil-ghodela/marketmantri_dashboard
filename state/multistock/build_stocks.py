"""10 liquid stocks pe NIFTY stage pipeline test — direction ke liye.

Har stock pe: indicators (add_indicators) + stage/action labels (scenario) +
entry tiers (T1 fresh-trend / T2 re-accel). Phir basket level pe:
  1. per-stock stage distribution + latest state
  2. quality signal cadence (union across 10 names) — month distribution
  3. T1/T2 signal ka mini-engine outcome (entry next open, hold jab tak
     bull-family, stop 2xATR, max 15 din) — kya direction milta hai

Outputs: state/multistock/stocks_state_latest.csv
         state/multistock/stocks_signals_all.csv
"""
import os
import sys
import json

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import build_state as bs   # noqa: E402  (add_indicators reuse)
import scenario            # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PRICES = os.path.join(HERE, 'stocks_prices.csv')
OUT_LATEST = os.path.join(HERE, 'stocks_state_latest.csv')
OUT_SIGNALS = os.path.join(HERE, 'stocks_signals_all.csv')

FAMILY = {'EARLY-UP', 'ALL-ALIGN BULL', 'STRONG-FLOW', 'TOP-WARNING'}
MAX_HOLD = 15


def analyze_stock(sym, g):
    df = g.sort_values('Date').reset_index(drop=True).copy()
    df = bs.add_indicators(df)
    scenario.assign_scenarios(df)
    valid = df['scenario'] != 'WARMUP'

    # tier signal days (index positions)
    t1 = scenario.run_first(df['regime'] == 'TREND UP') & valid
    t2 = (scenario.run_first(df['scenario'].isin(scenario.BUY_STAGES) &
                             df['scenario'].shift(1).eq('EARLY-UP')) & valid)
    sig = t1 | t2
    sig_idx = np.flatnonzero(sig.to_numpy())

    # per-signal mini engine (v1 rules)
    recs = []
    cl = df['Close'].to_numpy(float)
    op = df['Open'].to_numpy(float)
    atr = df['atr14'].to_numpy(float)
    scen = df['scenario'].to_numpy()
    n = len(df)
    for i in sig_idx:
        if i + 1 >= n:
            continue
        entry = op[i + 1]
        if not np.isfinite(entry) or entry <= 0:
            continue
        stop = entry - 2.0 * (atr[i] if np.isfinite(atr[i]) else np.nan)
        exit_px, exit_day, why = None, None, 'time'
        for j in range(i + 1, min(i + 1 + MAX_HOLD, n)):
            if j == i + MAX_HOLD:                      # time exit (15 din)
                exit_px, exit_day, why = cl[j], j, 'time'
                break
            if scen[j] not in FAMILY:
                exit_px, exit_day, why = cl[j], j, 'stage'
                break
            if np.isfinite(stop) and cl[j] <= stop:
                exit_px, exit_day, why = cl[j], j, 'stop'
                break
        if exit_px is None:                            # data-end: abhi open hai
            exit_px, exit_day, why = cl[n - 1], n - 1, 'open'
        pnl = 100.0 * (exit_px / entry - 1)
        recs.append({
            'symbol': sym, 'signal_date': df['Date'].iloc[i].date().isoformat(),
            'tier': 'T1' if t1.iloc[i] else 'T2',
            'entry_date': df['Date'].iloc[i + 1].date().isoformat(),
            'entry_px': round(float(entry), 2),
            'exit_px': round(float(exit_px), 2),
            'exit_date': df['Date'].iloc[exit_day].date().isoformat() if exit_day is not None else '',
            'exit': why, 'hold_days': int(exit_day - i) if exit_day is not None else None,
            'pnl_pct': round(pnl, 2), 'open': why == 'open',
            'stage_at_signal': df['scenario'].iloc[i],
            'rsi_at_signal': round(float(df['rsi14'].iloc[i]), 1),
        })
    latest = df.iloc[-1]
    st = scenario.stage_stats(df)
    return {
        'symbol': sym, 'df': df, 'signals': recs,
        'stats': st,
        'latest': {'date': latest['Date'].date().isoformat(),
                   'close': round(float(latest['Close']), 1),
                   'regime': latest['regime'], 'stage': latest['scenario'],
                   'action': latest['action'], 'rsi': round(float(latest['rsi14']), 0),
                   'macd': round(float(latest['macd_hist']), 0),
                   'sma200': round(float(latest['sma200']), 1) if pd.notna(latest['sma200']) else None,
                   'off_ath': round(float(latest['off_ath_pct']), 1)},
    }


def main():
    raw = pd.read_csv(PRICES, parse_dates=['Date'])
    out = []
    for sym, g in raw.groupby('symbol'):
        r = analyze_stock(sym, g)
        out.append(r)
        print(f"\n=== {sym} ===")
        lx = r['latest']
        print(f"latest {lx['date']}: {lx['stage']} ({lx['action']}) regime {lx['regime']} RSI {lx['rsi']} "
              f"close {lx['close']} off_ath {lx['off_ath']}%")
        share = r['stats']['share']
        top = sorted(share, key=lambda s: -s['pct'])[:3]
        print('  top stages: ' + ', '.join(f"{s['stage']} {s['pct']}%" for s in top))
        t = {x['tier']: x for x in r['stats']['tiers']}
        print(f"  T1 {t['T1 fresh-trend']['n']}x  T2 {t['T2 re-accel after pullback']['n']}x  "
              f"T3 {t['T3 chop-trigger (no-edge)']['n']}x  quality/yr {r['stats']['quality_per_year']}")
    # basket cadence (union dates)
    sigdf = pd.DataFrame([s for r in out for s in r['signals']])
    sigdf.to_csv(OUT_SIGNALS, index=False)
    lat = pd.DataFrame([r['latest'] | {'symbol': r['symbol']} for r in out])
    lat.to_csv(OUT_LATEST, index=False)

    sigdf['signal_date'] = pd.to_datetime(sigdf['signal_date'])
    months = sigdf['signal_date'].dt.to_period('M')
    per_month = months.value_counts().sort_index()
    all_mo = pd.period_range('2015-01', '2026-09', freq='M')
    cnt = per_month.reindex(all_mo, fill_value=0)
    print('\n===== BASKET (10 names) — quality signal cadence =====')
    print(f"total signals: {len(sigdf)} over {len(all_mo)} months")
    print(f"avg per month: {cnt.mean():.2f}  | median {cnt.median():.0f}  | max {cnt.max()} ({cnt.idxmax()})")
    dist = cnt.value_counts().sort_index()
    for k, v in dist.items():
        print(f'  {int(k)}/month: {v} months ({100*v/len(all_mo):.0f}%)')
    print(f"months with >=1: {(cnt>0).sum()} ({100*(cnt>0).mean():.0f}%)  | "
          f"months with >=2: {(cnt>=2).sum()} ({100*(cnt>=2).mean():.0f}%)")

    print('\n===== MINI-ENGINE OUTCOME (T1/T2 signals, entry next open) =====')
    done = sigdf[~sigdf['open']]
    print(f'signals: {len(sigdf)}  closed {len(done)}  still-open {len(sigdf)-len(done)}')
    for tier, sub in sigdf.groupby('tier'):
        d = sub[~sub['open']]
        if len(d):
            print(f'  {tier}: n={len(d)} win {100*(d.pnl_pct>0).mean():.0f}%  avg {d.pnl_pct.mean():+.2f}%  '
                  f'avg hold {d.hold_days.mean():.0f}d  per-year ~{len(sub)/11.7:.1f}')
    d = done
    if len(d):
        print(f'  ALL closed: n={len(d)} win {100*(d.pnl_pct>0).mean():.0f}%  avg {d.pnl_pct.mean():+.2f}%  '
              f'median {d.pnl_pct.median():+.2f}%  avg hold {d.hold_days.mean():.0f}d')
        print('  by exit:', d.groupby('exit')['pnl_pct'].agg(['count', 'mean']).round(2).to_dict('index'))
        print('  yearly:')
        y = d.copy(); y['year'] = pd.to_datetime(y['signal_date']).dt.year
        print(y.groupby('year')['pnl_pct'].agg(['count', 'mean']).round(2).to_string())
    print('\nlatest state per stock (direction):')
    print(lat[['symbol', 'stage', 'action', 'regime', 'rsi', 'close']].to_string(index=False))
    nbuy = (lat['action'] == 'BUY').sum()
    print(f"\nBREADTH: {nbuy}/10 BUY zone · watch/hold: {((lat['action'].isin(['WATCH','HOLD'])).sum())} "
          f"· stand/avoid: {(~lat['action'].isin(['BUY','WATCH','HOLD'])).sum()}")
    meta = {'tested': '10 liquid NSE stocks', 'n_signals': int(len(sigdf)),
            'avg_month': round(float(cnt.mean()), 2),
            'months_ge1_pct': round(100 * float((cnt > 0).mean()), 1),
            'months_ge2_pct': round(100 * float((cnt >= 2).mean()), 1)}
    with open(os.path.join(HERE, 'basket_test_summary.json'), 'w') as f:
        json.dump(meta, f)
    print('\nsaved ->', OUT_SIGNALS, OUT_LATEST)


if __name__ == '__main__':
    main()
