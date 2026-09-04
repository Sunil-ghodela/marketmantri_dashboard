"""Forward-return FLOW profiles + multi-parameter CONFLUENCE patterns (vectorized).

Sheets appended to technical_parameters_full.xlsx.
"""
import os
import shutil
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
XLSX = os.path.join(HERE, 'technical_parameters_full.xlsx')
COPY_TO = '/home/vaibhav/Downloads/meeting_notes/technical_parameters_full.xlsx'

df = pd.read_csv(os.path.join(HERE, 'nifty_daily_state.csv'), parse_dates=['Date'])
df = df.dropna(subset=['rsi14', 'Close']).reset_index(drop=True)
n = len(df)
H = [1, 2, 3, 4, 5, 7, 10, 12, 15, 20]
cl = df['Close'].to_numpy(dtype=float)
HMAX = max(H)

R = df['rsi14']
M = df['macd_hist']
C = df['Close']
S50 = df['sma50']
S200 = df['sma200']
CH = df['chop14']
ADX = df['adx14']
REG = df['regime']


def idx(mask):
    return np.flatnonzero(mask.to_numpy())


def vprof(mask_or_idx, label):
    if isinstance(mask_or_idx, pd.Series):
        ii = idx(mask_or_idx)
    else:
        ii = np.asarray(mask_or_idx, dtype=int)
    ii = ii[ii <= n - 1 - HMAX]
    row = {'State': label, 'n': int(len(ii))}
    for k in H:
        v = (cl[ii + k] / cl[ii] - 1) * 100
        row[f'+{k}d'] = round(float(v.mean()), 2)
    for k in (5, 10, 20):
        v = (cl[ii + k] / cl[ii] - 1) * 100
        row[f'win_+{k}d'] = round(100 * float((v > 0).mean()), 0)
    return row


allmask = pd.Series(True, index=df.index)
flow_rows = [vprof(allmask, 'ALL days (baseline)')]
for reg in ['TREND UP', 'TREND DOWN', 'RANGE', 'CHOP']:
    flow_rows.append(vprof(REG == reg, f'Regime: {reg}'))
flow_rows += [
    vprof(R < 30, 'RSI < 30'),
    vprof((R >= 60) & (R < 70), 'RSI 60-70'),
    vprof(R >= 70, 'RSI >= 70'),
    vprof(M > 0, 'MACD hist +'),
    vprof(M < 0, 'MACD hist -'),
    vprof((C > S50) & (S50 > S200), 'Close>SMA50>SMA200'),
    vprof((C < S50) & (S50 < S200), 'Close<SMA50<SMA200'),
    vprof(CH > 61.8, 'Chop > 62'),
    vprof((ADX >= 25) & (ADX < 35), 'ADX 25-35'),
    vprof(df['div'] == 'BULL_DIV', 'BULL_DIV'),
    vprof(df['div'] == 'BEAR_DIV', 'BEAR_DIV'),
]
flow = pd.DataFrame(flow_rows)

S50_up = S50 > S50.shift(5)
S50_dn = S50 < S50.shift(5)
scen = [
    vprof(allmask, 'ALL days (baseline)'),
    vprof((REG == 'TREND UP') & (R >= 55) & (R <= 75) & (C > S200),
          'ALL-ALIGN BULL: TREND UP + RSI 55-75 + above SMA200'),
    vprof((REG == 'TREND UP') & (ADX >= 25) & (C > S50) & S50_up,
          'BULL: TREND UP + ADX>=25 + SMA50 rising'),
    vprof((R >= 60) & (R <= 72) & (C > S50) & S50_up & (M > 0),
          'BULL: RSI 60-72 + above SMA50 + MACD+ + SMA50 up'),
    vprof((REG == 'TREND DOWN') & (R <= 40) & (M < 0) & (C < S200),
          'FALLING-KNIFE: TREND DOWN + RSI<=40 + MACD- + below SMA200'),
    vprof((REG == 'TREND DOWN') & (R >= 45) & (R <= 65) & (M < 0),
          'DOWN-CONTINUATION: TREND DOWN + RSI 45-65 + MACD-'),
    vprof((REG == 'CHOP') & (R >= 45) & (R <= 58) & (M.abs() < 15),
          'CHOP-MID: chop + RSI 45-58 + MACD flat'),
    vprof((C < S50) & S50_dn & (M < 0) & (R < 45),
          'BEAR STRUCTURE: below SMA50 + SMA50 down + MACD- + RSI<45'),
    vprof((C > S200) & S50_up & (R >= 55) & (ADX >= 20) & (M >= 0),
          'STRONG-FLOW: above SMA200 + SMA50 up + RSI>=55 + ADX>=20 + MACD+'),
    vprof((R <= 35) & (M < 0) & (C < S50),
          'WEAK-DAY: RSI<=35 + MACD- + below SMA50 (no buy)'),
    vprof(df['div'] == 'BULL_DIV', 'BULL_DIV (alone)'),
]
combo = pd.DataFrame(scen)

print('=== HORIZON FLOW (+1..+20 avg cumulative %) ===')
print(flow.to_string(index=False))
print()
print('=== CONFLUENCE SCENARIOS ===')
print(combo.to_string(index=False))

print()
print('=== Kab tak move chalta hai (peak day, phir fade?) ===')
cols = [c for c in flow.columns if c.startswith('+')]
for _, r in flow.iterrows():
    vals = [(int(c[1:-1]), r[c]) for c in cols if r[c] is not None]
    if not vals:
        continue
    peak_d, peak_v = max(vals, key=lambda x: x[1])
    last = vals[-1][1]
    print(f"  {r['State']:<28} peak +{peak_d:>2}d ({peak_v:+.2f}%)  +20d {last:+.2f}%  fade={'YES' if last < peak_v - 0.1 else 'no'}")

with pd.ExcelWriter(XLSX, engine='openpyxl', mode='a', if_sheet_exists='replace') as w:
    flow.to_excel(w, sheet_name='Horizon_Flow', index=False)
    combo.to_excel(w, sheet_name='Scenario_Combos', index=False)
try:
    shutil.copy(XLSX, COPY_TO)
    print('\nxlsx updated + copied')
except Exception as e:
    print('copy failed:', e)