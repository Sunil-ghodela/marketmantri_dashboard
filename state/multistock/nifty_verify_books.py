#!/usr/bin/env python3
"""NIFTY live-engine verify — books + entry-hour lab + daily-state gate combine.

Sawaal (Sunil):
1. Chalti hui v2.0 momentum strategy (B config: 1H MACD 12/26/5 completed-bar
   cross, no div, 2% stop, 18-bar max-hold, 0.06% rt) — flat vs W/L-sized vs
   filter(cl>=2) — naye full data (04 Sep 2026) pe verify.
2. Entry-hour / weekday lab — kis hour/weekday pe trade behtar (10yr).
3. Daily-state strategy ke saath combine — prev-day scenario gate lagane pe
   kitna milta hai (span-5 engine pe, jo live chalta hai).

Mechanics = live engine (MarketMantri/_nifty_lossfilter_10yr.py conventions):
1H resample of 15m closes (IST, :00-anchored), cross on COMPLETED bars, acted
at first 15m tick of next bar. Bidirectional flip. Stop 2% on 15m closes.
Max-hold 18 one-hour bars. No divergence. Cost 0.06% per round trip.
Data: state/nifty_15m_full.feather (15m + Yahoo, 04 Sep tak) + daily scenario.
"""
import json
import os
from collections import defaultdict

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.dirname(HERE)
COST, STOP_PCT, MAX_HOLD, SPAN = 0.06, 2.0, 18, 5


def load_15m() -> pd.DataFrame:
    df = pd.read_feather(os.path.join(STATE, "nifty_15m_full.feather"))
    ts = pd.DatetimeIndex(pd.to_datetime(df["date"], utc=True))
    ts = ts.tz_convert("Asia/Kolkata").tz_localize(None)   # naive IST
    df = df.set_index(ts).sort_index()
    return df[["open", "high", "low", "close"]]


def shadow_book(df: pd.DataFrame, span: int, gate=None) -> list[dict]:
    """Live engine replay. gate: optional callable(prev_day_scenario)->set of
    allowed directions {'long','short'} at entry time; None = always flip."""
    h = df["close"].resample("1h").last().dropna()
    macd = h.ewm(span=12, adjust=False).mean() - h.ewm(span=26, adjust=False).mean()
    sig = macd.ewm(span=span, adjust=False).mean()
    green = (macd > sig).to_numpy()
    cross = np.full(len(h), "none", dtype=object)
    flip = green[1:] != green[:-1]
    cross[1:][flip & green[1:]] = "up"
    cross[1:][flip & ~green[1:]] = "down"
    hpos = {t: i for i, t in enumerate(h.index)}

    closes = df["close"].to_numpy()
    bars15 = df.index
    day_of = {t.date(): i for i, t in enumerate(bars15)}
    dates = sorted(day_of)

    pos, trades = None, []
    last_hbar = None
    warmup_end = bars15[0] + pd.Timedelta(days=30)

    def close_tr(price, reason, ts):
        nonlocal pos
        gross = ((price - pos["ep"]) / pos["ep"] * 100) if pos["d"] == "long" \
            else ((pos["ep"] - price) / pos["ep"] * 100)
        trades.append({"dir": pos["d"], "entry_time": str(pos["et"]),
                       "exit_time": str(ts), "pnl_pct": round(gross - COST, 2),
                       "reason": reason, "entry_day": str(pos["et"].date()),
                       "entry_hour": pos["et"].hour})
        pos = None

    for i in range(len(bars15)):
        t = bars15[i]
        ltp = closes[i]
        hbar = t.floor("h")
        new_bar = hbar != last_hbar
        cr = "none"
        if new_bar and last_hbar is not None and last_hbar in hpos:
            cr = cross[hpos[last_hbar]]     # the just-completed bar's cross
        if new_bar:
            last_hbar = hbar
        if t < warmup_end:
            continue
        if pos:
            if new_bar:
                pos["bars"] += 1
            d, ep = pos["d"], pos["ep"]
            if (d == "long" and ltp <= ep * (1 - STOP_PCT / 100)) or \
               (d == "short" and ltp >= ep * (1 + STOP_PCT / 100)):
                close_tr(ltp, "Stop", t)
            elif pos["bars"] >= MAX_HOLD:
                close_tr(ltp, "Max Hold", t)
            elif new_bar and ((d == "long" and cr == "down") or
                              (d == "short" and cr == "up")):
                close_tr(ltp, "MACD Cross", t)
                # reverse only if gate allows; else stay flat
                if gate is not None:
                    di = np.searchsorted(dates, t.date())
                    prev = dates[di - 1] if di > 0 else None
                    allow = gate(prev)
                    want = "short" if cr == "down" else "long"
                    if want not in allow:
                        continue
                pos = {"d": "short" if cr == "down" else "long",
                       "ep": ltp, "et": t, "bars": 0}
        if pos is None and new_bar and cr in ("up", "down"):
            if gate is not None:
                di = np.searchsorted(dates, t.date())
                prev = dates[di - 1] if di > 0 else None
                allow = gate(prev)
                want = "long" if cr == "up" else "short"
                if want not in allow:
                    continue
            pos = {"d": "long" if cr == "up" else "short",
                   "ep": ltp, "et": t, "bars": 0}
    return trades


def add_books(trades: list[dict]) -> dict:
    pnl = np.array([t["pnl_pct"] for t in trades])
    n = len(pnl)
    mult = np.ones(n)
    cl = 0
    for i, p in enumerate(pnl):
        mult[i] = 3.0 if cl >= 4 else 2.5 if cl >= 3 else 2.0 if cl >= 2 else 1.0
        cl = 0 if p > 0 else cl + 1
    # filter book: only trades with >=2 prior consecutive losses, 1x
    clb = np.zeros(n, dtype=int)
    run = 0
    for i, p in enumerate(pnl):
        clb[i] = run
        run = 0 if p > 0 else run + 1
    taken = clb >= 2
    spnl = pnl * mult
    for t, m in zip(trades, mult):
        t["size_mult"] = m
    for t, tk in zip(trades, taken):
        t["taken_if_filter"] = bool(tk)
    eq, seq = np.cumsum(pnl), np.cumsum(spnl)
    feq = np.cumsum(np.where(taken, pnl, 0.0))
    out = {}
    for lbl, arr in (("flat", pnl), ("sized", spnl), ("filter", np.where(taken, pnl, 0.0))):
        e = np.cumsum(arr)
        dd = float(np.max(np.maximum.accumulate(e) - e)) if len(e) else 0.0
        months = pd.Series(arr).groupby(
            [pd.Timestamp(x["exit_time"]).to_period("M") for x in trades]).sum()
        mret = months.values / 100.0
        sharpe = (float(np.mean(mret) / np.std(mret) * np.sqrt(12))
                  if len(mret) > 2 and np.std(mret) > 0 else 0.0)
        out[lbl] = {"n": int(len(arr)), "wr": round(100 * float(np.mean(arr > 0)), 1),
                    "net": round(float(arr.sum()), 2),
                    "avg": round(float(arr.mean()), 4) if len(arr) else 0.0,
                    "maxDD": round(dd, 2), "sharpe_m": round(sharpe, 2)}
    out["trades"] = trades
    return out


def yearly(trades: list[dict], key: str) -> dict:
    y = defaultdict(list)
    for t in trades:
        y[t["exit_time"][:4]].append(t[key])
    return {k: {"n": len(v), "net": round(float(np.sum(v)), 2),
                "wr": round(100 * float(np.mean(np.array(v) > 0)), 1)}
            for k, v in sorted(y.items())}


def main():
    print("=" * 78)
    print("NIFTY live-engine verify — B config (span 5), full data (04 Sep tak)")
    df = load_15m()
    print(f"15m bars: {len(df):,}  {df.index[0]} -> {df.index[-1]}")

    base = shadow_book(df, SPAN)
    print(f"\nsignals/trades (no gate): {len(base)}")
    res = add_books(base)
    for lbl in ("flat", "sized", "filter"):
        s = res[lbl]
        print(f"  {lbl:<7} n={s['n']:>5}  WR {s['wr']:>5}%  net {s['net']:>+9.2f}%  "
              f"avg {s['avg']:>+7.4f}%  maxDD {s['maxDD']:>7.2f}%  Sharpe(m) {s['sharpe_m']:>5.2f}")

    # ---- yearly sized + flat
    print("\n--- Yearly (sized book; flat in parens) ---")
    yf, ys = yearly(base, "pnl_pct"), yearly(base, "pnl_pct")
    sp = defaultdict(list)
    for t in base:
        sp[t["exit_time"][:4]].append(t["pnl_pct"] * t["size_mult"])
    ysd = {k: round(float(np.sum(v)), 2) for k, v in sorted(sp.items())}
    print(f"{'year':<6}{'n':>5}{'flat%':>9}{'sized%':>9}")
    for k in sorted(yf):
        print(f"{k:<6}{yf[k]['n']:>5}{yf[k]['net']:>+9.2f}{ysd[k]:>+9.2f}")

    # ---- entry hour + weekday lab (flat pnl)
    print("\n--- Entry-hour lab (10yr, flat 1x) ---")
    hb = defaultdict(list)
    for t in base:
        hb[t["entry_hour"]].append(t["pnl_pct"])
    print(f"{'hour':>5}{'n':>6}{'WR%':>7}{'net%':>10}{'avg%':>9}")
    for hr in sorted(hb):
        a = np.array(hb[hr])
        print(f"{hr:>5}{len(a):>6}{100*np.mean(a>0):>7.1f}{a.sum():>+10.2f}{a.mean():>+9.4f}")

    print("\n--- Weekday lab (flat 1x) ---")
    wb = defaultdict(list)
    for t in base:
        wd = pd.Timestamp(t["entry_time"]).strftime("%a")
        wb[wd].append(t["pnl_pct"])
    for wd in ["Mon", "Tue", "Wed", "Thu", "Fri"]:
        a = np.array(wb.get(wd, []))
        if len(a):
            print(f"{wd:<4} n={len(a):>5} WR {100*np.mean(a>0):>5.1f}%  "
                  f"net {a.sum():>+9.2f}%  avg {a.mean():>+8.4f}%")

    # ---- daily-state gate combine
    d = pd.read_csv(os.path.join(STATE, "nifty_daily_state.csv"), parse_dates=["Date"])
    d["day"] = pd.to_datetime(d["Date"]).dt.date
    scen = dict(zip(d["day"], d["scenario"]))
    BULL_LEAN = {"CHOP-UP", "ALL-ALIGN BULL", "EARLY-UP", "STRONG-FLOW"}
    BEAR_LEAN = {"CHOP-DOWN", "BEAR", "WEAK", "PANIC", "TOP-WARNING"}
    CHOP = {"CHOP-MID"}
    AVOID = {"BEAR", "WEAK", "PANIC", "TOP-WARNING", "CHOP-DOWN"}

    def gate_bull(prev):
        s = scen.get(prev, "CHOP-MID")
        return {"long"} if s in BULL_LEAN else ({"short"} if s in BEAR_LEAN else set())

    def gate_no_avoid(prev):
        # long allowed unless previous day is bear/avoid; short never (index drift)
        s = scen.get(prev, "CHOP-MID")
        return {"long"} if s not in AVOID else set()

    variants = {
        "no-gate (live, flip)": None,
        "gate: bull-long / bear-short": gate_bull,
        "gate: long unless BEAR/AVOID prev-day": gate_no_avoid,
    }
    print("\n--- Daily-state gate combine (prev-day scenario) ---")
    allres = {"base": res, "hourly": {str(k): {"n": len(v), "net": round(float(np.sum(v)), 2),
                                               "avg": round(float(np.mean(v)), 4)}
                                      for k, v in hb.items()}}
    for name, g in variants.items():
        tr = base if g is None else shadow_book(df, SPAN, gate=g)
        if not tr:
            print(f"  {name}: NO TRADES")
            continue
        r = add_books(tr)
        s = r["sized"]
        print(f"  {name:<40} n={s['n']:>4}  net(sized) {s['net']:>+8.2f}%  "
              f"maxDD {s['maxDD']:>7.2f}%  Sharpe {s['sharpe_m']:>5.2f}  "
              f"WR {s['wr']:>4.1f}%")
        allres[name] = {"flat": r["flat"], "sized": r["sized"], "filter": r["filter"],
                        "yearly_sized": ysd_of(tr), "trades_n": len(tr)}

    # scenario bucket per trade (no-gate engine) — prev-day scenario of entry
    print("\n--- Trade bucket by PREV-day scenario (no-gate engine, flat) ---")
    bkt = defaultdict(list)
    for t in base:
        ed = pd.Timestamp(t["entry_time"]).date()
        days = sorted(scen)
        di = np.searchsorted(days, ed)
        prev = days[di - 1] if di > 0 else None
        s = scen.get(prev, "?")
        grp = "BULL-LEAN" if s in BULL_LEAN else ("BEAR/AVOID" if s in AVOID
                                                  else ("CHOP-MID" if s in CHOP else "?"))
        bkt[grp].append(t["pnl_pct"])
    print(f"{'bucket':<12}{'n':>6}{'WR%':>7}{'net%':>10}{'avg%':>9}")
    for k in sorted(bkt):
        a = np.array(bkt[k])
        print(f"{k:<12}{len(a):>6}{100*np.mean(a>0):>7.1f}{a.sum():>+10.2f}{a.mean():>+9.4f}")

    with open(os.path.join(STATE, "nifty_verify_books.json"), "w") as f:
        json.dump(allres, f, indent=1, default=str)


def ysd_of(trades: list[dict]) -> dict:
    sp = defaultdict(float)
    for t in trades:
        sp[t["exit_time"][:4]] += t["pnl_pct"] * t.get("size_mult", 1.0)
    return {k: round(v, 2) for k, v in sorted(sp.items())}


if __name__ == "__main__":
    main()
