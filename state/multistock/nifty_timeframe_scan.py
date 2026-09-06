#!/usr/bin/env python3
"""NIFTY timeframe scan — 15m/30m/1h/2h/4h x no-gate / long-only+skip / +entry-hour 9-10.

Sawaal (Sunil, 5 Sep raat, net flaky se ruka hua):
1. long-only + BEAR/AVOID-skip ka Sharpe 1.04 (1h pe mila) dusre timeframes pe
   tikta hai kya?  Ya wo 1h ka artefact hai?
2. Entry-hour 9-10 filter (entry lab ka sabse behtar bucket) timeframes pe kya karta hai?

Mechanics = nifty_verify_books.py ka exact engine, sirf frequency parametrized:
- closes.resample(freq).last() (IST, :00-anchored, left-closed) → MACD(12/26/5)
  completed-bar cross, acted at first 15m tick of next timeframe bar.
- Bidirectional flip (no-gate) / long-only + BEAR/AVOID-skip (gate) /
  + entry-hour filter (entry sirf hour 9-10).
- Stop 2% on 15m closes. Max-hold = 18 wall-clock hours (bars = 18/hours per bar:
  15m->72, 30m->36, 1h->18, 2h->9, 4h->4). Cost 0.06% rt. No divergence.
- Books (flat / B+sized / filter cl>=2) wahi add_books() jo verify mein tha.

Sanity: 1h no-gate sized +159.93 (DD 37.59, Sh 0.85) aur long-only+skip
+81.16 (DD 18.28, Sh 1.04) reproduce hona chahiye.
"""
import json
import os
from collections import defaultdict

import numpy as np
import pandas as pd

from nifty_verify_books import load_15m, add_books

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.dirname(HERE)
COST, STOP_PCT, SPAN = 0.06, 2.0, 5
WALL_CLOCK_MAX_HOLD_H = 18.0

FREQS = {
    "15m": ("15min", 0.25),
    "30m": ("30min", 0.5),
    "1h": ("1h", 1.0),
    "2h": ("2h", 2.0),
    "4h": ("4h", 4.0),
}

AVOID = {"BEAR", "WEAK", "PANIC", "TOP-WARNING", "CHOP-DOWN"}


def shadow_book(df: pd.DataFrame, freq: str, hours_per_bar: float,
                gate=None, entry_hours: tuple | None = None) -> list[dict]:
    """Live engine replay on any timeframe. gate: callable(prev_day)->set of
    allowed directions (None = always flip). entry_hours: allowed entry hours
    (IST) for NEW positions (None = any)."""
    max_hold_bars = max(1, int(WALL_CLOCK_MAX_HOLD_H / hours_per_bar))
    h = df["close"].resample(freq).last().dropna()
    macd = h.ewm(span=12, adjust=False).mean() - h.ewm(span=26, adjust=False).mean()
    sig = macd.ewm(span=SPAN, adjust=False).mean()
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
    # precompute slow per-iteration ops (floor + date) once
    hbar_arr = bars15.floor(freq)
    day_arr = np.array([t.date() for t in bars15])

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
        hbar = hbar_arr[i]
        new_bar = hbar != last_hbar
        cr = "none"
        if new_bar and last_hbar is not None and last_hbar in hpos:
            cr = cross[hpos[last_hbar]]     # just-completed timeframe bar's cross
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
            elif pos["bars"] >= max_hold_bars:
                close_tr(ltp, "Max Hold", t)
            elif new_bar and ((d == "long" and cr == "down") or
                              (d == "short" and cr == "up")):
                close_tr(ltp, "MACD Cross", t)
                if gate is not None or entry_hours is not None:
                    if entry_hours is not None and t.hour not in entry_hours:
                        continue            # exit, no reversal outside 9-10
                    if gate is not None:
                        di = np.searchsorted(dates, day_arr[i])
                        prev = dates[di - 1] if di > 0 else None
                        want = "short" if cr == "down" else "long"
                        if want not in gate(prev):
                            continue
                pos = {"d": "short" if cr == "down" else "long",
                       "ep": ltp, "et": t, "bars": 0}
        if pos is None and new_bar and cr in ("up", "down"):
            if entry_hours is not None and t.hour not in entry_hours:
                continue
            if gate is not None:
                di = np.searchsorted(dates, day_arr[i])
                prev = dates[di - 1] if di > 0 else None
                want = "long" if cr == "up" else "short"
                if want not in gate(prev):
                    continue
            pos = {"d": "long" if cr == "up" else "short",
                   "ep": ltp, "et": t, "bars": 0}
    return trades


def yearly_sized(trades: list[dict]) -> dict:
    sp = defaultdict(float)
    for t in trades:
        sp[t["exit_time"][:4]] += t["pnl_pct"] * t.get("size_mult", 1.0)
    return {k: round(v, 2) for k, v in sorted(sp.items())}


def main():
    print("=" * 88)
    print("NIFTY timeframe scan — 15m/30m/1h/2h/4h x gates, max-hold 18 wall-clock hours")
    df = load_15m()
    print(f"15m bars: {len(df):,}  {df.index[0]} -> {df.index[-1]}")

    d = pd.read_csv(os.path.join(STATE, "nifty_daily_state.csv"), parse_dates=["Date"])
    d["day"] = pd.to_datetime(d["Date"]).dt.date
    scen = dict(zip(d["day"], d["scenario"]))

    def gate_no_avoid(prev):
        s = scen.get(prev, "CHOP-MID")
        return {"long"} if s not in AVOID else set()

    variants = {
        "no-gate (flip)": {"gate": None, "hours": None},
        "long-only+BEAR/AVOID-skip": {"gate": gate_no_avoid, "hours": None},
        "long-only+skip+entry-9-10": {"gate": gate_no_avoid, "hours": (9, 10)},
    }

    results = {}
    for label, (freq, hpb) in FREQS.items():
        print(f"\n{'=' * 88}\nTIMEFRAME {label}  (bar {hpb}h, max-hold {int(WALL_CLOCK_MAX_HOLD_H / hpb)} bars = {WALL_CLOCK_MAX_HOLD_H:.0f}h wall-clock)")
        print(f"{'variant':<30}{'n':>5}{'WR%':>6}{'flat%':>9}{'sized%':>9}{'flt%':>8}{'maxDD(sz)':>10}{'Sh(sz)':>7}")
        results[label] = {}
        for vname, v in variants.items():
            tr = shadow_book(df, freq, hpb, gate=v["gate"], entry_hours=v["hours"])
            r = add_books(tr)
            f, s, fl = r["flat"], r["sized"], r["filter"]
            print(f"{vname:<30}{s['n']:>5}{s['wr']:>6.1f}{f['net']:>+9.2f}{s['net']:>+9.2f}"
                  f"{fl['net']:>+8.2f}{s['maxDD']:>10.2f}{s['sharpe_m']:>7.2f}")
            results[label][vname] = {
                "n": s["n"], "flat": f, "sized": s, "filter": fl,
                "yearly_sized": yearly_sized(tr), "trades": tr,
            }
            # hourly profile (flat) for the long-only+skip variant — timing check
            if vname == "long-only+BEAR/AVOID-skip":
                hb = defaultdict(list)
                for t in tr:
                    hb[t["entry_hour"]].append(t["pnl_pct"])
                prof = {str(k): {"n": len(a), "net": round(float(np.sum(a)), 2),
                                 "avg": round(float(np.mean(a)), 4)}
                        for k, a in hb.items()}
                results[label]["_hourly_profile"] = prof

    # ---- summary: Sharpe of long-only+skip across timeframes (the key question)
    print("\n" + "=" * 88)
    print("KEY QUESTION — long-only+BEAR/AVOID-skip: Sharpe 1.04 (1h) dusre timeframes pe?")
    print(f"{'tf':<5}{'n':>5}{'net%':>9}{'maxDD%':>9}{'Sharpe':>8}{'WR%':>6}")
    for label in FREQS:
        s = results[label]["long-only+BEAR/AVOID-skip"]["sized"]
        print(f"{label:<5}{s['n']:>5}{s['net']:>+9.2f}{s['maxDD']:>9.2f}{s['sharpe_m']:>8.2f}{s['wr']:>6.1f}")
    print("\nWith entry-hour 9-10 filter:")
    print(f"{'tf':<5}{'n':>5}{'net%':>9}{'maxDD%':>9}{'Sharpe':>8}{'WR%':>6}")
    for label in FREQS:
        s = results[label]["long-only+skip+entry-9-10"]["sized"]
        print(f"{label:<5}{s['n']:>5}{s['net']:>+9.2f}{s['maxDD']:>9.2f}{s['sharpe_m']:>8.2f}{s['wr']:>6.1f}")

    # ---- no-gate flip: does the edge hold up vs long-only?
    print("\nNo-gate (flip) — baseline per timeframe:")
    print(f"{'tf':<5}{'n':>5}{'net%':>9}{'maxDD%':>9}{'Sharpe':>8}{'WR%':>6}")
    for label in FREQS:
        s = results[label]["no-gate (flip)"]["sized"]
        print(f"{label:<5}{s['n']:>5}{s['net']:>+9.2f}{s['maxDD']:>9.2f}{s['sharpe_m']:>8.2f}{s['wr']:>6.1f}")

    out = {label: {k: (v if k == "_hourly_profile" else
                       {kk: vv for kk, vv in v.items() if kk != "trades"})
                   for k, v in runs.items()}
           for label, runs in results.items()}
    with open(os.path.join(STATE, "nifty_timeframe_scan.json"), "w") as f:
        json.dump(out, f, indent=1, default=str)
    print(f"\nJSON: state/nifty_timeframe_scan.json")


if __name__ == "__main__":
    main()