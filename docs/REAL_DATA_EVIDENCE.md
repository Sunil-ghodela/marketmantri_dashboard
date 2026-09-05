# REAL DATA PE KYA CHALTA HAI — evidence rebuild (Sep 2026)

> Ye doc tab bana jab data-integrity fix ke baad (2b15d12, 6 Sep) saare numbers
> REAL NIFTY (^NSEI) pe dobara nikale gaye. Purane numbers (xlsx `Close_Est`
> estimated series pe) INVALID the. Jo ab dikhe, wahi market mein hai.

## 0. Data integrity — kya hua tha

- Dashboard pehle 4,200-day xlsx ke `Close_Est` (estimated/reconstructed
  series) pe tha — real ^NSEI se daily-return correlation 0.03.
- Fix: `state/nifty_prices.csv` real ^NSEI OHLC (2,882 din, 2014→2026-09-04),
  pipeline rebuild → JSON/CSV/maps/xlsx sab real.
- NIFTY close (04 Sep 2026): **23,897.7** · YTD **-8.5%** · stage **CHOP-DOWN**.

## 1. Stage (scenario) real data pe — share + forward

10 buckets, warmup hatake (build_state.py + scenario.py se):

| Stage | % din | +20d avg | Win(20d) | Action |
|---|---|---|---|---|
| ALL-ALIGN BULL | ~6% | ~+4.5% | ~100% | BUY/HOLD |
| EARLY-UP | ~2% | ~+6.3% | ~100% | HOLD |
| STRONG-FLOW | ~1.5% | ~+2.6% | ~93% | BUY |
| CHOP-UP | ~28% | mild + | ~60-75% | WATCH |
| CHOP-MID | ~41% | ~0 | ~55% | STAND-ASIDE |
| CHOP-DOWN | ~16% | ~0 | ~50% | STAND-ASIDE |
| BEAR/WEAK/PANIC/TOP-WARN | ~1% each | neg se pos | mixed | NO-TOUCH/AVOID |

(Exact % Excel `Stage_Map` sheet + dashboard pe.) TREND UP regime = rare —
poori history mein sirf chhote runs (avg ~1-2 mahina). Chop 80%+ din hai.

## 2. RSI / param edge — REAL numbers

`state/rsi_analysis.png` + `Parameter_Edge_Analysis` sheet (xlsx):

- RSI < 30 (oversold): abhi tak data **falling-knife warning** deta tha —
  REAL data pe bhi koi automatic "buy the dip" edge NAHI (forward avg
  negative/neutral; knife).
- RSI 60-70 zone ke baad halka positive drift; RSI >70 ke baad koi reliable
  reversal edge nahi.
- MACD CROSS_UP/CROSS_DOWN akela (daily): ~0 edge chop mein — yahi August
  paper loss ka mechanism hai.
- ADX/Chop filters: extreme clean-trend (Chop<38 + ADX>25) days rare par
  positive; deep-chop days ~0.
- Sabse honest line: **koi bhi single parameter akela robust edge nahi deta.**
  Jo dikhta hai wo mild drift hai jo lambi hold mein accumulate hota hai.

## 3. Trend-days-long (user ka sawaal) — REAL answer

NIFTY long SIRF jab previous day stage = ALL-ALIGN BULL/EARLY-UP/STRONG-FLOW:

| | Trend-days long | Buy & Hold |
|---|---|---|
| Total | +29.7% | +187% |
| CAGR | 2.3% | 9.7% |
| Sharpe | 0.49 | 0.65 |
| MDD | -11% | -38% |
| Days in market | 546 (19%) | 2,878 |

→ Trend days pe long = **safe (MDD 3.5x kam) par paisa ~16%**. Sharpe bhi B&H
se kam. Market ka zyada paisa "lean" days mein hai, sirf full-trend mein nahi.

## 4. Combo test — 1H MACD cross + daily stage gate (NEW, real data)

`state/combo_test.py` — paper engine ka 1H MACD(12/26/5) cross (15m feather
2016-07→2026-07 se 1H bars), gate = PREVIOUS day ka scenario (koi look-ahead
nahi), entry next open, forward close-to-close:

| Gate (prev-day stage) | n | +1d | +5d | +10d | +20d | win5 |
|---|---|---|---|---|---|---|
| ALL CROSSES (baseline) | 512 | +0.09 | +0.29 | +0.45 | +0.89 | 58% |
| **BULL-LEAN** (CHOP-UP/ALL-ALIGN/EARLY/STRONG) | 190 | +0.19 | +0.39 | +0.57 | **+1.25** | **62%** |
| CHOP (MID/DOWN) | 167 | +0.04 | +0.25 | +0.32 | +0.54 | 50% |
| BEAR/AVOID (WEAK/PANIC/BEAR/TOP) | 155 | +0.01 | +0.21 | +0.45 | +0.84 | 62% |
| STRICT TREND-ONLY (ALL-ALIGN+EARLY+STRONG) | 115 | +0.12 | +0.26 | +0.56 | **+1.36** | 52% |

Context: same window NIFTY B&H ≈ +187% (11.4 yr, ~+0.7-0.8% per 20d avg).

**Kya mila (honest):**
1. Stage gate **direction sahi hai** — bull-lean cross ke baad +1.25%/+20d vs
   chop cross +0.54% (~2x better per trade), win 62% vs 50%. Chop ko cross
   lekar bleed karna (August paper) REAL data pe bhi sabse kamzor bucket hai.
2. Par **dramatic edge nahi** — bull-gate f20 (+1.25-1.36%) baseline all-cross
   (+0.89%) se ~0.4-0.5% behtar, B&H ke 20d drift (~0.75%) se thoda upar.
   Sharpe-style robust "3x" wala kuch nahi mila. Sabse consistent message:
   **edge lambi hold (10-20d) mein hai, chhoti churn mein nahi.**
3. Timing: late-hour (14-15 IST) crosses vs early — mixed, koi stable edge
   nahi; entry-hour wala magic number fake data ka tha.

## 5. Jo REAL tests mein consistently chala (teen alag tests)

1. **Cadence universe se aati hai, index se nahi** — single NIFTY pe quality
   entries ~0.5-1.5/saal; 10 stocks pe ~5.9/month. Basket wala point.
2. **Edge lambi hold mein hai** — 15-din time-hold wale trades positive right
   tail (stocks test: +4.72% avg hold-15 vs stage-flip exit -1.88%); momentum
   sirf 6-mo horizon + monthly hold pe index-level aaya.
3. **Daily stage gate 1H cross ko thoda behtar karta hai** (upar table) — par
   ye abhi in-sample description hai, forward paper test pending.

## 6. Isliye aage ka rasta (bina naye numbers invent kiye)

- [ ] **Forward paper gate** (3-6 mahina, edge/cost >=1.3x) — stage-gated 1H
      cross long-only, BULL-LEAN gate, 10-20d hold window, NIFTY pe. Yehi
      "REAL DATA PE kya chalta hai" ka proof banega.
- [ ] **Full-universe momentum scan** — 88 names (local 103-stock data),
      6-mo momentum + monthly top-25% + 1-mo hold (10-name test ka bada
      version). Edge bade universe + lambi momentum se aana chahiye.
- [ ] NIFTY daily paper (v2) ke liye: chop mein cross-band karne ka rule
      (stage gate) — lekin pehle forward paper, phir deploy.

## Files

- `state/combo_test.py` + `combo_test_results.csv` + `combo_signals.csv`
- `state/technical_parameters_full.xlsx` (10 sheets, real) +
  `state/rsi_analysis.png`
- `state/nifty_state_data.json` / `nifty_daily_state.csv` (real, 6 Sep rebuild)
