"""All-technical-parameter behaviour analysis (2015-2026).

For every indicator state / filter (RSI zone, chop level, ADX, MACD sign,
SMA position, regime...) it computes: kitne % din us state mein thi + uske
baad ka +5d/+20d average return aur win rate.

Appends a sheet 'Parameter_Edge_Analysis' to technical_parameters_full.xlsx
and prints the table.
"""
import os
import sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
XLSX = os.path.join(HERE, 'technical_parameters_full.xlsx')
COPY_TO = '/home/vaibhav/Downloads/meeting_notes/technical_parameters_full.xlsx'

df = pd.read_csv(os.path.join(HERE, 'nifty_daily_state.csv'), parse_dates=['Date'])
df = df.dropna(subset=['rsi14', 'Close']).reset_index(drop=True)
n = len(df)


def fwd(i, k):
    j = i + k
    return np.nan if j >= len(df) else 100 * (df.iloc[j]['Close'] / df.iloc[i]['Close'] - 1)


R = df['rsi14']
M = df['macd_hist']
C = df['Close']
S50 = df['sma50']
S200 = df['sma200']

MASKS = [
    # --- RSI
    ('RSI < 30 (oversold)', R < 30),
    ('RSI 30-40', (R >= 30) & (R < 40)),
    ('RSI 40-50', (R >= 40) & (R < 50)),
    ('RSI 50-60', (R >= 50) & (R < 60)),
    ('RSI 60-70', (R >= 60) & (R < 70)),
    ('RSI > 70 (overbought)', R >= 70),
    # --- Choppiness
    ('Chop < 38 (clean trend)', df['chop14'] < 38.2),
    ('Chop 38-55 (mild range)', (df['chop14'] >= 38.2) & (df['chop14'] < 55)),
    ('Chop 55-62', (df['chop14'] >= 55) & (df['chop14'] < 61.8)),
    ('Chop > 62 (deep chop)', df['chop14'] >= 61.8),
    # --- ADX
    ('ADX < 15', df['adx14'] < 15),
    ('ADX 15-25', (df['adx14'] >= 15) & (df['adx14'] < 25)),
    ('ADX 25-35', (df['adx14'] >= 25) & (df['adx14'] < 35)),
    ('ADX >= 35 (strong trend)', df['adx14'] >= 35),
    # --- MACD
    ('MACD hist + (bull)', M > 0),
    ('MACD hist - (bear)', M < 0),
    ('MACD CROSS_UP day', df['macd_cross'] == 'CROSS_UP'),
    ('MACD CROSS_DOWN day', df['macd_cross'] == 'CROSS_DOWN'),
    # --- Price vs SMAs
    ('Close > SMA50', C > S50),
    ('Close < SMA50', C < S50),
    ('Close > SMA200', C > S200),
    ('Close < SMA200', C < S200),
    ('SMA50 rising (slope+)', S50 > S50.shift(5)),
    ('SMA50 falling (slope-)', S50 < S50.shift(5)),
    ('Close > SMA50 > SMA200', (C > S50) & (S50 > S200)),
    # --- Volatility (descriptive)
    ('ATR top-10% days', df['atr14'] >= df['atr14'].quantile(0.90)),
    ('ATR bottom-10% days', df['atr14'] <= df['atr14'].quantile(0.10)),
    # --- Regime
    ('Regime TREND UP', df['regime'] == 'TREND UP'),
    ('Regime TREND DOWN', df['regime'] == 'TREND DOWN'),
    ('Regime RANGE', df['regime'] == 'RANGE'),
    ('Regime CHOP', df['regime'] == 'CHOP'),
    # --- Divergence
    ('BULL_DIV day', df['div'] == 'BULL_DIV'),
    ('BEAR_DIV day', df['div'] == 'BEAR_DIV'),
]

rows = []
for name, mask in MASKS:
    idxs = list(df[mask].index)
    if len(idxs) < 5:
        continue
    f5 = [fwd(i, 5) for i in idxs]
    f20 = [fwd(i, 20) for i in idxs]
    f5 = [v for v in f5 if not np.isnan(v)]
    f20 = [v for v in f20 if not np.isnan(v)]
    in_today = bool(mask.iloc[-1]) if hasattr(mask, 'iloc') else bool(mask[-1])
    rows.append({
        'Parameter_State': name,
        '%_din': round(100 * len(idxs) / n, 2),
        '+5d_avg': round(float(np.mean(f5)), 2) if f5 else None,
        '+5d_win%': round(100 * np.mean(np.array(f5) > 0), 0) if f5 else None,
        '+20d_avg': round(float(np.mean(f20)), 2) if f20 else None,
        '+20d_win%': round(100 * np.mean(np.array(f20) > 0), 0) if f20 else None,
        'aaj_is_state_mein?': 'YES' if in_today else '',
    })

res = pd.DataFrame(rows)
print(f"{'Parameter_State':<28}{'%din':>6}{'+5d':>8}{'w5':>6}{'+20d':>8}{'w20':>6}  aaj")
for _, r in res.iterrows():
    print(f"{r['Parameter_State']:<28}{r['%_din']:>5.1f}%{r['+5d_avg']:>+7.2f}{r['+5d_win%']:>5.0f}%{r['+20d_avg']:>+7.2f}{r['+20d_win%']:>5.0f}%  {r['aaj_is_state_mein?']}")

# append sheet to master xlsx
try:
    with pd.ExcelWriter(XLSX, engine='openpyxl', mode='a', if_sheet_exists='replace') as w:
        res.to_excel(w, sheet_name='Parameter_Edge_Analysis', index=False)
    import shutil
    shutil.copy(XLSX, COPY_TO)
    print('\nxlsx updated + copied ->', XLSX)
except Exception as e:
    print('xlsx append failed:', e)
