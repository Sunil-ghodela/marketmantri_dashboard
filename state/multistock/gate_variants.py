"""6-mo momentum + NIFTY BULL-LEAN regime gate variants.

Sawaal:
1. 30-40% DD kab hua (month-wise losses)?
2. 6M-MOM-21 pe NIFTY prev-month stage gate lagane se kya badalta hai?
   Variants: skip (cash) ya 50% cash jab prev month NIFTY BEAR/AVOID.
3. Yearly table + 2026 month-wise (gate ne kitna bachaya).
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

# ---- NIFTY daily scenario -> prev-month gate ----
nd=pd.read_csv(DAILY, parse_dates=['Date']).set_index('Date')
nd['ym']=nd.index.to_period('M')
# per month: last trading day ka scenario + BEAR-ish day share
last_scn=nd.groupby('ym')['scenario'].last()
bearish_share=nd.groupby('ym')['scenario'].apply(lambda s: s.isin(['BEAR','WEAK','PANIC','TOP-WARNING','CHOP-DOWN']).mean())
gate_month=pd.DataFrame({'last_scn':last_scn,'bear_share':bearish_share})
gate_month.index.name='ym'

# map each month-end date -> its period, and prev month's gate
def gate_for(dt, mode):
    ym=pd.Period(dt, freq='M')
    pm=ym-1
    if pm not in gate_month.index: return 'open'
    ls=gate_month.loc[pm,'last_scn']
    if mode=='strict':      # prev month last day BEAR/AVOID => gate
        return 'closed' if ls in ['BEAR','WEAK','PANIC','TOP-WARNING'] else 'open'
    if mode=='chopdown':    # + CHOP-DOWN
        return 'closed' if ls in ['BEAR','WEAK','PANIC','TOP-WARNING','CHOP-DOWN'] else 'open'
    if mode=='bear_share':  # >=40% din bearish prev month
        return 'closed' if gate_month.loc[pm,'bear_share']>=0.40 else 'open'
    return 'open'

def run(mode, exposure_closed=0.0, cost_rt=0.001):
    """Daily equity, monthly rebalance; gate se pura exposure 0 (skip) ya 50%."""
    prev_top=None
    daily_ret=[]
    months_log=[]
    for i in range(H, len(dates)-1):
        g=gate_for(dates[i], mode)
        mrow=mom.iloc[i].dropna()
        if len(mrow)<10: continue
        k=max(1,int(round(len(mrow)*0.25)))
        top=mrow.nlargest(k).index
        seg=px.loc[dates[i]:dates[i+1], top]
        nxt=me.iloc[i+1].reindex(top).dropna(); cur=me.iloc[i].reindex(top).dropna()
        r=(nxt/cur-1).replace([np.inf,-np.inf],np.nan).dropna()
        if len(r)<1: continue
        dseg=seg.ffill().pct_change().dropna().replace([np.inf,-np.inf],np.nan)
        dret=dseg.mean(axis=1)
        expo = exposure_closed if g=='closed' else 1.0
        dret=dret*expo
        chg=len(set(top)-(prev_top or set())) if prev_top is not None else len(top)
        if chg>0:
            dret.iloc[0]-= cost_rt*chg/len(top)*expo
        daily_ret.append(dret)
        # month log: equity change approx by compounded dret
        months_log.append((dates[i], g, (1+dret).prod()-1, len(top)))
        prev_top=set(top)
    r=pd.concat(daily_ret)
    eq=(1+r).cumprod()
    return eq,r,pd.DataFrame(months_log,columns=['date','gate','mret','n'])

print("="*100)
print("6M-MOM-21 baseline + gate variants (0.1% rt churn)")
print("="*100)
res={}
for mode,label in [('open','BASELINE (no gate)'),('strict','GATE: prev-mo BEAR/AVOID => CASH'),
                   ('strict_half','GATE: prev-mo BEAR/AVOID => 50%'),('chopdown','GATE: prev-mo BEAR/CHOP-DOWN => CASH')]:
    expo=0.0 if mode!='strict_half' else 0.5
    mkey=mode.replace('_half','') if mode!='strict_half' else 'strict'
    eq,r,ml=run(mkey, expo)
    yrs=len(r)/252
    tot=(eq.iloc[-1]-1)*100
    cagr=(eq.iloc[-1]**(1/yrs)-1)*100 if eq.iloc[-1]>0 else -100
    sharpe=r.mean()/r.std()*np.sqrt(252) if r.std()>0 else 0
    dd=((eq/eq.cummax())-1).min()*100
    res[label]=dict(eq=eq,r=r,ml=ml)
    print(f"{label:<42} total {tot:>+8.1f}%  CAGR {cagr:>+6.1f}%  Sharpe {sharpe:>5.2f}  DAILY MDD {dd:>+6.1f}%")
    # yearly
    yl=ml.copy(); yl['year']=pd.to_datetime(yl['date']).dt.year
    gy=yl.groupby('year')['mret'].apply(lambda x:(1+x).prod()-1)
    print('   green years:', int((gy>0).sum()),'/',len(gy), '| worst year:', gy.idxmin(), round(gy.min()*100,1),'%')

# ---- where are losses: baseline monthly table ----
print("\n"+"="*100)
print("BASELINE — monthly returns, big loss months + 2026 month-wise")
print("="*100)
ml=res['BASELINE (no gate)']['ml']
ml['mret']=ml['mret']
big=ml[ml['mret']<-0.05].sort_values('mret')
print("months with <-5%:")
for _,x in big.iterrows():
    print(f"  {x['date'].date()}  {x['mret']*100:>+6.1f}%")
# drawdown periods on equity
eq=res['BASELINE (no gate)']['eq']
cummax=eq.cummax(); dd=(eq/cummax)-1
# find drawdown episodes
in_dd=False; start=None
eps=[]
for dt,v in dd.items():
    if v<0 and not in_dd:
        in_dd=True; start=cummax.loc[:dt].idxmax()
    elif v>=0 and in_dd:
        eps.append((start,dt,dd.loc[start:dt].min())); in_dd=False
if in_dd: eps.append((start,dd.index[-1],dd.loc[start:].min()))
eps.sort(key=lambda e:e[2])
print("\ntop 5 drawdown episodes (baseline):")
for s,e,v in eps[:5]:
    print(f"  {v*100:>+6.1f}%  {s.date()} -> {e.date()}")
