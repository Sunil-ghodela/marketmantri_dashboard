"""Trend-days-only long test: NIFTY long ONLY when prior day's scenario is in the
bull-trend bucket (ALL-ALIGN BULL, EARLY-UP, STRONG-FLOW) — the ~9.1% of days.
Causal: decision at prior day close (scenario[D-1]), hold during day D close-to-close.
"""
import pandas as pd
import numpy as np

DAILY = "state/nifty_daily_state.csv"

df = pd.read_csv(DAILY, parse_dates=["Date"]).set_index("Date")
df["r"] = df["Close"].pct_change() * 100
df = df.dropna(subset=["r"])

BUCKET = ["ALL-ALIGN BULL", "EARLY-UP", "STRONG-FLOW"]

# position on day D decided by scenario on D-1 (prior completed day)
prev = df["scenario"].shift(1)
pos = prev.isin(BUCKET).astype(float)
pos[prev == "WARMUP"] = 0.0
df["pos"] = pos
df["strat_r"] = pos * df["r"]

def stats(series, label, n_switch, cost_rt):
    eq = (1 + series / 100).cumprod()
    years = len(series) / 252
    tot = (eq.iloc[-1] - 1) * 100
    cagr = (eq.iloc[-1] ** (1 / years) - 1) * 100
    sharpe = series.mean() / series.std() * np.sqrt(252) if series.std() > 0 else 0
    dd = ((eq / eq.cummax()) - 1).min() * 100
    net = tot - n_switch * cost_rt * 100
    return dict(label=label, days_in=series[series != 0].size, days_pct=(series[series != 0].size / len(series)) * 100,
                total=tot, cagr=cagr, sharpe=sharpe, mdd=dd, n_switches=n_switch, total_net_cost=net)

rows = []
rows.append(stats(df["strat_r"], "TREND-DAYS LONG (9.1%)", int((pos.diff().abs() != 0).sum()), 0.0005))
rows.append(stats(df["r"], "BUY & HOLD", 1, 0.0))

# variant: also include CHOP-UP (momentum-lean days)
for extra, name in [(["CHOP-UP"], "BULL+CHOP-UP"), (["CHOP-UP", "CHOP-MID"], "ALL-CHOP+ (long always)")]:
    p2 = prev.isin(BUCKET + extra).astype(float)
    p2[prev == "WARMUP"] = 0.0
    s2 = p2 * df["r"]
    rows.append(stats(s2, name, int((p2.diff().abs() != 0).sum()), 0.0005))

out = pd.DataFrame(rows).set_index("label")
print(out.round(2).to_string())
print()
print("Buy&hold total %:", round(out.loc['BUY & HOLD','total'], 1), "| TREND-DAYS total %:", round(out.loc['TREND-DAYS LONG (9.1%)','total'], 1))
print("Sharpe TREND-DAYS:", round(out.loc['TREND-DAYS LONG (9.1%)','sharpe'], 2), "vs B&H:", round(out.loc['BUY & HOLD','sharpe'], 2))
print("Days in market:", out.loc['TREND-DAYS LONG (9.1%)','days_in'], f"({out.loc['TREND-DAYS LONG (9.1%)','days_pct']:.1f}%)")
print("Avg % per in-market day:", round(out.loc['TREND-DAYS LONG (9.1%)','total'] / out.loc['TREND-DAYS LONG (9.1%)','days_in'], 2))

# equity curve save
eq = (1 + df["strat_r"] / 100).cumprod()
eq_bh = (1 + df["r"] / 100).cumprod()
pd.DataFrame({"trend_days": eq, "buy_hold": eq_bh}, index=df.index).to_csv("state/trend_hold_equity.csv")
print("\nSaved state/trend_hold_equity.csv")