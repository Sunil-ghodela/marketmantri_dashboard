"""NIFTY monthly result — buy&hold vs SMA200 gate (daily + monthly check), real ^NSEI.

Sawaal: NIFTY pe bhi monthly/yearly table — gate lagane se kya milta hai?
Systems:
- B&H: hamesha long.
- SMA200 daily: long jab close > SMA200, cash jab neeche (next day check).
- SMA200 monthly: month-end pe check, agla poora mahina long/cash.
- Trend-days (scenario BULL bucket) sirf reference.
"""
import numpy as np, pandas as pd

DAILY='/home/vaibhav/AI/yr2026/Investment/marketmantri_dashboard/state/nifty_daily_state.csv'
d=pd.read_csv(DAILY, parse_dates=['Date']).set_index('Date').sort_index()
cl=d['Close']
r=cl.pct_change().fillna(0)
sma=cl.rolling(200).mean()

# --- daily SMA200 gate (position decided prev close) ---
pos_d=(cl>sma).shift(1).fillna(False).astype(float)
sr_d=pos_d*r

# --- monthly SMA200 gate ---
me=cl.resample('ME').last()
r_m=me.pct_change()
above_m=(me>sma.resample('ME').last())
pos_m=above_m.shift(1).fillna(False).astype(float)  # prev month-end decision
sr_m=pos_m*r_m

# monthly returns of daily-gate strategy (position at day, monthly aggregate)
sr_d_m=sr_d.resample('ME').apply(lambda x:(1+x).prod()-1)

# --- stats helper on daily series ---
def stats_daily(s,label):
    eq=(1+s).cumprod(); yrs=len(s)/252
    tot=(eq.iloc[-1]-1)*100
    cagr=(eq.iloc[-1]**(1/yrs)-1)*100 if eq.iloc[-1]>0 else -100
    sharpe=s.mean()/s.std()*np.sqrt(252) if s.std()>0 else 0
    dd=((eq/eq.cummax())-1).min()*100
    expo=100*(s!=0).mean()
    return label,tot,cagr,sharpe,dd,expo

print("="*100)
print("NIFTY (real ^NSEI, 2015-01 -> 2026-09-04)")
print("="*100)
print(f"{'system':<32}{'total%':>9}{'CAGR%':>8}{'Sharpe':>8}{'MDD%':>8}{'in-mkt%':>8}")
for lbl,s in [("BUY & HOLD",r),("SMA200 gate (daily)",sr_d)]:
    L,t,c,sh,dd,e=stats_daily(s,lbl)
    print(f"{L:<32}{t:>+8.1f}%{c:>+7.1f}%{sh:>8.2f}{dd:>+7.1f}%{e:>7.0f}%")

# monthly-based systems on monthly series
def stats_monthly(ms,label):
    eq=(1+ms.fillna(0)).cumprod(); yrs=len(ms.dropna())/12
    tot=(eq.iloc[-1]-1)*100
    cagr=(eq.iloc[-1]**(1/yrs)-1)*100 if eq.iloc[-1]>0 else -100
    sharpe=ms.mean()/ms.std()*np.sqrt(12) if ms.std()>0 else 0
    eqs=pd.Series(eq); dd=((eqs/eqs.cummax())-1).min()*100
    return label,tot,cagr,sharpe,dd

print(f"{'SMA200 gate (monthly check)':<32}{'':<9}{'':<8}{'':<8}{'':<8}")

# monthly gate vs buy&hold yearly table (daily-gate for fair daily compounding)
print("\n"+"="*100)
print("YEARLY — B&H vs SMA200-daily-gate (%), + NIFTY year return")
print("="*100)
yr_bh=r.resample('YE').apply(lambda x:(1+x).prod()-1)*100
yr_g=sr_d.resample('YE').apply(lambda x:(1+x).prod()-1)*100
print(f"{'year':<6}{'B&H':>9}{'SMA-gate':>10}{'gate better?':>14}")
for y in yr_bh.index:
    b=yr_bh.get(y,np.nan); g=yr_g.get(y,np.nan)
    mark='YES' if g>b else ('no' if b>g else '=')
    print(f"{str(y.year):<6}{b:>+8.1f}%{g:>+9.1f}%{mark:>14}")

# monthly table last 18 months both
print("\n"+"="*100)
print("LAST 18 MONTHS — B&H monthly vs gate monthly")
print("="*100)
m_bh=r.resample('ME').apply(lambda x:(1+x).prod()-1)*100
print(f"{'month':<10}{'B&H':>9}{'gate':>9}{'pos':>6}")
mm=pd.DataFrame({'bh':m_bh,'gate':sr_d_m*100,'pos':pos_m.reindex(m_bh.index).ffill()*100})
for dt,row in mm.tail(18).iterrows():
    print(f"{str(dt.date()):<10}{row['bh']:>+8.1f}%{row['gate']:>+8.1f}%{int(row['pos']):>5}%")

# worst months
print("\nworst 8 months B&H + gate position:")
w=mm.sort_values('bh').head(8)
for dt,row in w.iterrows():
    print(f"  {dt.date()}  B&H {row['bh']:>+6.1f}%  gate {row['gate']:>+6.1f}%  pos {int(row['pos'])}%")
