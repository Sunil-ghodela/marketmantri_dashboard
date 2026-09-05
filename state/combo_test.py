"""Combo test — 1H MACD(12/26/5) cross + daily scenario (stage) filter, NIFTY.

Question: paper engine ke 1H cross signals ko daily stage gate lagaane se kya
milta hai? (August paper loss = chop mein cross lekar; stage gate wahi filter
hona chahiye.)

Data:
- 1H bars: MarketMantri/data/NIFTY50_15m.feather (2016-07 -> 2026-07), resample
- Daily scenario: state/nifty_daily_state.csv (REAL ^NSEI, 2014->2026-09-04)

Signal (paper jaisa causal):
- MACD(12,26) EMA diff, signal = EMA9. CROSS_UP = macd crosses above signal,
  evaluated on a COMPLETED 1H bar (hist sign flips >0).
- Signal day D = first completed 1H cross on that trading day.
- Entry = next open (paper: 15:30 wala signal = agli subah open pe entry).
  Forward returns measured close(D)->close(D+k) — standard approx, note gap.

Stage gate: scenario of PRIOR day (D-1, completed) — yaani stage pehle se pata
thi, cross D ke din aaya, entry D+1 open. Koi look-ahead nahi.
"""
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
FEATHER = "/home/vaibhav/AI/yr2026/MarketMantri/data/NIFTY50_15m.feather"
DAILY = os.path.join(HERE, "nifty_daily_state.csv")

# ---------------- 1H bars from 15m ----------------
f = pd.read_feather(FEATHER)
f["date"] = pd.to_datetime(f["date"], utc=True)
f = f.sort_values("date").reset_index(drop=True)
# NSE 1H completed bars: 10:00,11:00,12:00,13:00,14:00,15:00,15:30(wala half? no)
# 15m data 09:15-15:30 IST = 03:45-10:00 UTC. Hourly boundaries in UTC:
# 04:00..10:00 = 6 full hours + 09:15 open partial. Paper engine 1H bars are
# clock-hour bars; MACD crosses happen on completed hourly close (10:00..15:00
# IST). 15:30 ke cross pe entry next day. Isliye bas resample('1h', label='right').
f["h"] = f["date"].dt.floor("1h")
h1 = (f.groupby("h", as_index=False)
        .agg(open=("open", "first"), high=("high", "max"), low=("low", "min"),
             close=("close", "last"), n=("close", "size")))
h1 = h1[h1["n"] >= 3].reset_index(drop=True)  # pura ghanta (>=45 min)

c = h1["close"]
macd = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
sig = macd.ewm(span=9, adjust=False).mean()
hist = macd - sig
prev_hist = hist.shift(1)
cross_up = (hist > 0) & (prev_hist <= 0)
h1["cross_up"] = cross_up
h1["hist"] = hist

# signal day D = first hourly cross each trading day
h1["day"] = h1["h"].dt.date
sigs = h1[h1["cross_up"]].drop_duplicates("day", keep="first")[["day", "h"]].copy()
sigs["hour_ist"] = (sigs["h"].dt.tz_convert("Asia/Kolkata").dt.hour
                    if sigs["h"].dt.tz is not None else sigs["h"].dt.hour)

# ---------------- daily scenario ----------------
d = pd.read_csv(DAILY, parse_dates=["Date"])
d["day"] = d["Date"].dt.date
d = d.set_index("day")
d["r_next"] = 100 * (d["Close"].shift(-1) / d["Close"] - 1)  # D -> D+1

def fwd_close(day, k):
    """% return close(day) -> close(day+k trading days), market days only."""
    pos = d.index.get_loc(day) if day in d.index else None
    if pos is None or pos + k >= len(d):
        return np.nan
    c0 = d["Close"].iloc[pos]
    ck = d["Close"].iloc[pos + k]
    return 100 * (ck / c0 - 1)

rows = []
for _, s in sigs.iterrows():
    day = s["day"]
    if day not in d.index or d.index.get_loc(day) == 0:
        continue
    prev_scn = d["scenario"].iloc[d.index.get_loc(day) - 1]  # D-1 stage gate
    row = {"day": day, "hour_ist": s["hour_ist"], "prev_scn": prev_scn}
    for k in (1, 5, 10, 20):
        row[f"f{k}"] = fwd_close(day, k)
    rows.append(row)

sig = pd.DataFrame(rows).dropna(subset=["f1", "f5"])
print(f"1H CROSS_UP signals: {len(sig)}  (2016-07 -> 2026-07)")

# ---------------- buckets (stage gate on D-1 scenario) ----------------
BULL = ["ALL-ALIGN BULL", "EARLY-UP", "STRONG-FLOW", "CHOP-UP"]
CHOP = ["CHOP-MID", "CHOP-DOWN"]
BEAR = ["BEAR", "WEAK", "PANIC", "TOP-WARNING"]
RANGE_UP = ["RANGE", "TREND UP"]  # legacy regime-ish fallback

def bucket_of(scn):
    if scn in BULL:
        return "BULL-LEAN"
    if scn in CHOP:
        return "CHOP"
    if scn in BEAR:
        return "BEAR/AVOID"
    return "OTHER"

sig["bucket"] = sig["prev_scn"].map(bucket_of)

def report(sub, label):
    if len(sub) < 5:
        print(f"{label:<26} n={len(sub):<4} (too few)")
        return None
    out = {"bucket": label, "n": len(sub)}
    for k in (1, 5, 10, 20):
        v = sub[f"f{k}"].dropna()
        if len(v) >= 5:
            out[f"f{k}_avg"] = round(float(v.mean()), 2)
            out[f"f{k}_win"] = round(100 * float((v > 0).mean()), 0)
    # hourly timing split
    early = sub[sub["hour_ist"] <= 13]
    late = sub[sub["hour_ist"] >= 14]
    if len(early) >= 5 and len(late) >= 5:
        out["early_10-13_avg5"] = round(float(early["f5"].dropna().mean()), 2)
        out["late_14-15_avg5"] = round(float(late["f5"].dropna().mean()), 2)
    print(f"{label:<26} n={len(sub):<5} f1={out.get('f1_avg','-'):>6} f5={out.get('f5_avg','-'):>7} "
          f"f10={out.get('f10_avg','-'):>7} f20={out.get('f20_avg','-'):>7} "
          f"| win5={out.get('f5_win','-'):>3}%  (early/late5={out.get('early_10-13_avg5','-')}/{out.get('late_14-15_avg5','-')})")
    return out

print("\n--- 1H cross, stage gate = PREV day scenario ---")
print(f"{'bucket':<26} n    f1     f5      f10     f20  | win5  (early/late5)")
print("-" * 100)
res = []
res.append(report(sig, "ALL CROSSES (baseline)"))
for b in ["BULL-LEAN", "CHOP", "BEAR/AVOID", "OTHER"]:
    res.append(report(sig[sig["bucket"] == b], b))

# alternate gate: ALL-ALIGN BULL/EARLY-UP/STRONG-FLOW strict (trend-days only)
strict = sig[sig["prev_scn"].isin(["ALL-ALIGN BULL", "EARLY-UP", "STRONG-FLOW"])]
res.append(report(strict, "STRICT TREND-ONLY gate"))

res = [r for r in res if r]
outdf = pd.DataFrame(res)
outdf.to_csv(os.path.join(HERE, "combo_test_results.csv"), index=False)
sig.to_csv(os.path.join(HERE, "combo_signals.csv"), index=False)

# ---------------- baseline context: NIFTY always-in ----------------
d2 = d.dropna(subset=["Close"])
r = 100 * d2["Close"].pct_change()
years = len(r) / 252
bh_tot = (100 * ((1 + r / 100).cumprod().iloc[-1] - 1))
print(f"\nContext (same window, B&H NIFTY): total {bh_tot:+.0f}% over {len(r)} days ({years:.1f} yr)")
print("\nSaved: combo_test_results.csv + combo_signals.csv")
