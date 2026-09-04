"""
NIFTY State Pipeline — builds everything the dashboard needs.

Input : state/nifty_prices.csv   (daily OHLC; bootstrapped from the 4,200-day
         xlsx on first run, then extended by update_prices.py from Yahoo)
Output: state/nifty_daily_state.csv   per-day state (daily analysis)
        state/nifty_weekly.csv        per-week summary (weekly analysis)
        state/nifty_monthly.csv       per-month summary (monthly analysis)
        state/nifty_state_data.json   compact data the dashboard renders
        state/nifty_daily_map.png     master 11-yr map
        state/nifty_today_zoom.png    last-6-month zoom
"""
import os
import json
import math
import openpyxl
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Patch, FancyArrowPatch
from matplotlib.lines import Line2D
import scenario

HERE = os.path.dirname(os.path.abspath(__file__))
XLSX = '/home/vaibhav/AI/yr2026/dilvergence/data/Nifty-4200-Days-2015-2026-Full.xlsx'
PRICES = os.path.join(HERE, 'nifty_prices.csv')
OUT_DAILY = os.path.join(HERE, 'nifty_daily_state.csv')
OUT_WEEKLY = os.path.join(HERE, 'nifty_weekly.csv')
OUT_MONTHLY = os.path.join(HERE, 'nifty_monthly.csv')
OUT_JSON = os.path.join(HERE, 'nifty_state_data.json')
OUT_MAP = os.path.join(HERE, 'nifty_daily_map.png')
OUT_ZOOM = os.path.join(HERE, 'nifty_today_zoom.png')
OUT_CYCLE = os.path.join(HERE, 'nifty_state_cycle.png')
NEWS = os.path.join(HERE, 'news_events.csv')

REGIME_CODES = {'TREND UP': 0, 'TREND DOWN': 1, 'RANGE': 2, 'CHOP': 3}


# ---------------------------------------------------------------- data load
def load_prices():
    if os.path.exists(PRICES):
        df = pd.read_csv(PRICES)
        df['Date'] = pd.to_datetime(df['Date'])
        df['Event'] = df.get('Event', pd.Series('', index=df.index)).fillna('')
        return df.sort_values('Date').reset_index(drop=True)

    print('bootstrap: reading xlsx ->', XLSX)
    wb = openpyxl.load_workbook(XLSX, read_only=True)
    ws = wb['Sheet1']
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    wb.close()
    df = pd.DataFrame(rows).iloc[:, :7]
    df.columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Event', 'Category']
    df['Date'] = pd.to_datetime(df['Date'])
    for c in ['Open', 'High', 'Low', 'Close']:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    df = df.dropna(subset=['Close']).sort_values('Date').reset_index(drop=True)
    df['Event'] = df['Event'].fillna('')
    df['Category'] = df['Category'].fillna('')
    df.to_csv(PRICES, index=False)
    print('prices saved ->', PRICES)
    return df


# ---------------------------------------------------------------- indicators
def wilder(s, n):
    return s.ewm(alpha=1.0 / n, adjust=False).mean()


def add_indicators(df):
    h, l, c = df['High'], df['Low'], df['Close']

    df['sma50'] = c.rolling(50).mean()
    df['sma200'] = c.rolling(200).mean()

    macd = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    signal = macd.ewm(span=9, adjust=False).mean()
    df['macd'] = macd
    df['signal'] = signal
    df['macd_hist'] = macd - signal

    delta = c.diff()
    up = delta.clip(lower=0)
    dn = -delta.clip(upper=0)
    rs = wilder(up, 14) / wilder(dn, 14)
    df['rsi14'] = 100 - 100 / (1 + rs)

    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    df['atr14'] = wilder(tr, 14)

    n = 14
    hh = h.rolling(n).max()
    ll = l.rolling(n).min()
    df['chop14'] = 100 * np.log10(tr.rolling(n).sum() / (hh - ll)) / np.log10(n)

    plus_dm = pd.Series(np.where((h.diff() > -l.diff()) & (h.diff() > 0), h.diff(), 0.0), index=df.index)
    minus_dm = pd.Series(np.where((-l.diff() > h.diff()) & (-l.diff() > 0), -l.diff(), 0.0), index=df.index)
    di_p = 100 * wilder(plus_dm, 14) / df['atr14']
    di_m = 100 * wilder(minus_dm, 14) / df['atr14']
    dx = 100 * (di_p - di_m).abs() / (di_p + di_m).replace(0, np.nan)
    df['adx14'] = wilder(dx.fillna(0), 14)
    df['di_plus'] = di_p
    df['di_minus'] = di_m

    def classify(row):
        if pd.notna(row['adx14']) and row['adx14'] >= 25:
            return 'TREND UP' if row['di_plus'] >= row['di_minus'] else 'TREND DOWN'
        if pd.notna(row['chop14']) and row['chop14'] >= 55:
            return 'CHOP'
        return 'RANGE'
    df['regime'] = df.apply(classify, axis=1)

    hist_sign = np.sign(df['macd_hist'].fillna(0))
    df['macd_cross'] = ''
    df.loc[(hist_sign > 0) & (hist_sign.shift(1) <= 0), 'macd_cross'] = 'CROSS_UP'
    df.loc[(hist_sign < 0) & (hist_sign.shift(1) >= 0), 'macd_cross'] = 'CROSS_DOWN'

    df['rsi_zone'] = np.where(df['rsi14'] >= 70, 'OVERBOUGHT',
                     np.where(df['rsi14'] <= 30, 'OVERSOLD', 'NEUTRAL'))

    # RSI pivot divergence
    cl = c.values
    rv = df['rsi14'].values
    W = 5
    hi_piv = [i for i in range(W, len(df) - W) if cl[i] == max(cl[i - W:i + W + 1])]
    lo_piv = [i for i in range(W, len(df) - W) if cl[i] == min(cl[i - W:i + W + 1])]
    div_idx = np.zeros(len(df), dtype=int)
    for a, b in zip(hi_piv, hi_piv[1:]):
        if b - a >= 8 and cl[b] > cl[a] and rv[b] < rv[a]:
            div_idx[b] = -1
    for a, b in zip(lo_piv, lo_piv[1:]):
        if b - a >= 8 and cl[b] < cl[a] and rv[b] > rv[a]:
            div_idx[b] = 1
    df['div'] = pd.Series(div_idx, index=df.index).map({1: 'BULL_DIV', -1: 'BEAR_DIV', 0: ''})

    # moves
    year_last = df.groupby(df['Date'].dt.year)['Close'].last()
    prev_year_last = year_last.shift(1)
    df['month_so_far_pct'] = df.groupby(df['Date'].dt.to_period('M'))['Close'].transform(
        lambda s: 100 * (s / s.iloc[0] - 1))
    df['ytd_pct'] = df.apply(
        lambda r: 100 * (r['Close'] / prev_year_last.get(r['Date'].year, np.nan) - 1)
        if r['Date'].year in prev_year_last.index else np.nan, axis=1)
    df['ret_1y_pct'] = 100 * (c / c.shift(252) - 1)
    df['off_ath_pct'] = 100 * (c / c.cummax() - 1)
    df['daily_ret'] = 100 * c.pct_change()
    return df


# ---------------------------------------------------------------- analysis
def fwd_return(df, i, days):
    j = i + days
    if j >= len(df):
        return np.nan
    return 100 * (df.iloc[j]['Close'] / df.iloc[i]['Close'] - 1)


def compute_analysis(df):
    A = {}
    n = len(df)

    # regime share
    vc = df['regime'].value_counts()
    A['regime_share'] = {k: round(100.0 * vc.get(k, 0) / n, 1)
                         for k in ['TREND UP', 'TREND DOWN', 'RANGE', 'CHOP']}

    # streaks
    runs = {k: [] for k in ['TREND UP', 'TREND DOWN', 'RANGE', 'CHOP']}
    prev = None
    length = 0
    for r in df['regime']:
        if r == prev:
            length += 1
        else:
            if prev is not None:
                runs[prev].append(length)
            prev = r
            length = 1
    runs[prev].append(length)
    A['streaks'] = {k: {'n': len(v), 'avg': round(float(np.mean(v)), 1),
                        'max': int(max(v))} for k, v in runs.items()}

    # month seasonality (calendar months)
    mrets = {}
    for m in range(1, 13):
        sub = df[df['Date'].dt.month == m]
        if len(sub) == 0:
            continue
        firsts = sub.groupby(sub['Date'].dt.year)['Close'].first()
        lasts = sub.groupby(sub['Date'].dt.year)['Close'].last()
        rets = 100 * (lasts / firsts - 1)
        share = {k: round(100.0 * (sub['regime'] == k).mean(), 1)
                 for k in ['TREND UP', 'TREND DOWN', 'RANGE', 'CHOP']}
        mrets[m] = {'share': share, 'avg_ret': round(float(rets.mean()), 2),
                    'pct_green': round(100.0 * (rets > 0).mean(), 0)}
    A['month_season'] = {f'{m:02d}': mrets[m] for m in sorted(mrets)}

    # transition matrix (today -> tomorrow)
    tm = {k: {k2: 0 for k2 in ['TREND UP', 'TREND DOWN', 'RANGE', 'CHOP']}
          for k in ['TREND UP', 'TREND DOWN', 'RANGE', 'CHOP']}
    cnt = {k: 0 for k in tm}
    for i in range(1, n):
        f, t = df.iloc[i - 1]['regime'], df.iloc[i]['regime']
        tm[f][t] += 1
        cnt[f] += 1
    A['transitions'] = {k: {k2: round(100.0 * tm[k][k2] / max(cnt[k], 1), 1)
                            for k2 in tm[k]} for k in tm}

    # CHOP streak >= 10 days -> what next
    chop_runs = []
    i = 0
    while i < n:
        if df.iloc[i]['regime'] == 'CHOP':
            j = i
            while j + 1 < n and df.iloc[j + 1]['regime'] == 'CHOP':
                j += 1
            if j - i + 1 >= 10:
                chop_runs.append(j)  # end index of run
            i = j + 1
        else:
            i += 1
    if chop_runs:
        nxt = []
        for end in chop_runs:
            if end + 5 < n:
                r5 = df.iloc[end + 5]['regime']
                nxt.append(1 if r5 in ('TREND UP', 'TREND DOWN') else 0)
            if end + 10 < n:
                fr = fwd_return(df, end, 10)
                if not np.isnan(fr):
                    nxt.append(fr)
        trend_in5 = round(100.0 * sum(nxt[:len(chop_runs)]) / max(len(chop_runs), 1), 1)
        f10 = [v for v in nxt[len(chop_runs):] if not isinstance(v, int)]
        A['chop_to_trend'] = {'runs_ge_10d': len(chop_runs),
                              'trend_within_5d_pct': trend_in5,
                              'avg_10d_fwd': round(float(np.mean(f10)), 2) if f10 else None,
                              'win_10d_pct': round(100.0 * np.mean(np.array(f10) > 0), 0) if f10 else None}
    else:
        A['chop_to_trend'] = {'runs_ge_10d': 0}

    # MACD cross quality by regime at cross day
    cq = []
    for kind in ['CROSS_UP', 'CROSS_DOWN']:
        rows = df[df['macd_cross'] == kind]
        for reg in ['TREND UP', 'TREND DOWN', 'RANGE', 'CHOP']:
            sub = rows[rows['regime'] == reg]
            f5 = []
            for i in sub.index:
                v = fwd_return(df, i, 5)
                if not np.isnan(v):
                    f5.append(v)
            if f5:
                cq.append({'kind': kind, 'regime': reg, 'n': len(f5),
                           'avg_5d': round(float(np.mean(f5)), 2),
                           'win': round(100.0 * np.mean(np.array(f5) > 0), 0)})
    A['cross_quality'] = cq

    # divergence quality (10d forward)
    dq = {}
    for kind, code in [('BULL_DIV', 1), ('BEAR_DIV', -1)]:
        f10 = []
        for i in df[df['div'] == kind].index:
            v = fwd_return(df, i, 10)
            if not np.isnan(v):
                f10.append(v)
        if f10:
            dq[kind] = {'n': len(f10), 'avg_10d': round(float(np.mean(f10)), 2),
                        'win': round(100.0 * np.mean(np.array(f10) > 0), 0)}
    A['div_quality'] = dq

    # daily return by regime
    dr = {}
    for reg in ['TREND UP', 'TREND DOWN', 'RANGE', 'CHOP']:
        sub = df[df['regime'] == reg]['daily_ret'].dropna()
        if len(sub):
            dr[reg] = {'n': len(sub), 'avg': round(float(sub.mean()), 3),
                       'std': round(float(sub.std()), 2),
                       'win': round(100.0 * (sub > 0).mean(), 0)}
    A['daily_ret_by_regime'] = dr

    # yearly
    yr = []
    for y, g in df.groupby(df['Date'].dt.year):
        first = g.iloc[0]['Close']
        last = g.iloc[-1]['Close']
        yr.append({'year': int(y), 'ret': round(100 * (last / first - 1), 1),
                   'regime_mix': {k: round(100.0 * (g['regime'] == k).mean(), 0)
                                  for k in ['TREND UP', 'TREND DOWN', 'RANGE', 'CHOP']}})
    A['yearly'] = yr

    # last 12 calendar months
    lm = []
    months = list(df['Date'].dt.to_period('M').unique())[-12:]
    for p in months:
        sub = df[df['Date'].dt.to_period('M') == p]
        ret = 100 * (sub.iloc[-1]['Close'] / sub.iloc[0]['Close'] - 1)
        lm.append({'month': str(p), 'ret': round(ret, 2),
                   'close': round(sub.iloc[-1]['Close'], 1),
                   'regime_mode': sub['regime'].value_counts().idxmax(),
                   'macd_end': round(sub.iloc[-1]['macd_hist'], 0)})
    A['last12m'] = lm

    # last 8 ISO weeks
    lw = []
    wk = df.groupby(df['Date'].dt.to_period('W'))
    for p, sub in list(wk)[-8:]:
        ret = 100 * (sub.iloc[-1]['Close'] / sub.iloc[0]['Close'] - 1)
        lw.append({'week': str(p), 'ret': round(ret, 2),
                   'close': round(sub.iloc[-1]['Close'], 1),
                   'regime_mode': sub['regime'].value_counts().idxmax()})
    A['last8w'] = lw

    # stage map (scenario/action labels har din) + cadence
    A['stages'] = scenario.stage_stats(df)
    A['stage_meta'] = [scenario.META[k] for k in scenario.META]

    return A


# ---------------------------------------------------------------- news events

def fix(o):
    """Make JSON-safe (NaN/Inf -> None)."""
    if isinstance(o, dict):
        return {k: fix(v) for k, v in o.items()}
    if isinstance(o, list):
        return [fix(v) for v in o]
    if isinstance(o, float):
        if math.isnan(o) or math.isinf(o):
            return None
        return o
    return o


def load_news():
    if not os.path.exists(NEWS):
        return pd.DataFrame(columns=['Date', 'Driver', 'Category', 'Title', 'Impact', 'Note'])
    n = pd.read_csv(NEWS)
    n['Date'] = pd.to_datetime(n['Date'])
    for c in ['Driver', 'Category', 'Title', 'Impact', 'Note']:
        n[c] = n[c].fillna('').astype(str)
    return n


def compute_events(df, news):
    """For every news event: technical snapshot on the next trading day + forward returns."""
    dts = df['Date'].reset_index(drop=True)
    items = []
    for _, e in news.iterrows():
        i = int(dts.searchsorted(e['Date']))
        if i >= len(df):
            continue
        r = df.iloc[i]
        day_pct = None
        if i > 0:
            day_pct = round(100 * (r['Close'] / df.iloc[i - 1]['Close'] - 1), 2)
        fw = {}
        for k in (1, 5, 20, 60):
            v = fwd_return(df, i, k)
            fw[f'fwd{k}'] = None if v is None or np.isnan(v) else round(v, 2)
        items.append({
            'date': e['Date'].strftime('%Y-%m-%d'),
            'tdate': r['Date'].strftime('%Y-%m-%d'),
            'driver': e['Driver'], 'category': e['Category'],
            'title': e['Title'], 'impact': e['Impact'], 'note': e['Note'],
            'day_pct': day_pct,
            'fwd1': fw['fwd1'], 'fwd5': fw['fwd5'],
            'fwd20': fw['fwd20'], 'fwd60': fw['fwd60'],
            'regime': r['regime'], 'adx': round(r['adx14'], 0),
            'chop': round(r['chop14'], 0), 'macd_hist': round(r['macd_hist'], 0),
            'rsi': round(r['rsi14'], 0), 'close': round(r['Close'], 1),
        })

    drivers = {}
    for drv in sorted({x['driver'] for x in items}):
        sub = [x for x in items if x['driver'] == drv]
        dp = [x['day_pct'] for x in sub if x['day_pct'] is not None]
        f5 = [x['fwd5'] for x in sub if x['fwd5'] is not None]
        f20 = [x['fwd20'] for x in sub if x['fwd20'] is not None]
        drivers[drv] = {
            'n': len(sub),
            'avg_day': round(float(np.mean(dp)), 2) if dp else None,
            'avg_fwd5': round(float(np.mean(f5)), 2) if f5 else None,
            'avg_fwd20': round(float(np.mean(f20)), 2) if f20 else None,
            'win_fwd20': round(100 * float(np.mean(np.array(f20) > 0)), 0) if f20 else None,
        }
    return {'list': items, 'drivers': drivers}


# ---------------------------------------------------------------- charts
BG = '#0f172a'
PANEL = '#0f172a'
FG = '#e2e8f0'
MUT = '#94a3b8'
GRID = '#334155'
REG_COLORS = {'TREND UP': '#16a34a', 'TREND DOWN': '#dc2626',
              'RANGE': '#2563eb', 'CHOP': '#ea580c'}
REG_ALPHA = {'TREND UP': 0.10, 'TREND DOWN': 0.10, 'RANGE': 0.05, 'CHOP': 0.07}


def style_ax(ax, title=None, ylab=None):
    ax.set_facecolor(PANEL)
    ax.tick_params(colors=MUT, labelsize=8)
    for s in ['top', 'right']:
        ax.spines[s].set_visible(False)
    for s in ['left', 'bottom']:
        ax.spines[s].set_color(GRID)
    ax.grid(True, alpha=0.18, color=GRID, lw=0.5)
    if title:
        ax.set_title(title, color=FG, fontsize=10, fontweight='bold', loc='left')
    if ylab:
        ax.set_ylabel(ylab, color=MUT, fontsize=8)


def add_regime_bg(ax, dfx):
    y0_ = dfx['Close'].min() * 0.965
    y1_ = dfx['Close'].max() * 1.035
    prev = None
    start = None
    spans = []
    for i, r in dfx.iterrows():
        if r['regime'] != prev:
            if prev is not None and start is not None:
                spans.append((start, dfx.loc[i - 1, 'Date'], prev))
            prev = r['regime']
            start = r['Date']
    if prev is not None:
        spans.append((start, dfx.iloc[-1]['Date'], prev))
    for s, e, lab in spans:
        ax.axvspan(s, e, color=REG_COLORS[lab], alpha=REG_ALPHA[lab], lw=0)
    return y0_, y1_


def draw_events(ax, dfx, events_sub, font=6.5):
    last_side = None
    last_date = None
    for d in sorted(events_sub.keys()):
        i = dfx['Date'].searchsorted(d)
        if i >= len(dfx):
            i = len(dfx) - 1
        close = dfx.iloc[i]['Close']
        if last_date is not None and (d - last_date).days < 130 and last_side == 'top':
            side = 'bottom'
        elif last_date is not None and (d - last_date).days < 130 and last_side == 'bottom':
            side = 'top'
        else:
            side = 'top' if (last_side != 'top') else 'bottom'
        last_side = side
        last_date = d
        txt = str(events_sub[d])
        is_down = any(w in txt.lower() for w in ['crash', 'shock', 'panic', 'scare', '-'])
        col = '#f87171' if is_down else '#4ade80'
        off = 14 if side == 'top' else -14
        ax.plot(d, close, 'o', ms=4, color=col, zorder=6)
        ax.annotate(txt.split('(')[0].strip(), xy=(d, close), xytext=(0, off),
                    textcoords='offset points', fontsize=font, color=col,
                    fontweight='bold', ha='center',
                    va='bottom' if side == 'top' else 'top',
                    bbox=dict(boxstyle='round,pad=0.25', fc='#1e293b', ec=col, alpha=0.9))


def make_master_map(df, events):
    fig = plt.figure(figsize=(18, 13.5), facecolor=BG)
    gs = fig.add_gridspec(5, 1, height_ratios=[3.4, 1.1, 1.0, 1.0, 0.55],
                          hspace=0.12, left=0.055, right=0.985, top=0.93, bottom=0.06)
    ax_p = fig.add_subplot(gs[0])
    ax_m = fig.add_subplot(gs[1], sharex=ax_p)
    ax_r = fig.add_subplot(gs[2], sharex=ax_p)
    ax_c = fig.add_subplot(gs[3], sharex=ax_p)
    ax_y = fig.add_subplot(gs[4], sharex=ax_p)

    y0m, y1m = add_regime_bg(ax_p, df)
    ax_p.plot(df['Date'], df['Close'], color='#22d3ee', lw=1.0, alpha=0.95, label='Close')
    ax_p.plot(df['Date'], df['sma50'], color='#fbbf24', lw=0.8, alpha=0.8, label='SMA 50')
    ax_p.plot(df['Date'], df['sma200'], color='#c084fc', lw=0.8, alpha=0.8, label='SMA 200')
    draw_events(ax_p, df, events)
    ax_p.set_ylim(y0m, y1m)

    latest = df.iloc[-1]
    stats = (
        f"LATEST  {latest['Date'].strftime('%d %b %Y')}   Close Rs{latest['Close']:,.0f}\n"
        f"Regime: {latest['regime']}   (ADX {latest['adx14']:.0f} / Chop {latest['chop14']:.0f})\n"
        f"MACD hist {'+' if latest['macd_hist'] >= 0 else ''}{latest['macd_hist']:.0f}   RSI {latest['rsi14']:.0f} ({latest['rsi_zone']})\n"
        f"Month so far: {latest['month_so_far_pct']:+.1f}%   YTD: {latest['ytd_pct']:+.1f}%   "
        f"1yr: {latest['ret_1y_pct']:+.1f}%   from ATH: {latest['off_ath_pct']:+.1f}%"
    )
    props = dict(boxstyle='round,pad=0.55', fc='#1e293b', ec='#475569', alpha=0.95)
    ax_p.text(0.005, 0.985, stats, transform=ax_p.transAxes, fontsize=8.5, va='top',
              color=FG, bbox=props, family='monospace', zorder=7)

    leg = [Patch(fc=REG_COLORS[k], alpha=0.35, label=k) for k in REG_COLORS]
    leg += [Line2D([0], [0], color='#22d3ee', lw=1.2, label='Close'),
            Line2D([0], [0], color='#fbbf24', lw=0.8, label='SMA 50'),
            Line2D([0], [0], color='#c084fc', lw=0.8, label='SMA 200')]
    ax_p.legend(handles=leg, loc='lower left', ncol=4, fontsize=7,
                framealpha=0.25, facecolor=BG, edgecolor=GRID, labelcolor=FG)
    style_ax(ax_p)
    ax_p.set_title('NIFTY 50 — Daily State Map 2015 → today (background = regime: '
                   'green up-trend · red down-trend · blue range · orange chop)',
                   color='white', fontsize=13, fontweight='bold')
    ax_p.tick_params(labelbottom=False)
    ax_p.xaxis.set_major_locator(mdates.YearLocator())
    ax_p.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))

    col_h = np.where(df['macd_hist'] >= 0, '#4ade80', '#f87171')
    ax_m.bar(df['Date'], df['macd_hist'], color=col_h, width=1.2, alpha=0.75)
    ax_m.plot(df['Date'], df['macd'], color='#22d3ee', lw=0.7)
    ax_m.plot(df['Date'], df['signal'], color='#fbbf24', lw=0.7)
    ax_m.axhline(0, color=GRID, lw=0.6)
    style_ax(ax_m, title='MACD 12/26/9 — green hist = above signal (bull bias)', ylab='MACD')
    ax_m.tick_params(labelbottom=False)

    ax_r.plot(df['Date'], df['rsi14'], color='#a78bfa', lw=0.8)
    ax_r.axhline(70, color='#f87171', ls='--', lw=0.7)
    ax_r.axhline(30, color='#4ade80', ls='--', lw=0.7)
    ax_r.fill_between(df['Date'], 70, df['rsi14'], where=df['rsi14'] >= 70,
                      color='#f87171', alpha=0.12, interpolate=True)
    ax_r.fill_between(df['Date'], 30, df['rsi14'], where=df['rsi14'] <= 30,
                      color='#4ade80', alpha=0.12, interpolate=True)
    ax_r.set_ylim(5, 95)
    style_ax(ax_r, title='RSI 14 — above 70 overbought / below 30 oversold', ylab='RSI')
    ax_r.tick_params(labelbottom=False)

    ax_c.plot(df['Date'], df['chop14'], color='#fb923c', lw=0.8)
    ax_c.axhline(61.8, color='#f87171', ls='--', lw=0.7)
    ax_c.axhline(38.2, color='#4ade80', ls='--', lw=0.7)
    ax_c.fill_between(df['Date'], 61.8, df['chop14'], where=df['chop14'] >= 61.8,
                      color='#ea580c', alpha=0.15, interpolate=True)
    ax_c.text(df['Date'].iloc[3], 64, 'CHOP zone (>61.8)', color='#fdba74', fontsize=6.5, va='bottom')
    ax_c.text(df['Date'].iloc[3], 35, 'TREND zone (<38.2)', color='#86efac', fontsize=6.5, va='top')
    ax_c.set_ylim(0, 100)
    style_ax(ax_c, title='Choppiness Index 14 — high = chop / low = clean trend', ylab='Chop')
    ax_c.tick_params(labelbottom=False)

    yearly = df.groupby(df['Date'].dt.year)['Close'].agg(['first', 'last'])
    yret = 100 * (yearly['last'].values / yearly['first'].values - 1)
    cols = np.where(yret >= 0, '#4ade80', '#f87171')
    bars = ax_y.bar(pd.to_datetime(yearly.index.astype(str) + '-07-01'), yret,
                    width=360, color=cols, alpha=0.85)
    for b, v in zip(bars, yret):
        ax_y.text(b.get_x() + b.get_width() / 2, v + (0.4 if v >= 0 else -1.4),
                  f"{int(v)}%", ha='center', fontsize=6.5, color=MUT, fontweight='bold')
    ax_y.axhline(0, color=GRID, lw=0.6)
    ax_y.set_ylim(yret.min() - 10, yret.max() + 9)
    style_ax(ax_y, title='Calendar-year return %', ylab='yr %')
    ax_y.xaxis.set_major_locator(mdates.YearLocator())
    ax_y.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax_y.tick_params(labelsize=8)

    plt.savefig(OUT_MAP, dpi=130, bbox_inches='tight', facecolor=BG, edgecolor='none')
    plt.close(fig)
    print('map ->', OUT_MAP)


def make_zoom_map(df):
    Z = 126
    dz = df.iloc[-Z:].reset_index(drop=True)
    fig2 = plt.figure(figsize=(16, 11.5), facecolor=BG)
    gs2 = fig2.add_gridspec(4, 1, height_ratios=[3.2, 1.15, 1.0, 1.0],
                            hspace=0.14, left=0.06, right=0.985, top=0.90, bottom=0.08)
    ap = fig2.add_subplot(gs2[0])
    am = fig2.add_subplot(gs2[1], sharex=ap)
    ar = fig2.add_subplot(gs2[2], sharex=ap)
    ac = fig2.add_subplot(gs2[3], sharex=ap)

    y0z, y1z = add_regime_bg(ap, dz)
    ap.plot(dz['Date'], dz['Close'], color='#22d3ee', lw=1.6, zorder=4)
    ap.plot(dz['Date'], dz['sma50'], color='#fbbf24', lw=1.0, alpha=0.85, zorder=3)
    ap.plot(dz['Date'], dz['sma200'], color='#c084fc', lw=1.0, alpha=0.85, zorder=3)
    ap.set_ylim(y0z, y1z)

    for _, r in dz.iterrows():
        if r['div'] == 'BULL_DIV':
            ap.annotate('▲ BULL', xy=(r['Date'], r['Close']), xytext=(0, 10),
                        textcoords='offset points', fontsize=6, color='#4ade80',
                        ha='center', fontweight='bold', zorder=7)
        elif r['div'] == 'BEAR_DIV':
            ap.annotate('▼ BEAR', xy=(r['Date'], r['Close']), xytext=(0, -12),
                        textcoords='offset points', fontsize=6, color='#f87171',
                        ha='center', fontweight='bold', zorder=7)

    for _, r in dz.iterrows():
        if r['macd_cross'] == 'CROSS_UP':
            am.plot(r['Date'], 0, '^', color='#4ade80', ms=7, zorder=6)
        elif r['macd_cross'] == 'CROSS_DOWN':
            am.plot(r['Date'], 0, 'v', color='#f87171', ms=7, zorder=6)

    am.bar(dz['Date'], dz['macd_hist'],
           color=np.where(dz['macd_hist'] >= 0, '#4ade80', '#f87171'), width=0.9, alpha=0.7)
    am.axhline(0, color=GRID, lw=0.6)
    lo = dz['macd_hist'].min() * 1.2 or -1
    hi = dz['macd_hist'].max() * 1.2 or 1
    am.set_ylim(lo, hi)
    style_ax(am, title='MACD — ▲ cross up / ▼ cross down (daily signal for trade bias)')
    am.tick_params(labelbottom=False)

    ar.plot(dz['Date'], dz['rsi14'], color='#a78bfa', lw=1.2)
    ar.axhline(70, color='#f87171', ls='--', lw=0.8)
    ar.axhline(30, color='#4ade80', ls='--', lw=0.8)
    ar.fill_between(dz['Date'], 70, dz['rsi14'], where=dz['rsi14'] >= 70,
                    color='#f87171', alpha=0.15, interpolate=True)
    ar.fill_between(dz['Date'], 30, dz['rsi14'], where=dz['rsi14'] <= 30,
                    color='#4ade80', alpha=0.15, interpolate=True)
    ar.set_ylim(15, 85)
    style_ax(ar, title='RSI 14 — momentum health + divergence source')
    ar.tick_params(labelbottom=False)

    ac.plot(dz['Date'], dz['chop14'], color='#fb923c', lw=1.2)
    ac.axhline(61.8, color='#f87171', ls='--', lw=0.8)
    ac.axhline(38.2, color='#4ade80', ls='--', lw=0.8)
    ac.fill_between(dz['Date'], 61.8, dz['chop14'], where=dz['chop14'] >= 61.8,
                    color='#ea580c', alpha=0.18, interpolate=True)
    ac.set_ylim(0, 100)
    style_ax(ac, title='Choppiness — orange fill = chop regime (momentum systems bleed here)')
    ac.xaxis.set_major_locator(mdates.MonthLocator())
    ac.xaxis.set_major_formatter(mdates.DateFormatter('%d %b %y'))
    ac.tick_params(labelsize=8)

    ld = dz.iloc[-1]
    readout = (
        f"TODAY / {ld['Date'].strftime('%d %b %Y')}   Close Rs{ld['Close']:,.0f}\n"
        f"REGIME: {ld['regime']}   ->  " +
        ("momentum LONG-lean" if ld['regime'] == 'TREND UP' else
         "momentum SHORT-lean" if ld['regime'] == 'TREND DOWN' else
         "NO fresh trade — wait for regime change" if ld['regime'] == 'CHOP' else
         "RANGE — no fresh momentum entry") +
        f"\nADX {ld['adx14']:.0f} · Chop {ld['chop14']:.0f} · RSI {ld['rsi14']:.0f} ({ld['rsi_zone']})\n"
        f"MACD hist {'+' if ld['macd_hist'] >= 0 else ''}{ld['macd_hist']:.0f}  ·  "
        f"{'last CROSS_UP' if ld['macd_cross'] == 'CROSS_UP' else 'last CROSS_DOWN' if ld['macd_cross'] == 'CROSS_DOWN' else 'no cross today'}\n"
        f"Month: {ld['month_so_far_pct']:+.1f}% · YTD: {ld['ytd_pct']:+.1f}% · 1yr: {ld['ret_1y_pct']:+.1f}% · from ATH: {ld['off_ath_pct']:+.1f}%"
    )
    props2 = dict(boxstyle='round,pad=0.6', fc='#1e293b', ec='#475569', alpha=0.95)
    ap.text(0.01, 0.97, readout, transform=ap.transAxes, fontsize=8.5, va='top',
            color=FG, bbox=props2, family='monospace', zorder=8)

    leg2 = [Patch(fc=REG_COLORS[k], alpha=0.35, label=k) for k in REG_COLORS]
    leg2 += [Line2D([0], [0], marker='^', color='none', mfc='#4ade80', ms=8, label='bullish divergence ▲'),
             Line2D([0], [0], marker='v', color='none', mfc='#f87171', ms=8, label='bearish divergence ▼')]
    ap.legend(handles=leg2, loc='lower left', ncol=2, fontsize=7.5,
              framealpha=0.25, facecolor=BG, edgecolor=GRID, labelcolor=FG)
    style_ax(ap)
    ap.set_title('NIFTY — last 6 months in the 11-year map  (zoom of master map)',
                 color='white', fontsize=13, fontweight='bold')
    ap.tick_params(labelbottom=False)

    plt.savefig(OUT_ZOOM, dpi=130, bbox_inches='tight', facecolor=BG, edgecolor='none')
    plt.close(fig2)
    print('zoom ->', OUT_ZOOM)


# ---------------------------------------------------------------- state cycle map
def make_cycle_map(df, A):
    """Ghoomta hua map — stage se stage tak market ka flow (counts)."""
    import math
    st = A['stages']
    share = {s['stage']: s for s in st['share']}
    meta_by_id = {m['id']: m for m in A['stage_meta']}
    present = [m for m in A['stage_meta'] if m['name'] in share]

    # wheel position per stage id (deg, 0 = +x-axis, ccw)
    ang = {0: 290, 1: 318, 2: 346, 3: 14, 4: 42, 9: 74, 5: 150, 6: 184, 7: 218, 8: 252}
    R = 1.0
    pos = {}
    for m in present:
        rad = math.radians(ang[m['id']])
        pos[m['name']] = (R * math.cos(rad), R * math.sin(rad))

    fig = plt.figure(figsize=(16, 11), facecolor=BG)
    ax = fig.add_axes([0.005, 0.0, 0.64, 1.0])
    ax.set_facecolor(BG)
    ax.axis('off')
    ax.set_xlim(-1.6, 1.6)
    ax.set_ylim(-1.55, 1.55)
    ax.set_aspect('equal')

    maxpct = max(s['pct'] for s in st['share'])
    ring = plt.Circle((0, 0), R, fill=False, color=GRID, lw=1.2, ls=(0, (4, 4)), zorder=1)
    ax.add_patch(ring)

    # arrows: stage badalne wale transitions (top 14, self-loop nahi)
    ts = [t for t in st['top_trans'] if t['f'] != t['t']][:14]
    maxc = max((t['n'] for t in ts), default=1)
    for t in ts:
        pA, pB = pos.get(t['f']), pos.get(t['t'])
        if pA is None or pB is None:
            continue
        # arrow color = jis stage pe gaye
        tgt = next((m for m in present if m['name'] == t['t']), None)
        if tgt is None:
            continue
        k = t['n'] / maxc
        arr = FancyArrowPatch(pA, pB, connectionstyle='arc3,rad=0.16',
                              arrowstyle='-|>', mutation_scale=9 + 7 * k,
                              lw=1.1 + 2.8 * k, color=tgt['color'],
                              alpha=0.30 + 0.55 * k, zorder=3)
        ax.add_patch(arr)
        mx, my = (pA[0] + pB[0]) / 2, (pA[1] + pB[1]) / 2
        ax.text(mx * 1.06, my * 1.06, str(t['n']), color=tgt['color'],
                fontsize=8.5, fontweight='bold', ha='center', va='center', zorder=4)

    # nodes
    latest = df.iloc[-1]['scenario']
    for m in present:
        x, y = pos[m['name']]
        rd = 0.085 + 0.115 * math.sqrt(share[m['name']]['pct'] / maxpct)
        ax.add_patch(plt.Circle((x, y), rd, color=m['color'], ec='#0b1120',
                                lw=1.6, zorder=6))
        if m['name'] == latest:
            ax.add_patch(plt.Circle((x, y), rd + 0.045, fill=False, color='#fde047',
                                    lw=2.2, zorder=5))
        tx, ty = 1.26 * x, 1.26 * y
        ha = 'left' if x >= 0.0 else 'right'
        ax.text(tx, ty + 0.05, m['name'], color=FG, fontsize=11, fontweight='bold',
                ha=ha, va='center', zorder=7)
        ax.text(tx, ty - 0.09, f"{share[m['name']]['pct']}% din", color=MUT,
                fontsize=9, ha=ha, va='center', zorder=7)

    # legend (right side)
    meta_lbl = {'BUY': 'entry (next open)', 'HOLD': 'hold', 'WATCH': 'watch-confirm',
                'NO-NEW': 'no new', 'STAND-ASIDE': 'stand aside',
                'NO-BUY': 'no buy', 'AVOID': 'avoid', 'NO-TOUCH': 'no touch',
                'NO-DATA': '—'}
    y0 = 0.90
    fig.text(0.665, y0, 'HAR STAGE KA ACTION (v1 plan)', color='#f8fafc',
             fontsize=12, fontweight='bold')
    for i, m in enumerate(present):
        y = y0 - 0.058 * (i + 1)
        fig.text(0.665, y, '▮', color=m['color'], fontsize=13, va='center')
        fig.text(0.692, y, f"{m['name']}   ", color=FG, fontsize=10.5,
                 fontweight='bold', va='center')
        fig.text(0.692 + 0.115, y, f"{share[m['name']]['pct']}% · "
                 f"{meta_lbl.get(m['action'], m['action'])}", color=MUT,
                 fontsize=9.5, va='center')
    yb = y0 - 0.058 * (len(present) + 1.6)
    fig.text(0.665, yb, f"Aaj ka stage: {latest}  (gold ring)", color='#fde047',
             fontsize=10.5, fontweight='bold')
    fig.text(0.665, yb - 0.045, 'Arrow = market ne stage badla (count)',
             color=MUT, fontsize=9.5)
    fig.text(0.665, yb - 0.088, 'Self-loop exclude (stage same rahe).',
             color=MUT, fontsize=9.5)
    fig.text(0.665, yb - 0.131, 'Data: 2015-2026, warmup ~200 din hatake.',
             color=MUT, fontsize=9.5)

    fig.suptitle('NIFTY STATE CYCLE — market kis stage se kis stage tak ghoomta hai (2015-2026)',
                 color=FG, fontsize=15, fontweight='bold', y=0.965, x=0.30)
    plt.savefig(OUT_CYCLE, dpi=130, facecolor=BG)
    plt.close(fig)
    print('cycle ->', OUT_CYCLE)


# ---------------------------------------------------------------- outputs
def write_outputs(df, A):
    keep = ['Date', 'Close', 'sma50', 'sma200', 'atr14', 'chop14', 'adx14',
            'macd', 'signal', 'macd_hist', 'rsi14', 'regime', 'macd_cross',
            'rsi_zone', 'div', 'month_so_far_pct', 'ytd_pct', 'ret_1y_pct',
            'off_ath_pct', 'scenario', 'action', 'sig', 'Event']
    df[keep].to_csv(OUT_DAILY, index=False, float_format='%.2f')

    w = df.groupby(df['Date'].dt.to_period('W')).agg(
        week=('Date', 'last'),
        open=('Close', 'first'), close=('Close', 'last'),
        regime=('regime', lambda s: s.value_counts().idxmax()),
        n_days=('Close', 'count')).reset_index(drop=True)
    w['ret_pct'] = 100 * (w['close'] / w['open'] - 1)
    w['week'] = w['week'].dt.strftime('%Y-%m-%d')
    w[['week', 'open', 'close', 'ret_pct', 'regime', 'n_days']].to_csv(
        OUT_WEEKLY, index=False, float_format='%.2f')

    m = df.groupby(df['Date'].dt.to_period('M')).agg(
        month=('Date', 'last'),
        open=('Close', 'first'), close=('Close', 'last'),
        regime=('regime', lambda s: s.value_counts().idxmax()),
        n_days=('Close', 'count')).reset_index(drop=True)
    m['ret_pct'] = 100 * (m['close'] / m['open'] - 1)
    m['month'] = m['month'].dt.strftime('%Y-%m-%d')
    m[['month', 'open', 'close', 'ret_pct', 'regime', 'n_days']].to_csv(
        OUT_MONTHLY, index=False, float_format='%.2f')

    ld = df.iloc[-1]
    series = [[r['Date'].strftime('%Y-%m-%d'), round(r['Close'], 1),
               REGIME_CODES[r['regime']], round(r['macd_hist'], 0),
               round(r['rsi14'], 0), round(r['chop14'], 0), round(r['adx14'], 0),
               1 if r['macd_cross'] == 'CROSS_UP' else 2 if r['macd_cross'] == 'CROSS_DOWN' else 0,
               1 if r['div'] == 'BULL_DIV' else -1 if r['div'] == 'BEAR_DIV' else 0,
               round(r['month_so_far_pct'], 1), round(r['ytd_pct'], 1),
               round(r['off_ath_pct'], 1),
               -1 if r['scenario'] == 'WARMUP' else scenario.META[r['scenario']]['id']
               ] for _, r in df.iterrows()]

    out = {
        'updated': ld['Date'].strftime('%d %b %Y'),
        'source': '4,200-day xlsx (2015–Sep 2026) + Yahoo ^NSEI daily',
        'n_days': len(df),
        'latest': {
            'date': ld['Date'].strftime('%Y-%m-%d'),
            'close': round(ld['Close'], 1),
            'regime': ld['regime'],
            'stage': ld['scenario'],
            'action': ld['action'],
            'adx': round(ld['adx14'], 0), 'chop': round(ld['chop14'], 0),
            'rsi': round(ld['rsi14'], 0), 'rsi_zone': ld['rsi_zone'],
            'macd_hist': round(ld['macd_hist'], 0),
            'cross': ld['macd_cross'] or 'none',
            'div': ld['div'] or 'none',
            'sma50': round(ld['sma50'], 1) if pd.notna(ld['sma50']) else None,
            'sma200': round(ld['sma200'], 1) if pd.notna(ld['sma200']) else None,
            'month_pct': round(ld['month_so_far_pct'], 2),
            'ytd_pct': round(ld['ytd_pct'], 2) if pd.notna(ld['ytd_pct']) else None,
            'ret_1y_pct': round(ld['ret_1y_pct'], 2) if pd.notna(ld['ret_1y_pct']) else None,
            'off_ath_pct': round(ld['off_ath_pct'], 2),
        },
        'series': series,
        'analysis': A,
    }
    with open(OUT_JSON, 'w') as f:
        json.dump(fix(out), f)
    print('daily/weekly/monthly/json ->', OUT_DAILY, OUT_WEEKLY, OUT_MONTHLY, OUT_JSON)


def main():
    df = load_prices()
    df = add_indicators(df)
    scenario.assign_scenarios(df)
    A = compute_analysis(df)
    news = load_news()
    ev = compute_events(df, news)
    A['events'] = ev['list']
    A['drivers'] = ev['drivers']
    events = {r['Date']: str(r['Event']) for _, r in df.iterrows() if r['Event'] and str(r['Event']).strip()}
    make_master_map(df, events)
    make_zoom_map(df)
    make_cycle_map(df, A)
    write_outputs(df, A)
    print('news events analysed:', len(ev['list']))
    print('done.')


if __name__ == '__main__':
    main()