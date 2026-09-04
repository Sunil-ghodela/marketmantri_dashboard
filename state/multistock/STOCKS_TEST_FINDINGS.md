# 10 Liquid Stocks — Stage Pipeline Test (4 Sep 2026)

**Kya test kiya:** NIFTY wali state pipeline (indicators + 10 stage buckets +
T1/T2 entry tiers) 10 sabse liquid large-caps pe — RELIANCE, TCS, HDFCBANK,
ICICIBANK, INFY, HINDUNILVR, ITC, SBIN, BHARTIARTL, LT.
Data: Yahoo `.NS` daily, 2013→4 Sep 2026 (3,379 din/stock). Raw prices —
dividend-adjusted nahi, costs/slippage nahi, in-sample.

## 1. Cadence — target MILA (universe se monthly signals aate hain)

| Metric | NIFTY single index | 10-stock basket |
|---|---|---|
| Quality entries (T1+T2) | 17 in 12 saal (93% months zero) | **825 in 12 saal (avg 5.9/month)** |
| Months with ≥1 entry | ~7% | **95%** |
| Months with ≥2 entries | ~3% | **89%** |
| Max in ek month | — | 17 (Jul 2017) |

**Direction:** "month me 1-4 trades" ka rasta index nahi, **universe** hai —
kisi bhi mahine 10 names se 2-6 candidates milte hain. Basket/Restart wala
point yahi tha.

## 2. Per-trade edge — almost ZERO (naive daily T1/T2, cost se pehle)

Mini-engine: entry = signal ke **next open**, stop = −2×ATR, exit = stage
bull-family chhode pe / stop / max 15 din.

| Set | n | Win | Avg/trade | Median | Avg hold |
|---|---|---|---|---|---|
| T1 fresh-trend | 550 | 38% | **+0.11%** | −0.76% | 8 din |
| T2 re-accel | 275 | 40% | +0.34% | −0.60% | 9 din |
| ALL | 825 | 39% | **+0.19%** | −0.76% | 8 din |

Exit breakup: **stage-exit 530 × −1.88% avg** (barbaad karta hai — stage flip
pe bechna = pullback mein bechna), stop 26 × −4.6%, **time-exit (15 din) 269 ×
+4.72%** (saara paisa yahi hai — right tail). Year-wise: mix (2014/2017/2020
+ve, 2015/16/19/24 −ve) — koi robust edge pattern nahi.

**Cost ke baad yeh ~0 edge hai** (CE spread/fees ~0.1-0.3%/trade khayega).
NIFTY index pe dikhne wala +4.9% TREND-UP follow edge **stocks pe nahi utra**:
single stock ka daily "TREND UP" din local top ke paas aata hai, aur
stage-flip exit pullback mein nikalta hai.

## 3. Aaj ka breadth — risk-off (direction)

| Stock | Stage | Action | | Stock | Stage | Action |
|---|---|---|---|---|---|---|
| RELIANCE | CHOP-UP | WATCH | | ITC | **BEAR** | AVOID |
| TCS | CHOP-MID | STAND-ASIDE | | SBIN | CHOP-DOWN | STAND-ASIDE |
| HDFCBANK | **BEAR** | AVOID | | BHARTIARTL | CHOP-DOWN | STAND-ASIDE |
| ICICIBANK | CHOP-MID | STAND-ASIDE | | LT | CHOP-DOWN | STAND-ASIDE |
| INFY | CHOP-MID | STAND-ASIDE | | HINDUNILVR | **BEAR** | AVOID |

**0/10 BUY · 1 WATCH · 9 stand/avoid** — 3 names TREND DOWN (HDFCBANK, ITC,
HINDUNILVR), baaki sab chop. Index bhi CHOP-DOWN. Market-wide **no fresh
long zone** — yehi signal abhi.

## 4. Aage ka direction (kya kaam karega — ye test bata raha hai)

1. **Daily T1/T2 stage-chase stock level pe bekaar** — mat banao isi pe real
   system. Entry zyada selective chahiye.
2. **Jo chala: time-hold (15 din) aur T2 (pullback re-accel, +0.34%)** —
   momentum ka paisa "pakdo aur 2-3 hafte ruko" mein hai, stage-flip pe jaldi
   exit mein nahi (yaha exit-cross removal wala NIFTY finding repeat hua).
3. **Asli candidate: stage map as FILTER on basket weekly/monthly momentum**
   — 10 names roz dekhne ke bajaye: mahine ki shuruaat mein stage/trend
   rank karo (ALL-ALIGN/STRONG-FLOW names), top 5 lo, 15 din hold — yahi
   Basket Restart ke entry-filters se milta hai (flat + no Wed/Thu + cross-exit
   remove wale configs).
4. **Forward test spec:** in 10 names pe weekly momentum ranking + 15-din hold
   ka paper 3-6 mahine; edge/cost ≥1.3x hi aage.

Files: `stocks_prices.csv` (raw data) · `stocks_state_latest.csv` (aaj ka 10-name
state) · `stocks_signals_all.csv` (saare 825 signals + outcome) ·
`basket_test_summary.json`. Reproduce: `python3 state/multistock/fetch_stocks.py`
phir `build_stocks.py`.
