"""RSI(14) behaviour over 2015-2026 — how the value varies and what its
movement tells us. Reads state/nifty_daily_state.csv.

Outputs: printed stats + state/rsi_analysis.png
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

HERE = os.path.dirname(os.path.abspath(__file__))
df = pd.read_csv(os.path.join(HERE, 'nifty_daily_state.csv'), parse_dates=['Date'])
df = df.dropna(subset=['rsi14', 'Close']).reset_index(drop=True)
c = df['Close']
df['daily_ret'] = 100 * c.pct_change()

BUCKETS = [(0, 30, '<30 (oversold)'), (30, 40, '30-40'), (40, 50, '40-50'),
           (50, 60, '50-60'), (60, 70, '60-70'), (70, 100, '>70 (overbought)')]


def fwd(i, k):
    j = i + k
    return np.nan if j >= len(df) else 100 * (df.iloc[j]['Close'] / df.iloc[i]['Close'] - 1)


n = len(df)
print(f'rows: {n}')
print(f"RSI overall: mean {df['rsi14'].mean():.1f}  median {df['rsi14'].median():.1f}  "
      f"min {df['rsi14'].min():.1f}  max {df['rsi14'].max():.1f}")
print(f"din RSI>50: {(df['rsi14']>50).mean()*100:.0f}%   din RSI<50: {(df['rsi14']<50).mean()*100:.0f}%")
print(f"din RSI>70: {(df['rsi14']>70).mean()*100:.1f}%   din RSI<30: {(df['rsi14']<30).mean()*100:.1f}%")
print()

# ---- distribution + forward returns by bucket
stats = []
for lo, hi, name in BUCKETS:
    sub = df[(df['rsi14'] >= lo) & (df['rsi14'] < hi)]
    idxs = list(sub.index)
    f5 = [fwd(i, 5) for i in idxs]
    f20 = [fwd(i, 20) for i in idxs]
    f1 = [fwd(i, 1) for i in idxs]
    f5 = [v for v in f5 if not np.isnan(v)]
    f20 = [v for v in f20 if not np.isnan(v)]
    f1 = [v for v in f1 if not np.isnan(v)]
    stats.append({'name': name, 'share': 100 * len(idxs) / n,
                  'n': len(idxs), 'f5': float(np.mean(f5)), 'w5': 100 * np.mean(np.array(f5) > 0),
                  'f20': float(np.mean(f20)), 'w20': 100 * np.mean(np.array(f20) > 0)})

print(f"{'RSI bucket':<18}{'% din':>6}{'+5d avg':>9}{'+5d win':>9}{'+20d avg':>10}{'+20d win':>10}")
for s in stats:
    print(f"{s['name']:<18}{s['share']:>5.1f}%{s['f5']:>+8.2f}%{s['w5']:>8.0f}%{s['f20']:>+9.2f}%{s['w20']:>9.0f}%")
print()

# ---- next-day after extremes
for label, cond in [('RSI<30', df['rsi14'] < 30), ('RSI>70', df['rsi14'] > 70),
                    ('RSI 45-55 (chop mid)', (df['rsi14'] > 45) & (df['rsi14'] < 55)),
                    ('all days', pd.Series(True, index=df.index))]:
    sub = df[cond]
    nxt = [fwd(i, 1) for i in sub.index]
    nxt = [v for v in nxt if not np.isnan(v)]
    print(f"next-day: {label:<22} n={len(nxt):<5} avg {np.mean(nxt):+.3f}%  up% {100*np.mean(np.array(nxt)>0):.0f}%")

print()
# ---- RSI 50-line cross (bullish vs bearish half)
def cross_dir(i):
    if i == 0:
        return None
    if df.iloc[i]['rsi14'] >= 50 > df.iloc[i - 1]['rsi14']:
        return 'up'
    if df.iloc[i]['rsi14'] < 50 <= df.iloc[i - 1]['rsi14']:
        return 'down'
    return None

ups, dns = [], []
for i in range(1, n):
    d = cross_dir(i)
    if d == 'up':
        v = fwd(i, 20)
        if not np.isnan(v):
            ups.append(v)
    elif d == 'down':
        v = fwd(i, 20)
        if not np.isnan(v):
            dns.append(v)
print(f"RSI crosses 50-up : n={len(ups)}  avg +20d {np.mean(ups):+.2f}%  win {100*np.mean(np.array(ups)>0):.0f}%")
print(f"RSI crosses 50-dn : n={len(dns)}  avg +20d {np.mean(dns):+.2f}%  win {100*np.mean(np.array(dns)>0):.0f}%")

# ---- RSI by regime
print()
print('RSI by regime:')
for reg in ['TREND UP', 'TREND DOWN', 'RANGE', 'CHOP']:
    sub = df[df['regime'] == reg]['rsi14']
    print(f"  {reg:<11} avg {sub.mean():5.1f}  | RSI>60 {(sub>60).mean()*100:4.0f}%  RSI<40 {(sub<40).mean()*100:4.0f}%")

# ---- divergence quality already in json - quick reminder numbers
bull = df[df['div'] == 'BULL_DIV']
bear = df[df['div'] == 'BEAR_DIV']
for kind, sub in [('BULL_DIV', bull), ('BEAR_DIV', bear)]:
    f10 = [fwd(i, 10) for i in sub.index]
    f10 = [v for v in f10 if not np.isnan(v)]
    print(f"{kind}: n={len(f10)}  avg +10d {np.mean(f10):+.2f}%  win {100*np.mean(np.array(f10)>0):.0f}%")

# ================================================================ chart
BG, FG, MUT, GRID = '#0f172a', '#e2e8f0', '#94a3b8', '#334155'
fig = plt.figure(figsize=(17, 11), facecolor=BG)
gs = fig.add_gridspec(2, 2, height_ratios=[1.6, 1.0], hspace=0.25, wspace=0.07,
                      left=0.05, right=0.985, top=0.93, bottom=0.06)

ax1 = fig.add_subplot(gs[0, :])
ax1.set_facecolor(BG)
ax1.plot(df['Date'], df['rsi14'], color='#a78bfa', lw=0.7)
ax1.axhline(70, color='#f87171', ls='--', lw=0.8)
ax1.axhline(50, color='#64748b', ls=':', lw=0.7)
ax1.axhline(30, color='#4ade80', ls='--', lw=0.8)
ax1.fill_between(df['Date'], 70, df['rsi14'], where=df['rsi14'] >= 70, color='#f87171', alpha=0.18, interpolate=True)
ax1.fill_between(df['Date'], 30, df['rsi14'], where=df['rsi14'] <= 30, color='#4ade80', alpha=0.18, interpolate=True)
ax1.set_ylim(0, 100)
for sp in ['top', 'right']:
    ax1.spines[sp].set_visible(False)
for sp in ['left', 'bottom']:
    ax1.spines[sp].set_color(GRID)
ax1.tick_params(colors=MUT, labelsize=8)
ax1.grid(True, alpha=0.15, color=GRID)
ax1.set_title('RSI(14) 2015-2026 — value swing + extreme zones (<30 green / >70 red)', color='white', fontsize=12, fontweight='bold', loc='left')
ax1.xaxis.set_major_locator(mdates.YearLocator())
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
ax1.text(0.005, 0.95, f"RSI>50 {100*(df['rsi14']>50).mean():.0f}% din · >70 {100*(df['rsi14']>70).mean():.0f}% · <30 {100*(df['rsi14']<30).mean():.0f}%",
         transform=ax1.transAxes, color=MUT, fontsize=9, va='top')

ax2 = fig.add_subplot(gs[1, 0])
ax2.set_facecolor(BG)
vals = df['rsi14'].values
hist, edges = np.histogram(vals, bins=40, range=(0, 100))
colors = []
for hval in edges[:-1]:
    colors.append('#4ade80' if hval < 30 else '#f87171' if hval >= 70 else '#a78bfa')
ax2.bar(edges[:-1] + 1.25, hist, width=2.5, color=colors, alpha=0.9)
ax2.set_facecolor(BG)
for sp in ['top', 'right']:
    ax2.spines[sp].set_visible(False)
for sp in ['left', 'bottom']:
    ax2.spines[sp].set_color(GRID)
ax2.tick_params(colors=MUT, labelsize=8)
ax2.set_title('Distribution — RSI kab kahan rehti hai', color='white', fontsize=11, fontweight='bold', loc='left')
ax2.set_ylabel('din count', color=MUT, fontsize=8)

ax3 = fig.add_subplot(gs[1, 1])
ax3.set_facecolor(BG)
names = [s['name'] for s in stats]
x = np.arange(len(names))
w = 0.38
b1 = ax3.bar(x - w / 2, [s['f5'] for s in stats], w, label='+5d avg', color='#22d3ee', alpha=0.85)
b2 = ax3.bar(x + w / 2, [s['f20'] for s in stats], w, label='+20d avg', color='#fbbf24', alpha=0.85)
for b in list(b1) + list(b2):
    ax3.text(b.get_x() + b.get_width() / 2, b.get_height() + (0.08 if b.get_height() >= 0 else -0.45),
             f"{b.get_height():+.1f}%", ha='center', fontsize=6.5, color=MUT)
ax3.axhline(0, color=GRID, lw=0.7)
ax3.set_xticks(x)
ax3.set_xticklabels(names, rotation=0, fontsize=7.5, color=MUT)
for sp in ['top', 'right']:
    ax3.spines[sp].set_visible(False)
for sp in ['left', 'bottom']:
    ax3.spines[sp].set_color(GRID)
ax3.tick_params(colors=MUT, labelsize=8)
ax3.legend(fontsize=8, facecolor=BG, edgecolor=GRID, labelcolor=FG)
ax3.set_title('RSI zone ke baad forward return', color='white', fontsize=11, fontweight='bold', loc='left')
ax3.set_ylabel('%', color=MUT, fontsize=8)

fig.suptitle('', y=0.995)
plt.savefig(os.path.join(HERE, 'rsi_analysis.png'), dpi=130, bbox_inches='tight', facecolor=BG, edgecolor='none')
print('chart ->', os.path.join(HERE, 'rsi_analysis.png'))