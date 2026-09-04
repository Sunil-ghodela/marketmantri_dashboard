# 10 Stocks — Momentum Rank Filter Test (4 Sep 2026)

Har cycle boundary ke close pe rank karo → top-N (equal weight) → next open
pe enter → cycle end close pe exit. Net = gross − 0.12%/name/cycle. Data
2015-01→Sep 2026, Yahoo .NS, split-adjusted closes, dividends excluded,
in-sample (context — proof nahi). Score variants: stage-score (stage pts +
SMA50/SMA200 + RSI band) aur return-percentile blends.

## Results (net, ₹100 start)

| Strategy | Total | CAGR | MDD | Win | Avg/cycle |
|---|---|---|---|---|---|
| TOP5 · 15-din hold (stage-score) | −15.0% | −1.4% | −35.4% | 50% | −0.00 |
| TOP5 · weekly 5-din (stage-score) | **−95.1%** | −22.8% | −95.3% | 40% | −0.49 |
| TOP3 · 15-din hold (stage-score) | +20.7% | 1.6% | −40.7% | 55% | +0.18 |
| ALL-10 EW · 15-din | −69.2% | −9.6% | −70.5% | 42% | −0.54 |
| TOP5 · 1-mo hold, **3-mo momentum** mix | +13.8% | 1.1% | −32.2% | 53% | +0.22 |
| TOP5 · 1-mo hold, pure 3-mo momentum | +31.4% | 2.4% | −35.0% | 53% | +0.33 |
| **TOP5 · 1-mo hold, 6-mo momentum** mix | **+76.8%** | **5.0%** | −29.1% | 55% | +0.54 |
| NIFTY index buy-hold (benchmark) | +71.7% | 4.7% | — | — | — |

## Direction — kya mila

1. **Stage-score ka 15-din cycle ~zero edge** (−0.00/cycle, win 50%) —
   chhota hold + chhota universe = mean-reversion kha jata hai. TOP3 behtar
   par abhi bhi kamzor. **Weekly churn catastrophic** (−95%) — turnover ka
   poison; weekly rebalance isi universe pe never.
2. **6-mo momentum + monthly (1-mo) hold + top5 = NIFTY ke barabar/behtar**
   (+76.8% vs +71.7%, MDD −29% index jaisa) — classic long-horizon momentum
   is data me bhi edge rakhta hai; short-horizon nahi.
3. All-10 EW itself −69% vs index +71% → ye 10 large-caps (raw price, bina
   dividend) ne index ko beat nahi kiya; **index har gaya is universe ko** —
   isliye "top-N pick karna" ka fayda selection ka, hold nahi.
4. **Aaj (4 Sep) ka rank:** RELIANCE, ICICIBANK, TCS, INFY, LT top-5 —
   par scores sab kam (0/10 BUY stage) → weak breadth; ye ranking sirf
   agle monthly cycle ke liye reference hai, entry signal nahi.

## Aage (kya test karein — Basket Restart ke saath)

1. **Universe badhao** (10 → 40-90 liquid names) — cross-sectional momentum
   ka edge small universe me aata hi nahi; Basket Restart ka 46-name universe
   yahi hai. 6-mo momentum + 1-mo hold + top-25% wahi test do.
2. **Stage map + 6-mo momentum blend** ko large universe pe rank filter banao
   (stage = regime filter, 6-mo = edge) — 3-mo vs 6-mo vs 12-mo horizon scan.
3. **Forward paper** (3-6 mahina) sirf best config pe, edge/cost ≥1.3x gate.
4. Cost model sharp karo (options/stocks actual spread) — 0.12%/cycle rough
   estimate hai.

Files: `rank_test.py` (reproduce), `rank_cycles.csv`, `rank_summary.json`,
`rank_equity.png` (equity curves). Run: `python3 state/multistock/rank_test.py`.
