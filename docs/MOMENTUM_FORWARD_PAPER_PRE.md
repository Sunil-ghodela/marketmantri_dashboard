# Momentum Forward Paper — PRE-REGISTERED RULES (5 Sep 2026)

> Ye rules aaj (5 Sep 2026) **pehle se likh diye gaye hain** — paper shuru
> hone se pehle. Jo in-sample result aaya wo claim nahi hai; ye paper hi
> asli proof hai. Gate: edge/cost >= 1.3x ya Sharpe >= 0.9 (12-mo rolling)
> tabhi is system ko "kaam karta hai" bolenge.

## System naam: 6M-MOM-21-SMA50

### Universe
- 90-name WATCH (core/momentum_portfolio_feed.py) — archive-available names.
- Kyunki data live update hota rahega, jo names data miss karein wo skip
  (survivorship live mein nahi bach sakta — naye listing aate rahenge).

### Rebalance (Monthly)
- **Har month-end (last trading day) close pe** naya portfolio banao.
- Signal = 6-mo momentum: close / close(6 months pehle) - 1.
- Rank saare names (jinke paas data hai). Top-25% (≈21 names) lo.
- Equal weight.

### Gate (NIFTY regime)
- Rebalance day pe **NIFTY (^NSEI) close < SMA200** ho to exposure = **50%**
  (aadha capital cash), warna 100%.
- NIFTY SMA200 bhi usi din ke data se.

### Hold & Exit
- Agle month-end tak hold (1 month). Month-end pe fresh rebalance.
- **Koi intra-month exit nahi, koi stop-loss nahi** — ye design choice hai
  (DD control gate se aata hai, stop se nahi). Ye likh kar rakh rahe hain
  taaki beech mein rules na badle.

### Cost model (paper mein lagao)
- 0.1% round-trip churn cost har name pe jo portfolio badle (0.05% entry +
  0.05% exit). Report gross AND net dono.

### Paper protocol
- Har month-end: is doc ke saath `state/multistock/momentum_paper_log.csv`
  mein row append (date, portfolio names, NIFTY vs SMA200, exposure, entry
  prices). Agle month-end: exit prices, month return, cumulative equity.
- Monthly review: edge/cost ratio + rolling Sharpe + MDD vs baseline (bina
  gate ke paper bhi parallel chale — comparison ke liye).
- **Fail conditions (paper rukega):** 6 consecutive red months, ya monthly
  MDD > 12%, ya annualized rolling Sharpe < 0.5 for 6 months.

## In-sample reference (5 Sep 2026, archive 2016-02 → 2026-04)
Ye SIRF reference hai, claim nahi:
- Baseline 6M-MOM-21: CAGR 27.5%, Sharpe 1.30, MDD -40.6%
- SMA-50%: CAGR 24.4%, Sharpe 1.31, MDD -27.4%, 2026 Q1 +2.8%
- SMA-CASH: CAGR 21.0%, Sharpe 1.21, MDD -20.0%

## Start
Paper pehli rebalance **agle month-end (30 Sep 2026)** se — rules aaj locked.
Jab tak data nahi hai, is doc mein koi badlav nahi.
