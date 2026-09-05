"""Momentum forward paper runner — 6M-MOM-21-SMA50 (PRE-REGISTERED 5 Sep 2026).

Rules (docs/MOMENTUM_FORWARD_PAPER_PRE.md):
- Universe: 90-name WATCH. Month-end close pe 6-mo momentum rank, top-25% (~21),
  equal weight. Hold 1 month, koi intra-month exit/stop nahi.
- Gate: usi din NIFTY close < SMA200 => exposure 50%, warna 100%.
- Cost: 0.1% rt churn per changed name. Report gross AND net.
- Log: momentum_paper_log.csv append-only. Pehli rebalance 30 Sep 2026.

Usage:
  python3 momentum_paper.py            # agla month-end aaya? rebalance karo
  python3 momentum_paper.py --report   # current log summary
  python3 momentum_paper.py --force    # is month-end ka portfolio dikhao (dry)
"""
import os
import sys
import json
import datetime
import argparse

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "momentum_paper_log.csv")
STATE = os.path.join(HERE, "momentum_paper_state.json")

SYMBOLS = [
    'RELIANCE','HDFCBANK','ICICIBANK','INFY','TCS','ITC','SBIN','KOTAKBANK','BHARTIARTL','LT',
    'AXISBANK','BAJFINANCE','BAJAJFINSV','MARUTI','ASIANPAINT','HINDUNILVR','SUNPHARMA','TITAN',
    'ULTRACEMCO','NESTLEIND','WIPRO','HCLTECH','TATASTEEL','TMPV','MM','POWERGRID','NTPC','ONGC',
    'COALINDIA','JSWSTEEL','ADANIPORTS','GRASIM','CIPLA','TECHM','HAL','CHOLAFIN','MUTHOOTFIN',
    'MAZDOCK','DMART','MOTHERSON','TVSMOTOR','SIEMENS','ABB','BOSCHLTD','CUMMINSIND','DLF','GODREJCP',
    'AMBUJACEM','PIDILITIND','TORNTPHARM','INDHOTEL','PFC','RECLTD','BANKBARODA','INDIGO',
    'APOLLOHOSP','DIVISLAB','DRREDDY','ZYDUSLIFE','BRITANNIA','TATACONSUM','UNITDSPR','VBL',
    'EICHERMOT','BAJAJ-AUTO','HYUNDAI','BPCL','IOC','GAIL','TATAPOWER','ADANIPOWER','ADANIGREEN',
    'ADANIENT','ADANIENSOL','VEDL','HINDALCO','HINDZINC','JINDALSTEL','SHREECEM','MAXHEALTH',
    'CANBK','PNB','UNIONBANK','SHRIRAMFIN','BAJAJHLDNG','HDFCAMC','JIOFIN','TATACAP','LODHA',
    'ETERNAL',
]
_YMAP = {'TMPV': 'TATAMOTORS', 'MM': 'M&M'}


def yahoo(sym):
    return _YMAP.get(sym, sym) + '.NS'


def fetch_daily(sym):
    """Yahoo daily OHLC full history -> DataFrame(Date,Close)."""
    import urllib.request
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           f"{yahoo(sym)}?period1=1388534400&period2=4102444800&interval=1d")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        j = json.load(r)
    res = j["chart"]["result"][0]
    ts = res["timestamp"]
    cl = res["indicators"]["quote"][0]["close"]
    df = pd.DataFrame({"Date": pd.to_datetime(ts, unit="s"), "Close": cl}).dropna()
    return df


def fetch_nifty():
    import urllib.request
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI"
           "?period1=1388534400&period2=4102444800&interval=1d")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        j = json.load(r)
    res = j["chart"]["result"][0]
    ts = res["timestamp"]
    cl = res["indicators"]["quote"][0]["close"]
    return pd.DataFrame({"Date": pd.to_datetime(ts, unit="s"), "Close": cl}).dropna()


def month_end_of(dt):
    """Last trading day of dt's month (from NIFTY calendar approx via next month day 1)."""
    y, m = dt.year, dt.month
    if m == 12:
        ny, nm = y + 1, 1
    else:
        ny, nm = y, m + 1
    return datetime.date(ny, nm, 1) - datetime.timedelta(days=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    if a.report:
        if os.path.exists(LOG):
            print(pd.read_csv(LOG).to_string(index=False))
        else:
            print("no log yet — paper Sep 30 2026 se shuru")
        return

    today = datetime.date.today()
    me = month_end_of(today)
    print(f"today {today} | is month-end {me}")
    # Paper ke liye: sirf month-end ke BAAD (ya usi din shaam) rebalance karo.
    # Lekin live NSE data 15-min delay + day close ke baad hi milega; market close
    # 15:30 IST. Abhi sirf dry-run allowed hai.
    if not a.force and today < me:
        print("month-end nahi aaya — paper rebalance Sep 30 (ya agle month-end) pe hoga.")
        print("--force se aaj ka hypothetical portfolio dekh sakte ho (dry run).")
        return

    print(f"fetching {len(SYMBOLS)} names + NIFTY ...")
    closes = {}
    for i, s in enumerate(SYMBOLS):
        try:
            d = fetch_daily(s)
            if len(d) > 500:
                closes[s] = d.set_index("Date")["Close"]
        except Exception as e:
            print(f"  {s}: fetch fail {e}")
        if (i + 1) % 15 == 0:
            print(f"  ...{i+1}/{len(SYMBOLS)}")
    px = pd.DataFrame(closes).sort_index()
    nif = fetch_nifty().set_index("Date")["Close"]
    print(f"price matrix: {px.shape} ({px.index[0].date()} -> {px.index[-1].date()})")

    # signal date = last completed month-end (ya aaj agar month-end ho chuka)
    sig_date = px.index[px.index <= pd.Timestamp(me)].max()
    if pd.isna(sig_date):
        sig_date = px.index[-1]
    lookback = sig_date - pd.DateOffset(months=6)
    mom = px.loc[sig_date] / px.loc[lookback:].iloc[0] - 1
    mom = mom.dropna().sort_values(ascending=False)
    k = max(1, int(round(len(mom) * 0.25)))
    top = list(mom.index[:k])

    # gate: NIFTY vs SMA200 on sig_date
    sma = nif.rolling(200).mean()
    below = bool(nif.loc[:sig_date].iloc[-1] < sma.loc[:sig_date].dropna().iloc[-1])
    expo = 0.5 if below else 1.0

    print(f"\nsignal date {sig_date.date()} | momentum names {len(mom)} | top {k} | "
          f"NIFTY<SMA200: {below} => exposure {expo:.0%}")
    print("portfolio:", ", ".join(top))
    px_close = px.loc[sig_date, top]
    for t in top:
        print(f"  {t:<12} {px_close[t]:>10.1f}")

    row = {"rebalance_date": sig_date.date().isoformat(), "nifty_below_sma200": below,
           "exposure": expo, "k": k, "n_scored": len(mom),
           "portfolio": "|".join(top), "logged": datetime.date.today().isoformat()}
    if a.force:
        print("\n[DRY RUN — log mein nahi likha. Paper rules: agle month-end pe log.]")
        return
    st = {"last_rebalance": sig_date.date().isoformat()}
    with open(STATE, "w") as f:
        json.dump(st, f, indent=2)
    # append log
    if not os.path.exists(LOG):
        pd.DataFrame([row]).to_csv(LOG, index=False)
    else:
        old = pd.read_csv(LOG)
        if row["rebalance_date"] not in set(old["rebalance_date"]):
            pd.concat([old, pd.DataFrame([row])], ignore_index=True).to_csv(LOG, index=False)
    print("\nlogged -> momentum_paper_log.csv")


if __name__ == "__main__":
    main()
