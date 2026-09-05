"""Stocks combo curve — 1H MACD cross + daily BULL-LEAN stage gate, 10 liquid names.

NIFTY combo (state/combo_curve.py) ka stock version. Har stock pe same rule:
- 1H bars (archive 5-min 2015-02 -> 2026-04-09; daily se match), MACD(12,26,9)-hist
  cross = signal. Pehla cross din ka = signal day.
- Gate: previous day ka scenario BULL-LEAN (CHOP-UP/ALL-ALIGN BULL/EARLY-UP/
  STRONG-FLOW). Entry next open, time-hold exit (10/20 din), no overlap.
- Cost 0.1% round-trip.
Per-stock equity -> equal-weight basket. Compare vs NIFTY combo + EW buy&hold.
"""
import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import build_state as bs
import scenario

HERE = os.path.dirname(os.path.abspath(__file__))
ARCHIVE = "/home/vaibhav/AI/yr2026/MarketMantri/data_sources/archive-data"
PRICES = os.path.join(HERE, "stocks_prices.csv")
NIFTY_FULL = os.path.join(os.path.dirname(HERE), "nifty_15m_full.feather")

SYMS = ["RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "HINDUNILVR",
        "ITC", "SBIN", "BHARTIARTL", "LT"]
BULL_LEAN = ["CHOP-UP", "ALL-ALIGN BULL", "EARLY-UP", "STRONG-FLOW"]


def load_1h(sym):
    """1H OHLC bars from archive 5-min (naive IST). Returns df with h, close, day."""
    f = pd.read_csv(os.path.join(ARCHIVE, f"{sym}_5minute.csv"),
                    parse_dates=["date"])
    f = f[["date", "open", "high", "low", "close"]].dropna()
    f["h"] = f["date"].dt.floor("1h")
    h1 = (f.groupby("h", as_index=False)
           .agg(open=("open", "first"), high=("high", "max"),
                low=("low", "min"), close=("close", "last"), n=("close", "size")))
    h1 = h1[h1["n"] >= 3].reset_index(drop=True)   # full hour (~>=45 min)
    return h1


def crosses(h1):
    c = h1["close"]
    macd = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    sig = macd.ewm(span=9, adjust=False).mean()
    hist = macd - sig
    up = (hist > 0) & (hist.shift(1) <= 0)
    dn = (hist < 0) & (hist.shift(1) >= 0)
    h1["hist"] = hist
    h1["xup"] = up
    h1["xdn"] = dn
    h1["day"] = h1["h"].dt.date
    up_days = set(h1[h1["xup"]].drop_duplicates("day", keep="first")["day"])
    return up_days


def daily_scenarios(sym):
    raw = pd.read_csv(PRICES, parse_dates=["Date"])
    g = raw[raw["symbol"] == sym].sort_values("Date").reset_index(drop=True)
    g = bs.add_indicators(g)
    scenario.assign_scenarios(g)
    g = g[g["scenario"] != "WARMUP"].copy()
    g["day"] = g["Date"].dt.date
    g = g.set_index("day").sort_index()
    return g


def simulate(daily, up_days, hold_days, cost_side):
    """Same engine as combo_curve: prev-day gate, next open, time exit, no overlap."""
    days = list(daily.index)
    n = len(days)
    scn = daily["scenario"].values
    prev_scn = pd.Series(scn).shift(1).values
    prev_scn[0] = None
    cl = daily["Close"].values
    op = daily["Open"].values
    eq = np.ones(n)
    in_pos, hold_left, entry_i, n_tr, wins = False, 0, None, 0, 0
    tr_ret = []
    for i in range(n):
        day = days[i]
        if in_pos:
            ret = (cl[i] / op[i] - 1) if i == entry_i else (cl[i] / cl[i - 1] - 1)
            if i == entry_i:
                ret -= cost_side
            eq[i] = eq[i - 1] * (1 + ret)
            hold_left -= 1
            if hold_left <= 0:
                eq[i] *= (1 - cost_side)
                in_pos = False
                r = (cl[i] / op[entry_i] - 1) - 2 * cost_side
                tr_ret.append(r)
                n_tr += 1
                if r > 0:
                    wins += 1
        else:
            eq[i] = eq[i - 1] if i > 0 else 1.0
            if day in up_days and prev_scn[i] is not None and prev_scn[i] in BULL_LEAN:
                in_pos = True
                hold_left = hold_days
                entry_i = i
    r_daily = pd.Series(np.diff(eq) / eq[:-1], index=daily.index[1:]).fillna(0)
    return eq, r_daily, n_tr, wins, tr_ret


def stat(eq, r_daily, n_tr, wins, tr_ret, daily):
    years = len(r_daily) / 252
    tot = (eq[-1] - 1) * 100
    cagr = ((eq[-1]) ** (1 / years) - 1) * 100 if eq[-1] > 0 else -100
    sharpe = r_daily.mean() / r_daily.std() * np.sqrt(252) if r_daily.std() > 0 else 0
    eq_series = pd.Series(eq, index=daily.index)
    cum = eq_series / eq_series.cummax()
    mdd = (cum.min() - 1) * 100
    return dict(tot=tot, cagr=cagr, sharpe=sharpe, mdd=mdd, n_tr=n_tr,
                win=100 * wins / n_tr if n_tr else 0,
                avg=100 * np.mean(tr_ret) if tr_ret else 0,
                expo=100 * (r_daily != 0).mean())


print("=" * 108)
print("10 STOCKS — 1H MACD cross + daily BULL-LEAN gate (cost 0.1% rt, archive 2015-02->2026-04)")
print("=" * 108)
per_stock = []
for hold in (10, 20):
    for sym in SYMS:
        daily = daily_scenarios(sym)
        h1 = load_1h(sym)
        if h1.empty:
            print(f"{sym}: no intraday, skip")
            continue
        up_days = crosses(h1)
        # limit daily window to intraday coverage
        first = h1["day"].min()
        daily = daily[daily.index >= first]
        eq, r_d, n_tr, wins, tr = simulate(daily, up_days, hold, 0.0005)
        s = stat(eq, r_d, n_tr, wins, tr, daily)
        s.update(symbol=sym, hold=hold)
        per_stock.append(s)

# per-stock table (hold-20)
print("\n--- per stock (hold-20, 0.1% rt) ---")
print(f"{'sym':<11}{'n_tr':>5}{'win%':>6}{'total%':>9}{'CAGR%':>8}{'Sharpe':>8}{'MDD%':>8}{'expo%':>6}")
h20 = [s for s in per_stock if s["hold"] == 20]
for s in h20:
    print(f"{s['symbol']:<11}{s['n_tr']:>5}{s['win']:>5.0f}%{s['tot']:>+8.1f}%{s['cagr']:>+7.1f}%"
          f"{s['sharpe']:>8.2f}{s['mdd']:>+7.1f}%{s['expo']:>5.0f}%")

# basket: equal-weight mean of per-stock daily strategy returns
# rebuild full daily grids for averaging
grid = {}
grid_bh = {}
for sym in SYMS:
    daily = daily_scenarios(sym)
    h1 = load_1h(sym)
    up_days = crosses(h1)
    first = h1["day"].min()
    daily = daily[daily.index >= first]
    eq, r_d, *_ = simulate(daily, up_days, 20, 0.0005)
    r_bh = 100 * daily["Close"].pct_change().fillna(0) / 100
    grid[sym] = pd.Series(r_d.values, index=daily.index[1:])
    grid_bh[sym] = r_bh
all_idx = pd.DatetimeIndex(sorted(set().union(*[g.index for g in grid.values()])))
rets = pd.DataFrame({s: g.reindex(all_idx).fillna(0) for s, g in grid.items()})
rets_bh = pd.DataFrame({s: g.reindex(all_idx) for s, g in grid_bh.items()}).ffill().fillna(0)

basket = rets.mean(axis=1)             # equal-weight: har stock ko 1/10 capital
bh = rets_bh.mean(axis=1)
eq_b = (1 + basket).cumprod()
eq_bh = (1 + bh).cumprod()

def bstat(eq, r, label):
    years = len(r) / 252
    tot = (eq.iloc[-1] - 1) * 100
    cagr = (eq.iloc[-1] ** (1 / years) - 1) * 100
    sharpe = r.mean() / r.std() * np.sqrt(252) if r.std() > 0 else 0
    mdd = ((eq / eq.cummax()) - 1).min() * 100
    return dict(label=label, tot=tot, cagr=cagr, sharpe=sharpe, mdd=mdd)

print("\n--- BASKET (equal-weight 10 names) ---")
print(f"{'':<28}{'total%':>9}{'CAGR%':>8}{'Sharpe':>8}{'MDD%':>8}")
for r in [bstat(eq_b, basket, "COMBO gate hold-20 (0.1% rt)"),
          bstat(eq_bh, bh, "EW BUY & HOLD 10 names")]:
    print(f"{r['label']:<28}{r['tot']:>+8.1f}%{r['cagr']:>+7.1f}%{r['sharpe']:>8.2f}{r['mdd']:>+7.1f}%")

print("\n--- BASKET yearly (combo vs EW B&H) ---")
yr = pd.DataFrame({"combo": basket, "bh": bh}, index=all_idx)
gy = yr.groupby(all_idx.year).apply(lambda x: pd.Series({
    "combo": (1 + x["combo"]).prod() - 1, "bh": (1 + x["bh"]).prod() - 1}))
for y, row in gy.iterrows():
    if y < 2015 or y > 2026:
        continue
    mark = "BETTER" if row["combo"] > row["bh"] else "worse"
    print(f"{y}: combo {100*row['combo']:>+7.1f}%   BH {100*row['bh']:>+7.1f}%   {mark}")
print(f"\nYears combo beat EW B&H: {(gy['combo']>gy['bh']).sum()}/{len(gy)}")
print(f"Green years combo: {(gy['combo']>0).sum()}/{len(gy)}")

# save
pd.DataFrame({"combo_10": eq_b, "ew_bh_10": eq_bh}).to_csv(
    os.path.join(HERE, "stocks_combo_equity.csv"))
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    BG, GRID, MUT = "#0f172a", "#334155", "#94a3b8"
    fig, ax = plt.subplots(figsize=(13, 6), facecolor=BG)
    ax.set_facecolor(BG)
    ax.plot(eq_b.index, eq_b.values, label="Combo gate hold-20 (10 stocks, EW)", color="#22d3ee", lw=1.3)
    ax.plot(eq_bh.index, eq_bh.values, label="EW Buy & Hold (10 stocks)", color="#fbbf24", lw=1.0, alpha=0.8)
    for sp in ["top", "right"]:
        ax.spines[sp].set_visible(False)
    ax.tick_params(colors=MUT, labelsize=9)
    ax.grid(True, alpha=0.15, color=GRID)
    ax.legend(facecolor=BG, edgecolor=GRID, labelcolor="white", fontsize=10)
    ax.set_title("10 stocks combo: 1H MACD cross + BULL-LEAN gate, hold-20, 0.1% rt",
                 color="white", fontsize=12, loc="left")
    plt.tight_layout()
    plt.savefig(os.path.join(HERE, "stocks_combo_equity.png"), dpi=130, facecolor=BG)
    print("\nSaved: stocks_combo_equity.csv + stocks_combo_equity.png")
except Exception as e:
    print("png fail:", e)
