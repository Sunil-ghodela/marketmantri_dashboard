# Stocks combo test — 1H MACD cross + BULL-LEAN gate, 10 liquid names (Sep 2026)

Wahi NIFTY combo rule (state/combo_curve.py) 10 large-caps pe. 1H bars archive
5-min (2015-02 → 2026-04-09), daily state from stocks_prices.csv (real Yahoo
.NS, 04 Sep tak), prev-day BULL-LEAN gate, entry next open, hold-20, cost 0.1%
rt, no overlap. Per-stock equity → equal-weight basket.

## Per stock (hold-20, 0.1% rt) — combo vs us stock ka apna B&H

| sym | combo tot | B&H tot | combo Sh | B&H Sh | combo CAGR | B&H CAGR | Sharpe better? |
|---|---|---|---|---|---|---|---|
| RELIANCE | +380% | +537% | **0.87** | 0.74 | +14.8% | +17.7% | YES |
| BHARTIARTL | +267% | +468% | **0.69** | 0.67 | +12.1% | +16.5% | YES |
| HDFCBANK | +100% | +163% | **0.51** | 0.49 | +6.3% | +8.9% | YES (marginal) |
| INFY | +73% | +112% | 0.35 | 0.38 | +4.9% | +6.8% | no |
| SBIN | +60% | +230% | 0.30 | 0.48 | +4.2% | +11.1% | no |
| LT | +60% | +243% | 0.33 | 0.54 | +4.2% | +11.4% | no |
| HINDUNILVR | +24% | +117% | 0.20 | 0.42 | +1.9% | +7.1% | no |
| ICICIBANK | +20% | +345% | 0.18 | 0.59 | +1.6% | +14.0% | no |
| TCS | +12% | +83% | 0.14 | 0.34 | +1.0% | +5.5% | no |
| ITC | -2% | +14% | 0.07 | 0.17 | -0.2% | +1.2% | no |

## Basket (equal-weight 10) — yearly

| year | combo | EW B&H |
|---|---|---|
| 2015 | -7.1% | -7.7% |
| 2017 | +19.7% | +39.8% |
| 2020 | +14.6% | +18.1% |
| 2022 | +7.9% | +12.8% |
| 2024 | +8.1% | +13.4% |
| 2026* | -5.1% | -15.6% |

Basket: COMBO **+100.3%** CAGR 6.3% Sharpe **0.77** MDD **-15.3%** · EW B&H
+277.3% CAGR 12.4% Sharpe 0.81 MDD -34.5%. Combo beat B&H 2/12 years.

## Honest conclusion

1. **"Stocks pe improve" — absolute return mein NAHI.** Har stock pe combo ka
   total B&H se KAM hai (RELIANCE +380% vs +537%, ICICI +20% vs +345%). 10
   mein se 8 pe Sharpe bhi behtar nahi.
2. **Risk-adjusted sirf 2-3 trending names pe** (RELIANCE Sharpe 0.87 vs 0.74
   — asli; BHARTIARTL/HDFCBANK marginal). Jo naam trend karte hain, unme
   gate drawdown kam karta hai bina Sharpe kharab kiye.
3. **MDD har jagah 2x chhota** (basket -15% vs -34%; NIFTY -17% vs -38%) —
   ye combo ka SIRF consistent fayda hai: B&H jaisa risk-adjusted, aadha
   drawdown, aadha time market mein.
4. Pattern ab teeno tests mein same: **edge lambi hold mein hai, par market ka
   drift itna strong hai ki time se bahar rehna absolute paisa chhod deta
   hai.** Gate "suraksha" deta hai, "alpha" nahi.
5. In-sample 11 saal, koi forward paper nahi. RELIANCE-type single-name
   selection ka asli proof forward test hi dega.

Files: stocks_combo_curve.py · stocks_combo_equity.csv · stocks_combo_equity.png
