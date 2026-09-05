"""SMA200 gate variants — yearly + monthly tables (6M-MOM-21).

Variant A: NIFTY < SMA200 at month-end rebalance => 50% exposure, else 100%.
Variant B: NIFTY < SMA200 => 0% (cash).
Variant C: baseline (no gate).
Yearly table + gate-on months + worst months + 2026 detail.
"""
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

nd=pd.read_csv(DAILY, parse_dates=['Date']).set_index('Date')['Close']
sma=nd.rolling(200).mean()

def run(gate_mode, expo_below):
    prev_top=None; daily=[]; mlog=[]
    for i in range(H, len(dates)-1):
        dt=dates[i]
        hist=nd.loc[:dt]; hs=sma.loc[:dt].dropna()
        below = bool(hist.iloc[-1] < hs.iloc[-1]) if len(hs)>0 and not np.isnan(hs.iloc[-1]) else False
        if gate_mode=='none':
            expo=1.0
        elif gate_mode=='sma':
            expo = expo_below if below else 1.0
        mrow=mom.iloc[i].dropna()
        if len(mrow)<10: continue
        k=max(1,int(round(len(mrow)*0.25)))
        top=mrow.nlargest(k).index
        seg=px.loc[dt:dates[i+1], top]
        nxt=me.iloc[i+1].reindex(top).dropna(); cur=me.iloc[i].reindex(top).dropna()
        r=(nxt/cur-1).replace([np.inf,-np.inf],np.nan).dropna()
        if len(r)<1: continue
        dseg=seg.ffill().pct_change().dropna().replace([np.inf,-np.inf],np.nan)
        dret=dseg.mean(axis=1)*expo
        chg=len(set(top)-(prev_top or set())) if prev_top is not None else len(top)
        if chg>0: dret.iloc[0]-= 0.001*chg/len(top)*expo
        daily.append(dret)
        mlog.append((dt, bool(below) if gate_mode=='sma' else False, expo, (1+dret).prod()-1))
        prev_top=set(top)
    r=pd.concat(daily); eq=(1+r).cumprod()
    return eq,r,pd.DataFrame(mlog,columns=['date','below','expo','mret'])

def summary(eq,r,ml,label):
    yrs=len(r)/252
    tot=(eq.iloc[-1]-1)*100
    cagr=(eq.iloc[-1]**(1/yrs)-1)*100
    sharpe=r.mean()/r.std()*np.sqrt(252)
    dd=((eq/eq.cummax())-1).min()*100
    return dict(label=label,tot=tot,cagr=cagr,sharpe=sharpe,dd=dd)

# ---- yearly table across variants ----
def yearly(ml):
    y=ml.copy(); y['year']=pd.to_datetime(y['date']).dt.year
    return y.groupby('year')['mret'].apply(lambda x:(1+x).prod()-1)

res={}
eqA,rA,mlA=run('sma',0.5)
eqB,rB,mlB=run('sma',0.0)
eqC,rC,mlC=run('none',0.0)
res['SMA-50%']=(eqA,rA,mlA); res['SMA-CASH']=(eqB,rB,mlB); res['BASELINE']=(eqC,rC,mlC)

print("="*110)
print("YEARLY — 6M-MOM-21 baseline vs SMA200 gate (0.1% rt, daily path)")
print("="*110)
ya=yearly(mlA); yb=yearly(mlB); yc=yearly(mlC)
print(f"{'year':<6}{'BASELINE':>10}{'SMA-50%':>10}{'SMA-CASH':>10}{'NIFTY':>10}")
nif_yr = nd.resample('YE').apply(lambda x: (1+x.pct_change().dropna()).prod()-1)
for y in yc.index:
    nv = nif_yr.get(y, np.nan)
    print(f"{y:<6}{yc.get(y,np.nan)*100:>+9.1f}%{ya.get(y,np.nan)*100:>+9.1f}%{yb.get(y,np.nan)*100:>+9.1f}%{nv*100:>+9.1f}%")

print("\n"+"="*110)
print("SUMMARY")
print("="*110)
for lbl,(eq,r,ml) in res.items():
    s=summary(eq,r,ml,lbl)
    print(f"{lbl:<12} total {s['tot']:>+8.1f}%  CAGR {s['cagr']:>+6.1f}%  Sharpe {s['sharpe']:>5.2f}  MDD {s['dd']:>+6.1f}%")

# ---- gate months ----
print("\n"+"="*110)
print("GATE-ON months (NIFTY < SMA200 at rebalance) — SMA-50% kab 50% pe tha")
print("="*110)
gon=mlA[mlA['below']]
print(f"total gate-on months: {len(gon)} of {len(mlA)} ({100*len(gon)/len(mlA):.0f}%)")
for _,x in gon.iterrows():
    print(f"  {x['date'].date()}  expo {x['expo']:.0%}  month {x['mret']*100:+.1f}%")

# ---- 2026 month-wise detail (all variants) ----
print("\n"+"="*110)
print("2026 month-wise")
print("="*110)
m26=mlC[mlC['date'].dt.year==2026]
for _,x in m26.iterrows():
    dt=x['date']
    a=mlA[mlA['date']==dt]['mret'].iloc[0]
    b=mlB[mlB['date']==dt]['mret'].iloc[0]
    flag='GATE-ON' if dt in set(gon['date']) else ''
    print(f"  {dt.date()}  base {x['mret']*100:+7.1f}%  SMA50 {a*100:+7.1f}%  SMAcash {b*100:+7.1f}%  {flag}")

# ---- worst months baseline ----
print("\nworst 8 months baseline:")
wm=mlC.sort_values('mret').head(8)
for _,x in wm.iterrows():
    dt=x['date']
    a=mlA[mlA['date']==dt]['mret'].iloc[0] if dt in set(mlA['date']) else np.nan
    print(f"  {dt.date()}  base {x['mret']*100:+6.1f}%  SMA50 {a*100:+6.1f}%")
