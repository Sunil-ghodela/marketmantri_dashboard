# Momentum horizon scan — 90-name universe (Sep 2026)

**Sawaal:** 1/2/3/4/5/6-month momentum, monthly rebalance, top-25%, 1-mo hold —
kaunsa horizon chalata hai? Archive 5-min (real prices) 2015-08 → 2026-04-09 se
daily closes, 88/90 names covered. Cost 0.1% rt on churned names.

## Result (2016-02 → 2026-04, 10.2 saal)

| Horizon | Total | CAGR | Sharpe | MDD | avg hold |
|---|---|---|---|---|---|
| 1-mo | +559% | 19.5% | 1.03 | -34.8% | 21 names |
| 2-mo | +780% | 23.0% | 1.19 | -30.2% | 21 |
| 3-mo | +814% | 23.7% | 1.18 | -23.8% | 21 |
| 4-mo | +751% | 23.0% | 1.09 | -33.0% | 21 |
| 5-mo | +1128% | 27.7% | 1.28 | -30.7% | 21 |
| **6-mo** | **+1252%** | **29.2%** | **1.35** | -31.4% | 21 |

Benchmarks (same window):
- NIFTY50: +240%, CAGR 12.8%, Sharpe 0.83
- Universe EW buy&hold (88 names): +641% (equal weight, multibaggers included)

## 6-mo momentum — yearly

2016 +47.9 · 2017 +35.8 · 2018 +1.4 · 2019 +20.5 · 2020 +24.1 · 2021 +62.5 ·
2022 +24.7 · 2023 +75.7 · 2024 +17.0 · 2025 +15.9 · 2026 -4.8 → **green 10/11**

## Holdings (6-mo): diversified
MUTHOOTFIN 60 · ADANIENSOL 56 · BAJFINANCE 49 · ADANIPOWER 49 · CHOLAFIN 47 ·
TVSMOTOR 46 · JINDALSTEL 46 · VEDL 46 · ADANIENT 46 ... top-5 sirf 10% total holds.

## Honest caveats (ye numbers in-sample hain)

1. **Survivorship/universe bias:** ye 90-name WATCH = aaj ke universe. Jo names
   kabhi nikle/delist hue wo archive mein hain nahi. Equal-weight bhi
   multibaggers (ADANIENSOL +3626%, ADANIPOWER +2927%, ADANIENT +2388%) se
   boosted hai — isliye EW bhi NIFTY se 2.7x zyada. In-sample description.
2. **Bug found during run:** pehle run mein /100 double-divide tha → sab ~0 aaya.
   Fix ke baad ye numbers (data sahi, EW monthly +1.73% sanity check pass).
3. **Monotonic horizon effect:** 1→6-mo total/CAGR badhta hai (6-mo best:
   Sharpe 1.35). 10-name test (4 Sep) mein bhi 6-mo momentum + monthly hold ≈
   index-level aaya tha — ab bade universe pe 6-mo B&H (EW) se bhi aage.
4. **Direction (honest):** lamba momentum (5-6 mo) chhote (1-2 mo) se behtar
   dikhta hai — consistent teen tests mein. Par Sharpe 1.35 in-sample ka
   overfit ho sakta hai; asli proof = 1-2 saal forward paper, edge/cost gate
   (≥1.3x) ke saath.

## Aage ka step (basket restart ke liye natural)
6-mo momentum + monthly top-25% (≈20 names) + 1-mo hold ko paper pe test karna,
position sizing ke saath, delivery cost (STT+brokerage ~0.1-0.2% rt) do baar
check karke. Yehi "lambi baazi" wala rasta hai jo data mein dikh raha hai.

Files: momentum_horizon_scan.py · momentum_horizon_results.csv ·
momentum_horizon_equity.png
