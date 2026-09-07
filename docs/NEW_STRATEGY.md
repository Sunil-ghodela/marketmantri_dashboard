# NEW STRATEGY — NIFTY + Universe Tests ka Poora Record (7 Sep 2026)

> Ye doc **nayi strategy** ke liye hai — dono taraf ke saare tests ka record:
> **(A) NIFTY wale tests** (live-engine verify + timeframe scan) aur
> **(B) Universe wale tests** (90-name momentum scan + 10-stock rank/stage/combo).
> Har table, har number, har caveat — sab ek jagah. In-sample numbers **claim
> nahi** hain; forward paper (30 Sep se) hi asli proof hai.
>
> Live dekho: `strategy_docs.html` (Vercel) · Sources: `state/multistock/*FINDINGS.md`

---

## 🎯 Ek line me nateeja

1. **NIFTY:** edge **30m–1h zone** ka hai (15m/4h dead). Long-only + daily-state
   gate (BEAR/AVOID-skip) = **Sharpe 1.04, maxDD aadha (−18% vs −38%)**.
2. **Universe:** **6-mo momentum + monthly top-25% + 1-mo hold = Sharpe 1.35**
   in-sample (+1252% / 10.2 saal) — lambi baazi hi rasta hai.
3. **Nayi strategy locked (5 Sep):** `6M-MOM-21-SMA50` — NIFTY gate (SMA200 →
   50%) ke saath. **Pehli rebalance 30 Sep 2026.** Sab in-sample reference hai.

---

## A) NIFTY WALE TESTS

Engine (dono tests ka): 1H MACD(12/26/5) completed-bar cross, 2% stop (15m
closes), max-hold 18 wall-clock hours, 0.06% rt cost, no divergence.
Data: 62,437 15m bars (2016-07-25 → 2026-09-04) = `state/nifty_15m_full.feather`.

### A1. Live-engine verify — 3 books (6 Sep)

| Book | n | WR% | net% | avg/trade | maxDD | Sharpe(m) |
|---|---:|---:|---:|---:|---:|---:|
| flat 1x | 1594 | 37.7 | +46.02 | +0.0289 | 25.61 | 0.45 |
| **B+sized (W/L 2x/2.5x/3x)** | 1594 | 37.7 | **+159.93** | +0.1003 | 37.59 | **0.85** |
| filter(cl≥2) 1x | 1594 | 14.9* | +73.19 | +0.0459 | **13.71** | 0.96 |

\* filter book ki WR sirf "taken" trades pe hai — haar-ke-baad wali trades leta
hai, isliye % kam par avg zyada → net positive.

**Yearly (sized):** 2016 +4.7 · 2017 +13.4 · 2018 +16.8 · 2019 +22.7 · 2020
+16.6 · 2021 +20.0 · 2022 +27.1 · 2023 +0.2 · 2024 +26.6 · 2025 +5.9 ·
2026 +6.0 → **11/11 saal green** (22 Jul–4 Sep ke CHOP din jodne pe sized ~5%
kam hua, doc 21 Jul wale +165.3 vs ab +159.9).

### A2. Entry-hour + weekday lab (10 saal, flat 1x) — direction, rule NAHI

| Entry hour | n | WR% | net% | avg% |
|---|---:|---:|---:|---:|
| 9 | 221 | 39.4 | +28.31 | **+0.1281** |
| 10 | 400 | 41.2 | +31.46 | **+0.0787** |
| 11 | 231 | 30.7 | −21.19 | **−0.0917** ❌ |
| 12 | 158 | 40.5 | +11.69 | +0.0740 |
| 13 | 191 | 34.6 | −4.42 | −0.0231 |
| 14 | 171 | 35.1 | −3.75 | −0.0219 |
| 15 | 218 | 39.4 | +1.97 | +0.0090 |

- Weekday: **Fri best (+48.9, avg +0.158) · Wed sabse kharab (−12.5)** — basket
  ke `no_wed_thu` finding se consistent.
- **Post-hoc bucket tha — timeframe scan ne formally REJECT kiya (A4).**

### A3. Daily-state gate combine (prev-day scenario, sized) — JAWAB: long-only

| Variant | n | net(sized)% | maxDD | Sharpe | WR% |
|---|---:|---:|---:|---:|---:|
| no-gate (live, flip) | 1594 | +159.93 | 37.59 | 0.85 | 37.7 |
| gate: bull→long / bear→short | 685 | +76.54 | 30.83 | 0.52 | 38.4 |
| **long sirf (BEAR/AVOID prev-day pe entry nahi)** | 389 | +81.16 | **18.28** | **1.04** | 40.1 |

Bucket split (flat, long vs short): **longs har bucket me positive** (BEAR/AVOID
+0.09, BULL-LEAN +0.11, CHOP-MID +0.12 avg). **Shorts bekaar** — BULL-LEAN
−0.06, CHOP-MID −0.18 (1 Aug ka "shorts bekaar" ab full-data pe confirm).

**Matlab:** state-gate ka saaf jawab = **long-only bano**. Return aadha, DD
aadha, Sharpe behtar.

### A4. Timeframe scan — 15m/30m/1h/2h/4h (6 Sep) — JAWAB: 30m–1h zone

Sawaal tha: kya Sharpe 1.04 sirf 1h ka artefact hai? **Nahi — par edge
"30m–1h zone" ka hai, 15m/4h pe mar jaata hai.**

| tf | n | net% | maxDD% | Sharpe(m) | WR% |
|---|---:|---:|---:|---:|---:|
| 15m | 1511 | **−32.80** | 55.21 | **−0.26** ❌ | 35.3 |
| **30m** | 765 | **+93.52** | **13.52** | **0.87** | 38.7 |
| **1h** | 389 | +81.16 | 18.28 | **1.04** | 40.1 |
| 2h | 210 | +41.20 | 17.92 | 0.65 | 46.7 |
| 4h | 92 | +3.54 | 10.45 | **0.11** ❌ | 48.9 |

- 30m: net +93.5% (1h se ZYADA), DD 13.5 (KAM) — dono ek zone ke do chehre.
- 15m = poison (whipsaw + fees); 4h = signal hi nahi milta (92 trades/10 saal).
- **Entry-hour 9-10 filter: REJECTED** — har timeframe pe Sharpe giraya
  (1h 1.04→0.69, 30m 0.87→−0.14). Post-hoc bucket, tradeable nahi.

---

## B) UNIVERSE WALE TESTS

### B1. Momentum horizon scan — 90-name universe (5 Sep)

Archive 5-min real prices (2015-08 → 2026-04-09) se daily closes, 88/90 names.
Monthly rebalance, top-25% (~21 names), 1-mo hold, 0.1% rt churn.

| Horizon | Total | CAGR | Sharpe | MDD |
|---|---:|---:|---:|---:|
| 1-mo | +559% | 19.5% | 1.03 | −34.8% |
| 2-mo | +780% | 23.0% | 1.19 | −30.2% |
| 3-mo | +814% | 23.7% | 1.18 | −23.8% |
| 4-mo | +751% | 23.0% | 1.09 | −33.0% |
| 5-mo | +1128% | 27.7% | 1.28 | −30.7% |
| **6-mo** | **+1252%** | **29.2%** | **1.35** | −31.4% |

Benchmarks (same window): **NIFTY50 +240% (CAGR 12.8%, Sharpe 0.83)** ·
**Universe EW B&H +641%** (multibaggers included).

6-mo yearly: 2016 +47.9 · 2017 +35.8 · 2018 +1.4 · 2019 +20.5 · 2020 +24.1 ·
2021 +62.5 · 2022 +24.7 · 2023 +75.7 · 2024 +17.0 · 2025 +15.9 · 2026 −4.8 →
**green 10/11 saal**.

⚠️ Caveats: survivorship/universe bias (aaj ka 90-name WATCH), in-sample,
Sharpe 1.35 overfit ho sakta hai. Run ke beech mein `/100` double-divide bug
mila tha — fix ke baad ye numbers (sanity pass).

### B2. 10-stock rank filter test (4 Sep)

| Strategy (net, ₹100 start) | Total | CAGR | MDD | Avg/cycle |
|---|---:|---:|---:|---:|
| TOP5 · 15-din hold (stage-score) | −15.0% | −1.4% | −35.4% | −0.00 |
| TOP5 · **weekly** 5-din (stage-score) | **−95.1%** | −22.8% | −95.3% | −0.49 |
| TOP5 · 1-mo hold, **6-mo momentum** | **+76.8%** | 5.0% | −29.1% | +0.54 |
| NIFTY index buy-hold (bench) | +71.7% | 4.7% | — | — |

**Sabak:** weekly churn = poison (−95%). 6-mo momentum + monthly hold = index
ke barabar/behtar. Selection ka fayda lambi hold me hai, short-horizon me nahi.

### B3. 10-stock stage pipeline test (4 Sep)

- **Cadence MILA:** 825 quality entries / 12 saal = **5.9/month**, 95% months
  ≥1 (NIFTY akela: 17/12 saal, 93% months zero) → monthly cadence universe se
  aata hai, index se nahi.
- **Per-trade edge ~zero pre-cost:** T1 +0.11%, T2 +0.34%, ALL +0.19% avg.
- Exit breakup: **stage-flip exit 530 × −1.88%** (pullback me bechta hai —
  barbaad), stop 26 × −4.6%, **time-exit 15-din 269 × +4.72%** (saara paisa).
- Aaj ka breadth: **0/10 BUY** (HDFCBANK/ITC/HINDUNILVR TREND DOWN) — risk-off.

### B4. Stocks combo test — 1H MACD + BULL-LEAN gate, 10 names (Sep)

| | Combo | EW B&H |
|---|---:|---:|
| Total | +100.3% | +277.3% |
| CAGR | 6.3% | 12.4% |
| Sharpe | 0.77 | 0.81 |
| **MDD** | **−15.3%** | −34.5% |

- **Absolute return HAR stock pe B&H se KAM** (RELIANCE +380% vs +537%, ICICI
  +20% vs +345%). 10 me se 8 pe Sharpe bhi behtar nahi.
- Sharpe sirf 2-3 trending names pe (RELIANCE 0.87 vs 0.74 — asli).
- **MDD har jagah ~2x chhota = combo ka SIRF consistent fayda.** Gate
  "suraksha" deta hai, "alpha" nahi. Combo B&H ko 2/12 saal hi harata hai.

### B5. Gate variants — 6-mo momentum + regime gate (5 Sep)

| Variant | Total | CAGR | Sharpe | Daily MDD |
|---|---:|---:|---:|---:|
| BASELINE (no gate) | +978% | 27.5% | 1.30 | −40.6% |
| Prev-mo BEAR/AVOID → CASH | +321% | 15.8% | 0.93 | −40.6% ❌ |
| Prev-mo BEAR/CHOP-DOWN → CASH | +167% | 10.6% | 0.81 | −22.1% |
| NIFTY < SMA200 → CASH | +543% | 21.0% | 1.21 | **−20.0%** |
| **NIFTY < SMA200 → 50%** | +746% | 24.4% | 1.31 | **−27.4%** |

- **Suggestion ("CAGR 32-34%, Sh 1.45, MDD −24%") confirm NAHI hui** — best
  realistic 24-27% / 1.31.
- **Prev-month BEAR gate FAIL** — lagged hai (Feb-20 crash se pehle Jan-20
  CHOP-DOWN tha, gate khula tha). Monthly regime gate crash nahi pakadta.
- **SMA200-50% = best balance:** Sharpe baseline jaisa, MDD −27%, return −746%.
- Sabse bada DD −40.6% = COVID 2020-02-06 → 2020-11-11; Feb-20 akela −25%
  (koi stop nahi, design choice — DD control gate se aata hai).

---

## C) NAYI STRATEGY — `6M-MOM-21-SMA50` (rules 5 Sep ko LOCKED)

Yehi wo system hai jo forward paper pe jayega. **Pehli rebalance: 30 Sep 2026.**

### Rules

| Rule | Detail |
|---|---|
| Universe | 90-name WATCH (archive-available names) |
| Rebalance | Har month-end close pe, monthly |
| Signal | 6-mo momentum: close / close(6mo pehle) − 1 |
| Selection | Rank → **top-25% (≈21 names)**, equal weight |
| Gate | Rebalance day pe **NIFTY close < SMA200 → exposure 50%**, warna 100% |
| Hold | 1 month (agle month-end tak), **koi intra-month exit nahi, koi stop nahi** |
| Cost | 0.1% rt churn (0.05% entry + 0.05% exit) — gross AND net dono report |

### Paper protocol

- Har month-end: `state/multistock/momentum_paper_log.csv` me row — date,
  names, NIFTY vs SMA200, exposure, entry prices. Agle month-end: exit, month
  return, cumulative equity.
- Monthly review: edge/cost + rolling Sharpe + MDD vs baseline (bina-gate wala
  paper bhi parallel — comparison ke liye).
- **Fail conditions (paper rukega):** 6 consecutive red months · monthly MDD
  > 12% · annualized rolling Sharpe < 0.5 for 6 months.

### In-sample reference (claim nahi)

- Baseline: CAGR 27.5%, Sharpe 1.30, MDD −40.6%
- **SMA50: CAGR 24.4%, Sharpe 1.31, MDD −27.4%** (2026 Q1 +2.8%)
- SMA-CASH: CAGR 21.0%, Sharpe 1.21, MDD −20.0%

### Gate (paper se hi claim)

edge/cost **≥ 1.3x** ya rolling Sharpe **≥ 0.9** (12-mo) tabhi "kaam karta hai".

---

## D) ENGINE PAR ASAR — kya kya badla / kya decide hua

| Sawaal | Jawab |
|---|---|
| 1h Sharpe 1.04 artefact hai? | **Nahi** — edge 30m–1h zone ka hai. 1h engine chalta rahega |
| Entry-hour 9-10 filter? | **REJECT** — har timeframe pe Sharpe giraata hai, post-hoc tha |
| Shorts? | **Bekaar** — longs har bucket positive, shorts BULL-LEAN/CHOP me nuksan |
| Wed/Thu? | Wed sabse kharab (NIFTY + basket dono pe) — `no_wed_thu` khada |
| Sizing? | B+sized 11/11 saal green par gaddha gehra (−37.6%) — cushion zaroori |
| Stocks pe daily stage-chase? | **Bekaar** — edge ~zero pre-cost; asli candidate = 6-mo momentum rank filter |
| Naya paisa? | **ZERO** — backtest → paper → deploy order kabhi mat todo |

---

## E) HONEST GATES (kabhi mat toda)

1. Real capital **ZERO** · koi return/loss-control promise nahi.
2. Backtest → paper → deploy order kabhi mat todo.
3. Har faisla **pehle likho, phir test karo** (post-hoc wale 4 NIFTY resets ka
   lesson).
4. Live engine = backtest config.
5. In-sample numbers sirf reference hain — forward paper hi asli proof.

---

## F) FILE MAP (kahan kya hai)

| File | Kya hai |
|---|---|
| `docs/NEW_STRATEGY.md` | Ye doc — sab ka record |
| `strategy_docs.html` | Live HTML version (Vercel) |
| `docs/MOMENTUM_FORWARD_PAPER_PRE.md` | 6M-MOM-21-SMA50 ke pre-registered rules |
| `state/multistock/NIFTY_VERIFY_FINDINGS.md` | A1/A2/A3 ka detail |
| `state/multistock/TIMEFRAME_SCAN_FINDINGS.md` | A4 ka detail |
| `state/multistock/MOMENTUM_HORIZON_FINDINGS.md` | B1 ka detail |
| `state/multistock/RANK_TEST_FINDINGS.md` | B2 ka detail |
| `state/multistock/STOCKS_TEST_FINDINGS.md` | B3 ka detail |
| `state/multistock/STOCKS_COMBO_FINDINGS.md` | B4 ka detail |
| `state/multistock/GATE_VARIANTS_FINDINGS.md` | B5 ka detail |
| `state/multistock/momentum_paper.py` | Forward paper runner (30 Sep se) |

*Update karna jab bhi naya test/result aaye — purani entries mitana nahi,
nayi add karna.*