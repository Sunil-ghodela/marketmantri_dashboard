import re, os
import numpy as np, pandas as pd
ARCHIVE='/home/vaibhav/AI/yr2026/MarketMantri/data_sources/archive-data'
FEED='/home/vaibhav/AI/yr2026/MarketMantri/core/momentum_portfolio_feed.py'
DAILY='/home/vaibhav/AI/yr2026/Investment/marketmantri_dashboard/state/nifty_daily_state.csv'
src=open(FEED).read()
m=re.search(r"WATCH = \[(.*?)\]", src, re.S)
SYMS=re.findall(r"['\"]([A-Z0-9&\-]+)['\"]", m.group(1))
def dc(sym):
    f=os.path.join(ARCHIVE, f'{sym}_5minute.csv')
    if not os.path.exists(f): return None
    df=pd.read_csv(f, usecols=['date','close'], parse_dates=['date'])
    d=df.groupby(df['date'].dt.date)['close'].last()
    d.index=pd.to_datetime(d.index); return d.sort_index()
cl={s:dc(s) for s in SYMS}
cl={s:d for s,d in cl.items() if d is not None and len(d)>500}
px=pd.DataFrame(cl).sort_index().loc['2015-08-01':]
me=px.resample('ME').last()
dates=me.index
H=6
mom=me/me.shift(H)-1

# NIFTY daily scenario monthly summary
nd=pd.read_csv(DAILY, parse_dates=['Date']).set_index('Date')
nd['ym']=nd.index.to_period('M')
last_scn=nd.groupby('ym')['scenario'].last()
nifty_close_daily=nd['Close']
# NIFTY SMA200
nifty_sma200=nifty_close_daily.rolling(200).mean()

# 2026 month-wise baseline + what gate said
print("="*100)
print("2026 month-wise — baseline 6M-MOM-21 + NIFTY prev-month scenario")
print("="*100)
print(f"{'rebalance @':<13}{'NIFTY prev-mo':<16}{'mkt ret':>8}")
for i in range(H, len(dates)-1):
    if dates[i].year!=2026: continue
    ym=pd.Period(dates[i],freq='M'); pm=ym-1
    ls=last_scn.get(pm,'?')
    ncl=nifty_close_daily.loc[:dates[i]]
    above=bool(ncl.iloc[-1]>nifty_sma200.loc[:dates[i]].iloc[-1]) if len(ncl)>200 else None
    print(f"{str(dates[i].date()):<13}{ls:<16}  SMA200: {'above' if above else 'BELOW' if above is not None else '?'}")

# NIFTY scenario counts by month (BEAR-ish months history)
print("\nNIFTY BEAR/AVOID/CHOP-DOWN months (last-day scenario):")
bear_mo=last_scn[last_scn.isin(['BEAR','WEAK','PANIC','TOP-WARNING','CHOP-DOWN'])]
print(bear_mo.to_string())

# variant: gate on NIFTY below SMA200 at rebalance
def run_sma(expo_closed):
    prev_top=None; daily=[]
    for i in range(H, len(dates)-1):
        ncl=nifty_close_daily.loc[:dates[i]]
        sma=nifty_sma200.loc[:dates[i]]
        if len(sma)<200 or np.isnan(sma.iloc[-1]):
            expo=1.0
        else:
            expo=expo_closed if ncl.iloc[-1]<sma.iloc[-1] else 1.0
        mrow=mom.iloc[i].dropna()
        if len(mrow)<10: continue
        k=max(1,int(round(len(mrow)*0.25)))
        top=mrow.nlargest(k).index
        seg=px.loc[dates[i]:dates[i+1], top]
        nxt=me.iloc[i+1].reindex(top).dropna(); cur=me.iloc[i].reindex(top).dropna()
        r=(nxt/cur-1).replace([np.inf,-np.inf],np.nan).dropna()
        if len(r)<1: continue
        dseg=seg.ffill().pct_change().dropna().replace([np.inf,-np.inf],np.nan)
        dret=dseg.mean(axis=1)*expo
        chg=len(set(top)-(prev_top or set())) if prev_top is not None else len(top)
        if chg>0: dret.iloc[0]-= 0.001*chg/len(top)*expo
        daily.append(dret); prev_top=set(top)
    r=pd.concat(daily); eq=(1+r).cumprod()
    yrs=len(r)/252
    tot=(eq.iloc[-1]-1)*100
    cagr=(eq.iloc[-1]**(1/yrs)-1)*100
    sharpe=r.mean()/r.std()*np.sqrt(252)
    dd=((eq/eq.cummax())-1).min()*100
    return tot,cagr,sharpe,dd,eq

print("\n"+"="*100)
print("Gate variant: NIFTY < SMA200 at rebalance => CASH (monthly)")
print("="*100)
for expo in [0.0,0.5]:
    t,c,s,d,eq=run_sma(expo)
    ml='CASH' if expo==0 else '50%'
    print(f"NIFTY<SMA200 => {ml}: total {t:>+8.1f}% CAGR {c:>+6.1f}% Sharpe {s:>5.2f} MDD {d:>+6.1f}%")
# baseline reference for equity curve date of COVID dd
