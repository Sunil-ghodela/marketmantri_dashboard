"""Export EVERY technical parameter into one file.

Sheets:
  1. Daily_2015_2026  -> har din ke saare technical values (3,047 rows)
  2. Aaj_Summary       -> aaj ke saare parameters + 11-saal ka min/max/avg + matlab
  3. Parameter_Guide   -> har parameter ka formula aur value kaise badalti hai

Output: state/technical_parameters_full.xlsx (+ copy to Downloads/meeting_notes)
"""
import os
import sys
import shutil
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_state as bs

OUT_XLSX = os.path.join(HERE, 'technical_parameters_full.xlsx')
COPY_TO = '/home/vaibhav/Downloads/meeting_notes/technical_parameters_full.xlsx'

df = bs.load_prices()
df = bs.add_indicators(df)

# ---------- full daily sheet ----------
cols = ['Date', 'Open', 'High', 'Low', 'Close', 'sma50', 'sma200', 'atr14',
        'chop14', 'adx14', 'di_plus', 'di_minus', 'macd', 'signal', 'macd_hist',
        'rsi14', 'rsi_zone', 'regime', 'macd_cross', 'div',
        'month_so_far_pct', 'ytd_pct', 'ret_1y_pct', 'off_ath_pct',
        'daily_ret', 'Event']
daily = df[cols].copy()
daily.columns = ['Date', 'Open', 'High', 'Low', 'Close', 'SMA50', 'SMA200',
                 'ATR14', 'Chop14', 'ADX14', '+DI14', '-DI14', 'MACD', 'MACD_signal',
                 'MACD_hist', 'RSI14', 'RSI_zone', 'Regime', 'MACD_cross',
                 'Divergence', 'Month_so_far_%', 'YTD_%', '1yr_%', 'from_ATH_%',
                 'daily_ret_%', 'News']
daily['Date'] = pd.to_datetime(daily['Date']).dt.strftime('%Y-%m-%d')

# ---------- guide ----------
GUIDE = [
    ('Close', 'Din ka last price', 'Price data (Yahoo ^NSEI / xlsx)', '—'),
    ('SMA50', '50 din ka average price — short-term rukh', '50 din ke closes ka average', 'Price upar hai toh uptrend filter'),
    ('SMA200', '200 din ka average — long-term rukh', '200 din ke closes ka average', 'Upar = long-term bull, neeche = bear'),
    ('ATR14', 'Volatility — din kitna hilta hai', 'Avg True Range (high-low, gap-adjusted) 14 din Wilder smooth', 'Crash/news mein badhta hai, quiet mein ghatta hai'),
    ('Chop14', 'Choppiness 0-100 — sidha chal raha ya idhar-udhar', '100*log10(sum ATR14 / 14-din high-low range)/log10(14)', '>61.8 chop, <38.2 clean trend'),
    ('ADX14', 'Trend strength 0-100', '100*|+DI - -DI| / (+DI + -DI) smoothed 14 din', '>=25 trend, kam = no trend'),
    ('+DI14', 'Upward directional pressure', '100 * smoothed +DM / ATR14', '+DI > -DI = up pressure'),
    ('-DI14', 'Downward directional pressure', '100 * smoothed -DM / ATR14', '-DI > +DI = down pressure'),
    ('MACD', 'Momentum line', 'EMA12 - EMA26', 'Upar jaaye = momentum strong hota'),
    ('MACD_signal', 'MACD ka 9-din average (trigger line)', 'EMA9 of MACD', 'MACD vs signal = cross signal'),
    ('MACD_hist', 'MACD - signal — momentum direction+speed', 'MACD line minus signal line', '+ = bullish, - = bearish; sign flip = CROSS'),
    ('RSI14', 'Momentum health 0-100', '100 - 100/(1 + avg gain / avg loss) 14 din', '>70 overbought, <30 oversold, 50 = neutral'),
    ('RSI_zone', 'RSI ki zone', 'RSI se', 'OVERBOUGHT / NEUTRAL / OVERSOLD'),
    ('Regime', 'Market ka mode', 'ADX + Choppiness + DI direction', 'TREND UP / TREND DOWN / RANGE / CHOP'),
    ('MACD_cross', 'Histogram ka sign flip', 'MACD_hist sign change', 'CROSS_UP ▲ = buy bias, CROSS_DOWN ▼ = sell bias'),
    ('Divergence', 'RSI pivot divergence', 'Price high/low vs RSI opposite', 'BULL_DIV (bottom pe), BEAR_DIV (top pe)'),
    ('Month_so_far_%', 'Is mahine ka return', 'close / month-start - 1', 'Mahine ki position'),
    ('YTD_%', 'Saal bhar ka return', 'close / last year close - 1', 'Saal ki position'),
    ('1yr_%', 'Pichhle 252 din ka return', 'close / close 252 din pehle - 1', 'Rolling 1-saal return'),
    ('from_ATH_%', 'All-time high se doori', 'close / cummax close - 1', '-10% = ATH se 10% neeche'),
    ('daily_ret_%', 'Kal se aaj ka %', 'close pct change', 'Roz ka move'),
]
guide = pd.DataFrame(GUIDE, columns=['Parameter', 'Kya hai', 'Formula', 'Kaise badalti hai'])
MEAN = {g[0]: g[1] for g in GUIDE}

# ---------- today summary ----------
ld = df.iloc[-1]
today_row = {'Date': ld['Date'].strftime('%Y-%m-%d')}

def num_stats(s):
    s = pd.to_numeric(s, errors='coerce').dropna()
    if len(s) == 0:
        return None, None, None
    return round(float(s.min()), 2), round(float(s.max()), 2), round(float(s.mean()), 2)

summary_rows = []
text_params = {'Regime': ld['regime'], 'RSI_zone': ld['rsi_zone'],
               'MACD_cross': ld['macd_cross'] or '-', 'Divergence': ld['div'] or '-'}
for key, name, *_ in [(g[0], g[0]) for g in GUIDE]:
    if key in ('Date',) or key in text_params:
        continue
    col = {'Close': 'Close', 'SMA50': 'sma50', 'SMA200': 'sma200', 'ATR14': 'atr14',
           'Chop14': 'chop14', 'ADX14': 'adx14', '+DI14': 'di_plus', '-DI14': 'di_minus',
           'MACD': 'macd', 'MACD_signal': 'signal', 'MACD_hist': 'macd_hist',
           'RSI14': 'rsi14', 'Month_so_far_%': 'month_so_far_pct', 'YTD_%': 'ytd_pct',
           '1yr_%': 'ret_1y_pct', 'from_ATH_%': 'off_ath_pct', 'daily_ret_%': 'daily_ret'}[key]
    cur = ld[col]
    cur = None if pd.isna(cur) else round(float(cur), 2)
    mn, mx, avg = num_stats(df[col])
    meaning = MEAN[key]
    summary_rows.append({
        'Parameter': key, 'Aaj_value': cur, 'Min_11saal': mn, 'Max_11saal': mx,
        'Avg_11saal': avg, 'Matlab': meaning})
for key, val in text_params.items():
    summary_rows.append({'Parameter': key, 'Aaj_value': val, 'Min_11saal': '-',
                         'Max_11saal': '-', 'Avg_11saal': '-', 'Matlab': MEAN[key]})
summary = pd.DataFrame(summary_rows)

with pd.ExcelWriter(OUT_XLSX, engine='openpyxl') as w:
    daily.to_excel(w, sheet_name='Daily_2015_2026', index=False)
    summary.to_excel(w, sheet_name='Aaj_Summary', index=False)
    guide.to_excel(w, sheet_name='Parameter_Guide', index=False)

print('xlsx ->', OUT_XLSX)
try:
    os.makedirs(os.path.dirname(COPY_TO), exist_ok=True)
    shutil.copy(OUT_XLSX, COPY_TO)
    print('copy ->', COPY_TO)
except Exception as e:
    print('copy failed:', e)

print()
print('=== AAJ KI SAB VALUES (%s) ===' % ld['Date'].strftime('%d %b %Y'))
for r in summary_rows:
    print(f"  {r['Parameter']:<16} {str(r['Aaj_value']):<10} {r['Matlab'][:48]}")
print()
print('sheets: Daily_2015_2026 (%d rows) | Aaj_Summary | Parameter_Guide' % len(daily))