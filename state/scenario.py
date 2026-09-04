"""
scenario.py — har din ke liye ek STAGE label + ACTION (v1 decision rules).

STAGE  = market ka "chapter" momentum-cycle pe (mutually exclusive, priority order).
ACTION = v1 long-only momentum paper plan ke hisaab se aaj ka decision.

Ye module build_state.py, analysis_strategy.py aur make_cycle_map.py sab use karte
hain — taaki definitions ek hi jagah rahein.

Stage rules 2015-2026 ke data se nikale gaye hain (dekho docs/NIFTY_STATE_STRATEGY.md):
  - RSI 60-70 ke din aage +3.14% (win 88%) -> strength follow karo
  - RSI < 30 -> +20d -7.7% (knife)           -> oversold pe mat kharido
  - ADX>=25 +DI side = TREND, chop>=55 = CHOP (regime pehle se)
  - Chop ~80% din no-trade; cross/div akela chop mein NO EDGE (f20 ~0%)

ENTRY TIERS (kab trade milegi — honest cadence):
  T1 fresh-trend : regime TREND UP bane (entry-candidate, ~18/yr, gap ~7 din)
  T2 re-accel    : pullback ke baad ALL-ALIGN/STRONG-FLOW wapas (rare, ~1/yr)
  T3 chop-trigger: CHOP-UP + cross/div — NO EDGE, trade mat lo (sirf confirm)
  Matlab: trend wale mahine 1-4 trades, chop mahine 0. Single index pe
  har mahine guaranteed trade impossible hai bina edge khoye.
"""
import numpy as np
import pandas as pd

# stage: (id, name, color, action, one-line desc, v1 rule)
STAGES = [
    (0, 'CHOP-MID',     '#94a3b8', 'STAND-ASIDE',
     'No-trend base: RSI ~45-60, MACD flat — market idhar-udhar',
     'Chop hai, koi edge nahi. Fresh trade NO — jab tak stage break na ho.'),
    (1, 'CHOP-UP',      '#0d9488', 'WATCH',
     'Recovery shuru: chop ke andar RSI 60+ ya RSI 52+ ke saath MACD+',
     'Trigger (cross/div) aa gaya toh T3 candidate — par T3 ka edge nahi hai, '
     'sirf T1 confirm hone pe hi trade.'),
    (2, 'STRONG-FLOW',  '#22c55e', 'BUY',
     'Trend ban raha hai: SMA200 upar + SMA50 up + ADX>=20 + RSI>=55 + MACD+',
     'ENTRY (T1/T2). Next open pe 1x long (CE). Stop = entry - 2xATR. '
     'Exit: trend-flip ya week-2..4 window.'),
    (3, 'ALL-ALIGN BULL', '#15803d', 'BUY',
     'Sab green aligned: TREND UP regime + RSI 55-71 + SMA200 ke upar',
     'ENTRY / HOLD (T1/T2). Exit: TOP-WARNING pe partial lock; trend-flip pe full.'),
    (4, 'TOP-WARNING',  '#d97706', 'NO-NEW',
     'Thakawat: RSI 72+ ya bearish divergence — bull-run ka last phase',
     'Naya long mat lo. Andar ho toh 50% lock karo, baaki trend-flip pe.'),
    (5, 'CHOP-DOWN',    '#f97316', 'STAND-ASIDE',
     'Weak chop: RSI<=45 ya MACD deep- (-15 se neeche) — neeche jhukta hua',
     'No entry. Momentum long ke liye ye zona forbidden hai.'),
    (6, 'WEAK',         '#fb7185', 'NO-BUY',
     'Structure gir raha: RSI<=38 + SMA50 ke neeche',
     'Agar trade andar ho toh exit karo. Naya long strictly NO.'),
    (7, 'BEAR',         '#dc2626', 'AVOID',
     'TREND DOWN regime (ADX>=25, -DI upar) — market gir raha hai',
     'Long avoid karo. Short-lean sirf paper experiment ke liye.'),
    (8, 'PANIC',        '#7f1d1d', 'NO-TOUCH',
     'Falling knife: TREND DOWN + RSI<=35 + MACD- + SMA50 neeche',
     'Chaku mat pakdo — oversold ke baad bhi aage girta hai. RSI>40 recovery wait.'),
    (9, 'EARLY-UP',     '#10b981', 'HOLD',
     'TREND UP andar hai par momentum thanda (RSI<55) — pullback ya fresh start',
     'Jo trade andar hai usse hold. Naya entry T2 (re-accel) confirmation pe.'),
]

META = {name: {'id': sid, 'name': name, 'color': color, 'action': action,
               'desc': desc, 'rule': rule}
        for sid, name, color, action, desc, rule in STAGES}
ID2NAME = {sid: name for sid, name, *_ in STAGES}
ACT_CLS = {  # html-friendly classes for action chips
    'BUY': 'bg-green-600 text-white',
    'HOLD': 'bg-emerald-100 text-emerald-800',
    'WATCH': 'bg-teal-100 text-teal-800',
    'NO-NEW': 'bg-amber-100 text-amber-800',
    'STAND-ASIDE': 'bg-slate-200 text-slate-700',
    'NO-BUY': 'bg-rose-100 text-rose-700',
    'AVOID': 'bg-red-100 text-red-700',
    'NO-TOUCH': 'bg-red-900 text-white',
    'NO-DATA': 'bg-slate-100 text-slate-400',
}

# stages jisme entry allowed hai (buy-group)
BUY_STAGES = {'STRONG-FLOW', 'ALL-ALIGN BULL'}


def run_first(mask):
    """mask ke har True-run ka pehla din True, baaki False.

    pandas 3.x note: object-dtype Series pe `~` ints de deta hai,
    isliye shift ke baad dobara .astype(bool) zaroori.
    """
    m = mask.fillna(False).astype(bool)
    prev = m.shift(1).fillna(False).astype(bool)
    return m & ~prev


def assign_scenarios(df):
    """df pe 'scenario', 'action', 'sig' columns add karta hai (in-place).

    Warmup rows (sma200/adx abhi nahi bane) -> 'WARMUP' / NO-DATA.
    Priority: PANIC > BEAR > TOP-WARNING > ALL-ALIGN BULL > EARLY-UP
              > STRONG-FLOW > WEAK > CHOP-DOWN > CHOP-UP > CHOP-MID.
    sig = T1 fresh-trend entry-candidate day.
    """
    df['scenario'] = 'WARMUP'
    df['action'] = 'NO-DATA'
    df['sig'] = 0

    v = df['sma200'].notna() & df['sma50'].notna() & df['adx14'].notna() & df['rsi14'].notna()
    s = df.loc[v]
    if len(s) == 0:
        return df

    rsi = s['rsi14']; macd = s['macd_hist']; reg = s['regime']; adx = s['adx14']
    c = s['Close']; s50 = s['sma50']; s200 = s['sma200']
    div = s['div'].fillna('').astype(str)
    s50up = s50 > s50.shift(5)

    cond = [
        (reg == 'TREND DOWN') & (rsi <= 35) & (macd < 0) & (c < s50),      # PANIC
        reg == 'TREND DOWN',                                                # BEAR
        (rsi >= 72) | (div == 'BEAR_DIV'),                                  # TOP-WARNING
        (reg == 'TREND UP') & (rsi >= 55) & (c > s200),                     # ALL-ALIGN BULL
        reg == 'TREND UP',                                                  # EARLY-UP
        (c > s200) & s50up & (rsi >= 55) & (adx >= 20) & (macd >= 0),       # STRONG-FLOW
        (rsi <= 38) & (c < s50),                                            # WEAK
        (rsi <= 45) | (macd <= -15),                                        # CHOP-DOWN
        (rsi >= 60) | ((rsi >= 52) & (macd >= 0)),                          # CHOP-UP
    ]
    labels = ['PANIC', 'BEAR', 'TOP-WARNING', 'ALL-ALIGN BULL', 'EARLY-UP',
              'STRONG-FLOW', 'WEAK', 'CHOP-DOWN', 'CHOP-UP']
    df.loc[v, 'scenario'] = np.select(cond, labels, default='CHOP-MID')
    df['action'] = df['scenario'].map(lambda x: META.get(x, {}).get('action', 'NO-DATA'))

    # sig = T1: regime TREND UP ke run ka pehla din (entry NEXT open)
    df['sig'] = run_first(df['regime'] == 'TREND UP').astype(int)
    return df


def stage_stats(df):
    """Dashboard/analysis ke liye per-stage + tier-cadence numbers."""
    sc = df['scenario']
    reg = df['regime']
    cross = df['macd_cross'].fillna('')
    div = df['div'].fillna('').astype(str)
    rsi = df['rsi14']
    v = sc != 'WARMUP'
    total = int(v.sum())
    c = df['Close'].to_numpy(dtype=float)
    n = len(df)
    f5 = np.full(n, np.nan); f10 = np.full(n, np.nan); f20 = np.full(n, np.nan)
    for k, arr in ((5, f5), (10, f10), (20, f20)):
        arr[:-k] = c[k:] / c[:-k] - 1

    run_lens = {k: [] for k in META}
    cur, cur_name = 0, None
    for name in sc:
        if name == 'WARMUP':
            if cur_name:
                run_lens[cur_name].append(cur)
            cur, cur_name = 0, None
            continue
        if name == cur_name:
            cur += 1
        else:
            if cur_name:
                run_lens[cur_name].append(cur)
            cur, cur_name = 1, name
    if cur_name:
        run_lens[cur_name].append(cur)

    share, runs = [], {}
    for name in META:
        k = (sc == name).to_numpy() & v.to_numpy()
        if k.sum() == 0:
            continue
        share.append({'stage': name, 'n': int(k.sum()),
                      'pct': round(100.0 * k.sum() / total, 1),
                      'avg20': round(float(np.nanmean(f20[k]) * 100), 2),
                      'win20': round(100.0 * float(np.nanmean(f20[k] > 0)), 0)})
        rl = run_lens.get(name, [])
        runs[name] = {'runs': len(rl),
                      'avg_len': round(float(np.mean(rl)), 1) if rl else 0,
                      'max_len': int(max(rl)) if rl else 0}

    # ---- entry tiers ----
    t1 = run_first(reg == 'TREND UP') & v                      # fresh trend
    t2 = run_first(sc.isin(BUY_STAGES) & sc.shift(1).eq('EARLY-UP') & v)  # re-accel
    t3 = run_first((sc == 'CHOP-UP') &
                   ((cross == 'CROSS_UP') | (div == 'BULL_DIV')) & v)      # chop trigger

    def tier_stats(mask, label):
        k = mask.to_numpy() & v.to_numpy()
        idx = np.flatnonzero(k)
        years = int(df['Date'].dt.year[v].nunique())
        out = {'tier': label, 'n': int(len(idx)),
               'per_year': round(len(idx) / max(years, 1), 1),
               'gap_avg': round(float(np.mean(np.diff(idx))), 1) if len(idx) > 1 else None}
        for h, arr in (('f10', f10), ('f20', f20)):
            vals = arr[k]
            out[f'avg_{h}'] = round(float(np.nanmean(vals) * 100), 2) if vals.size else None
            out[f'win_{h}'] = round(100.0 * float(np.nanmean(vals > 0)), 0) if vals.size else None
        return out

    tiers = [tier_stats(t1, 'T1 fresh-trend'),
             tier_stats(t2, 'T2 re-accel after pullback'),
             tier_stats(t3, 'T3 chop-trigger (no-edge)')]

    # quality entries = T1 + T2 -> per-month distribution (honest cadence)
    qmask = (t1 | t2).to_numpy() & v.to_numpy()
    qidx = np.flatnonzero(qmask)
    qmonths = df['Date'].dt.to_period('M')[qmask]
    qmo_cnt = qmonths.value_counts()
    all_mo = df['Date'].dt.to_period('M')[v].unique()
    dist = {'0': 0, '1': 0, '2': 0, '3': 0, '4+': 0}
    for p in all_mo:
        cc = int(qmo_cnt.get(str(p), 0))
        key = '4+' if cc >= 4 else str(cc)
        dist[key] = dist.get(key, 0) + 1
    dist_pct = {k: round(100.0 * val / max(len(all_mo), 1), 1)
                for k, val in dist.items()}

    # top transitions (stage -> next stage, change-only) for the rotating map
    nxt = sc.shift(-1)
    trans = {}
    for i in df.index:
        f, t = sc.iloc[i], nxt.iloc[i] if i in nxt.index else None
        if f == 'WARMUP' or t is None or t == 'WARMUP' or f == t:
            continue
        trans[(f, t)] = trans.get((f, t), 0) + 1
    top = sorted(trans.items(), key=lambda x: -x[1])[:14]

    return {'share': share, 'runs': runs, 'tiers': tiers,
            'quality_n': int(len(qidx)),
            'quality_per_year': round(len(qidx) / max(len(all_mo) / 12.0, 1), 1),
            'quality_gap_avg': round(float(np.mean(np.diff(qidx))), 1) if len(qidx) > 1 else None,
            'months_dist_pct': dist_pct,
            'top_trans': [{'f': f, 't': t, 'n': c2} for (f, t), c2 in top]}
