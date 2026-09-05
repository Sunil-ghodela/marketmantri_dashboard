"""Momentum horizon scan — 90-name WATCH universe (feed.py), archive 5-min data.

Sawaal: 1/2/3/4/5/6-month momentum, monthly rebalance, top-25% hold 1 month —
kaunsa horizon chalata hai? (10-name test: 6-mo momentum + monthly hold ≈ index.)

Method:
- 5-min archive (2015-02 -> 2026-04-09) se daily close per stock (real data).
- Har month-end: momentum = close / close[H months ago] - 1 (fraction). Top-25%
  names lo, 1 month hold, equal weight, agli month-end rebalance.
- Cost: 0.1% round-trip on churned names (sirf names jo portfolio badle).
- Benchmark: NIFTY50 (daily state CSV se) same window + universe EW.
"""
import os
import re
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ARCHIVE = "/home/vaibhav/AI/yr2026/MarketMantri/data_sources/archive-data"
FEED = "/home/vaibhav/AI/yr2026/MarketMantri/core/momentum_portfolio_feed.py"
DAILY = os.path.join(os.path.dirname(HERE), "nifty_daily_state.csv")

src = open(FEED).read()
m = re.search(r"WATCH = \[(.*?)\]", src, re.S)
SYMS = re.findall(r"['\"]([A-Z0-9&\-]+)['\"]", m.group(1))
print(f"universe: {len(SYMS)} names")


def daily_close(sym):
    f = os.path.join(ARCHIVE, f"{sym}_5minute.csv")
    if not os.path.exists(f):
        return None
    df = pd.read_csv(f, usecols=["date", "close"], parse_dates=["date"])
    d = df.groupby(df["date"].dt.date)["close"].last()
    d.index = pd.to_datetime(d.index)
    return d.sort_index()


closes = {}
for sym in SYMS:
    d = daily_close(sym)
    if d is not None and len(d) > 500:
        closes[sym] = d
print(f"daily series loaded: {len(closes)}/{len(SYMS)}")

px = pd.DataFrame(closes).sort_index()
px = px.loc["2015-08-01":]
print(f"price matrix: {px.shape[0]} days x {px.shape[1]} names  "
      f"({px.index[0].date()} -> {px.index[-1].date()})")

me = px.resample("ME").last()
dates = me.index

results = []
for H in [1, 2, 3, 4, 5, 6]:
    mom = me / me.shift(H) - 1               # momentum H months (fraction)
    prev_top = None
    mo_rets = []
    n_hold = []
    for i in range(H, len(dates) - 1):       # signal month-end i, hold i -> i+1
        mrow = mom.iloc[i].dropna()
        if len(mrow) < 10:
            continue
        k = max(1, int(round(len(mrow) * 0.25)))
        top = mrow.nlargest(k).index
        nxt = me.iloc[i + 1].reindex(top).dropna()
        cur = me.iloc[i].reindex(top).dropna()
        r = (nxt / cur - 1)                  # actual next-month returns (fraction)
        r = r.replace([np.inf, -np.inf], np.nan).dropna()
        if len(r) < 1:
            continue
        chg = len(set(top) - (prev_top or set())) if prev_top is not None else len(top)
        cost = chg * 0.001 / len(r)          # 0.1% rt on churned names / EW split
        mo_rets.append(float(r.mean()) - cost)
        prev_top = set(top)
        n_hold.append(len(r))
    mo = pd.Series(mo_rets)
    eq = (1 + mo).cumprod()
    yrs = len(mo) / 12
    tot = (eq.iloc[-1] - 1) * 100
    cagr = (eq.iloc[-1] ** (1 / yrs) - 1) * 100 if eq.iloc[-1] > 0 else -100
    sharpe = mo.mean() / mo.std() * np.sqrt(12) if mo.std() > 0 else 0
    dd = ((eq / eq.cummax()) - 1).min() * 100
    results.append(dict(H=H, months=len(mo), tot=tot, cagr=cagr, sharpe=sharpe,
                        mdd=dd, n_hold=int(np.mean(n_hold)) if n_hold else 0))
    print(f"{H}-mo: months={len(mo):>3}  total {tot:>+8.1f}%  CAGR {cagr:>+6.1f}%  "
          f"Sharpe {sharpe:>5.2f}  MDD {dd:>+6.1f}%  avg hold {int(np.mean(n_hold)) if n_hold else 0} names")

# ---- benchmarks (same active window ~2016-02 -> 2026-04) ----
nif = pd.read_csv(DAILY, parse_dates=["Date"]).set_index("Date")["Close"]
nif = nif.loc["2016-02-01":"2026-04-09"]
nif_me = nif.resample("ME").last()
r = nif_me.pct_change().dropna()
eq_n = (1 + r).cumprod()
yrs = len(r) / 12
ew_me = px.resample("ME").last().pct_change().mean(axis=1).dropna()
eq_ew = (1 + ew_me).cumprod()
print("\nbenchmarks (2016-02 -> 2026-04):")
print(f"NIFTY50:   total {(eq_n.iloc[-1]-1)*100:>+8.1f}%  CAGR {(eq_n.iloc[-1]**(1/yrs)-1)*100:>+6.1f}%  "
      f"Sharpe {r.mean()/r.std()*np.sqrt(12):>5.2f}")
print(f"Universe EW buy&hold: total {(eq_ew.iloc[-1]-1)*100:>+8.1f}%")

out = pd.DataFrame(results).set_index("H")
out.to_csv(os.path.join(HERE, "momentum_horizon_results.csv"))
print("\nsaved -> momentum_horizon_results.csv")
