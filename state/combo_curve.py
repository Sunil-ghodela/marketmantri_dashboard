"""Combo strategy EQUITY CURVE test — 1H MACD cross + daily stage gate, NIFTY.

Pehla combo test (combo_test.py) sirf per-signal forward-average tha. Ye proper
simulation hai: entry next open, time-hold exit, koi overlap nahi, cost sahit,
equity curve + Sharpe + MDD + saal-dar-saal. Long AUR short dono side.

Rules:
- LONG: 1H CROSS_UP signal day D + prev-day scenario BULL-LEAN -> entry D+1 open,
  hold H trading din, exit close pe. Flat rehne pe naya signal hi entry.
- SHORT: 1H CROSS_DOWN signal day D + prev-day scenario BEAR-LEAN -> entry D+1
  open (short), hold H din.
- No overlap (single instrument). Cost = per-side (entry+exit).
"""
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
FEATHER = os.path.join(HERE, "nifty_15m_full.feather")  # 15m + Yahoo recent (04 Sep tak)
DAILY = os.path.join(HERE, "nifty_daily_state.csv")

# ---------------- 1H bars ----------------
f = pd.read_feather(FEATHER)
f["date"] = pd.to_datetime(f["date"], utc=True)
f = f.sort_values("date").reset_index(drop=True)
f["h"] = f["date"].dt.floor("1h")
h1 = (f.groupby("h", as_index=False)
        .agg(open=("open", "first"), close=("close", "last"), n=("close", "size")))
h1 = h1[h1["n"] >= 3].reset_index(drop=True)
c = h1["close"]
macd = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
sig = macd.ewm(span=9, adjust=False).mean()
hist = macd - sig
h1["hist"] = hist
ph = hist.shift(1)
h1["xup"] = (hist > 0) & (ph <= 0)
h1["xdn"] = (hist < 0) & (ph >= 0)
h1["day"] = h1["h"].dt.date
# first cross of each day (signal day)
up_days = set(h1[h1["xup"]].drop_duplicates("day", keep="first")["day"])
dn_days = set(h1[h1["xdn"]].drop_duplicates("day", keep="first")["day"])
# daily open proxy (pehla 15m bar of day ka open)
dopen = f.groupby(f["date"].dt.date)["open"].first()

# ---------------- daily state ----------------
d = pd.read_csv(DAILY, parse_dates=["Date"])
d["day"] = d["Date"].dt.date
d = d.set_index("day").sort_index()
cl = d["Close"]

BULL_LEAN = ["CHOP-UP", "ALL-ALIGN BULL", "EARLY-UP", "STRONG-FLOW"]
BEAR_LEAN = ["CHOP-DOWN", "BEAR", "WEAK", "PANIC", "TOP-WARNING"]


def simulate(direction, gate_list, hold_days, cost_side, gate_on=True, gate_label=""):
    """direction: 'long'|'short'. Equity over d.index (aligned to d rows)."""
    days = list(d.index)
    n = len(days)
    sig_days = up_days if direction == "long" else dn_days
    sign = 1 if direction == "long" else -1
    eq = np.ones(n)
    # prev-day gate
    scn = d["scenario"].values
    prev_scn = pd.Series(scn).shift(1).values  # gate for day index i = scenario[i-1]
    prev_scn[0] = None

    in_pos = False
    hold_left = 0
    entry_i = None
    n_tr = 0
    wins = 0
    tr_ret = []
    entry_date = None

    for i in range(n):
        day = days[i]
        if in_pos:
            if i == entry_i:
                # entry day: open se close tak
                op = dopen.get(day, np.nan)
                ret = (cl.iloc[i] / op - 1) if not np.isnan(op) else 0.0
            else:
                ret = (cl.iloc[i] / cl.iloc[i - 1] - 1) if cl.iloc[i - 1] > 0 else 0.0
            # cost entry side
            if i == entry_i:
                ret -= cost_side
            eq[i] = eq[i - 1] * (1 + sign * ret)
            hold_left -= 1
            if hold_left <= 0:
                # exit at close, pay exit cost
                eq[i] *= (1 - cost_side)
                in_pos = False
                r = (cl.iloc[i] / dopen.get(entry_date, cl.iloc[entry_i - 1] if entry_i > 0 else cl.iloc[entry_i]) - 1) * sign - 2 * cost_side
                tr_ret.append(r)
                n_tr += 1
                if r > 0:
                    wins += 1
        else:
            eq[i] = eq[i - 1] if i > 0 else 1.0
            if day in sig_days:
                if not gate_on:
                    g = True
                else:
                    g = prev_scn[i] is not None and prev_scn[i] in gate_list
                if g:
                    in_pos = True
                    hold_left = hold_days
                    entry_i = i
                    entry_date = day

    r_daily = pd.Series(np.diff(eq) / eq[:-1], index=d.index[1:])
    r_daily = r_daily.replace([np.inf, -np.inf], np.nan).fillna(0)
    years = len(r_daily) / 252
    tot = (eq[-1] - 1) * 100
    cagr = ((eq[-1]) ** (1 / years) - 1) * 100 if eq[-1] > 0 else -100
    sharpe = r_daily.mean() / r_daily.std() * np.sqrt(252) if r_daily.std() > 0 else 0
    cum = pd.Series(eq, index=d.index)
    dd = ((cum / cum.cummax()) - 1).min() * 100
    expo = (r_daily != 0).mean() * 100
    return dict(eq=eq, daily=r_daily, tot=tot, cagr=cagr, sharpe=sharpe, mdd=dd,
                trades=n_tr, win=100 * wins / n_tr if n_tr else 0, expo=expo,
                avg_ret=100 * np.mean(tr_ret) if tr_ret else 0)


# ---------------- run variants ----------------
print("=" * 110)
print(f"{'variant':<40}{'n_tr':>5}{'win%':>6}{'expo%':>7}{'total%':>9}{'CAGR%':>8}{'Sharpe':>8}{'MDD%':>8}{'avg/tr%':>9}")
print("-" * 110)
rows = []

def run(label, direction, gate_list, hold, cost, gate_on=True):
    r = simulate(direction, gate_list, hold, cost, gate_on)
    rows.append((label, r))
    print(f"{label:<40}{r['trades']:>5}{r['win']:>5.0f}%{r['expo']:>6.0f}%{r['tot']:>+8.1f}%{r['cagr']:>+7.1f}%"
          f"{r['sharpe']:>8.2f}{r['mdd']:>+7.1f}%{r['avg_ret']:>+8.2f}%")

COST0, COST = 0.0000, 0.0005  # 0.05%/side = 0.10% rt
# LONG variants
run("LONG gate-BULL-LEAN hold-10 (0.1% rt)", "long", BULL_LEAN, 10, COST)
run("LONG gate-BULL-LEAN hold-20 (0.1% rt)", "long", BULL_LEAN, 20, COST)
run("LONG NO-gate hold-20 (0.1% rt) [baseline]", "long", [], 20, COST, gate_on=False)
run("LONG gate-BULL-LEAN hold-20 (0 cost)", "long", BULL_LEAN, 20, COST0)
run("LONG STRICT-TREND gate hold-20 (0.1% rt)", "long",
    ["ALL-ALIGN BULL", "EARLY-UP", "STRONG-FLOW"], 20, COST)
# SHORT variants
run("SHORT gate-BEAR-LEAN hold-10 (0.1% rt)", "short", BEAR_LEAN, 10, COST)
run("SHORT gate-BEAR-LEAN hold-20 (0.1% rt)", "short", BEAR_LEAN, 20, COST)
run("SHORT NO-gate hold-20 (0.1% rt) [baseline]", "short", [], 20, COST, gate_on=False)
# B&H reference
bh = (100 * (cl.iloc[-1] / cl.iloc[0] - 1))
bh_daily = 100 * cl.pct_change().dropna()
years_bh = len(bh_daily) / 252
bh_cagr = ((cl.iloc[-1] / cl.iloc[0]) ** (1 / years_bh) - 1) * 100
bh_sharpe = bh_daily.mean() / bh_daily.std() * np.sqrt(252)
print(f"{'BUY & HOLD NIFTY (benchmark)':<40}{'':<5}{'':<6}100%{bh:>+8.1f}%{bh_cagr:>+7.1f}%{bh_sharpe:>8.2f}{'':<8}{'':<9}")

# ---------------- best variant equity + year table ----------------
# datetime index convert (year table ke liye)
d.index = pd.to_datetime(d.index)
cl = d["Close"]
best = [r for l, r in rows if l.startswith("LONG gate-BULL-LEAN hold-20 (0.1")][0]
eq = pd.Series(best["eq"], index=d.index)
d["eq_strat"] = eq
d["eq_bh"] = (cl / cl.iloc[0])
d["strat_ret"] = best["daily"]

yr = pd.DataFrame({
    "year": d.index.year,
    "strat": d["eq_strat"].pct_change().fillna(0),
    "bh": d["eq_bh"].pct_change().fillna(0),
})
g = yr.groupby("year").agg(
    strat_ret=("strat", lambda x: (1 + x).prod() - 1),
    bh_ret=("bh", lambda x: (1 + x).prod() - 1),
    strat_days_in=("strat", lambda x: (x != 0).sum()),
)
# trades per year
sig_days_used = best.get("trades")
print(f"{'year':<7}{'strat%':>10}{'B&H%':>10}{'din_in':>8}{'strat<=B&H?':>12}")
for y, row in g.iterrows():
    if row["strat_days_in"] == 0:
        continue
    print(f"{y:<7}{100*row['strat_ret']:>+9.1f}%{100*row['bh_ret']:>+9.1f}%{int(row['strat_days_in']):>7}{'BETTER' if row['strat_ret']>row['bh_ret'] else 'worse':>12}")
up_years = (g["strat_ret"] > g["bh_ret"]).sum()
print(f"\nYears strat beat B&H: {up_years}/{len(g)}")
print(f"Green years (strat>0): {(g['strat_ret']>0).sum()}/{len(g)}")

# save equity csv + png
pd.DataFrame({"eq_strat": eq, "eq_bh": cl / cl.iloc[0], "close": cl}).to_csv(
    os.path.join(HERE, "combo_curve_equity.csv"))
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    BG, GRID, MUT = "#0f172a", "#334155", "#94a3b8"
    fig, ax = plt.subplots(figsize=(13, 6), facecolor=BG)
    ax.set_facecolor(BG)
    ax.plot(d.index, eq, label=f"Stage-gated 1H cross (Sharpe {best['sharpe']:.2f})", color="#22d3ee", lw=1.3)
    ax.plot(d.index, cl / cl.iloc[0], label="Buy & Hold NIFTY", color="#fbbf24", lw=1.0, alpha=0.8)
    for sp in ["top", "right"]:
        ax.spines[sp].set_visible(False)
    ax.tick_params(colors=MUT, labelsize=9)
    ax.grid(True, alpha=0.15, color=GRID)
    ax.legend(facecolor=BG, edgecolor=GRID, labelcolor="white", fontsize=10)
    ax.set_title("Combo: 1H MACD cross + daily BULL-LEAN gate, hold-20d, 0.1% rt — REAL NIFTY",
                 color="white", fontsize=12, loc="left")
    plt.tight_layout()
    plt.savefig(os.path.join(HERE, "combo_curve_equity.png"), dpi=130, facecolor=BG)
    print("\nSaved: combo_curve_equity.csv + combo_curve_equity.png")
except Exception as e:
    print("png fail:", e)
