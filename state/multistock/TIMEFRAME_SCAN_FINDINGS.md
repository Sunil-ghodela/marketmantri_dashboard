# NIFTY TIMEFRAME SCAN — 15m/30m/1h/2h/4h x gates x entry-hour (6 Sep 2026)

> Script: `state/multistock/nifty_timeframe_scan.py` · Data: `state/nifty_15m_full.feather`
> (62,437 15m bars, 2016-07-25 → 2026-09-04) + `state/nifty_daily_state.csv`
> Engine = live B config ka exact replay, **sirf timeframe parametrized**: 1H
> MACD(12/26/5) completed-bar cross → resample(freq) pe, 2% stop (15m closes),
> **max-hold 18 wall-clock hours** (15m→72, 30m→36, 1h→18, 2h→9, 4h→4 bars),
> 0.06% rt cost, no divergence. Books = wahi flat / B+sized / filter(cl≥2).
> Sawaal: Sharpe 1.04 (1h long-only+BEAR/AVOID-skip) dusre timeframes pe tikta hai?

## Sanity ✅ — 1h verify se match
no-gate +159.93 (DD 37.59, Sh 0.85) · long-only+skip +81.16 (DD 18.28, Sh 1.04) —
`NIFTY_VERIFY_FINDINGS.md` se digit-to-digit same. Engine sahi hai.

## 1. Key question — long-only + BEAR/AVOID-skip, sized book

| tf | n | net% | maxDD% | Sharpe(m) | WR% |
|---|---:|---:|---:|---:|---:|
| 15m | 1511 | **−32.80** | 55.21 | **−0.26** ❌ | 35.3 |
| **30m** | 765 | **+93.52** | **13.52** | **0.87** | 38.7 |
| **1h** | 389 | +81.16 | 18.28 | **1.04** | 40.1 |
| 2h | 210 | +41.20 | 17.92 | 0.65 | 46.7 |
| 4h | 92 | +3.54 | 10.45 | **0.11** ❌ | 48.9 |

**Jawab: 1.04 sirf 1h pe hai, par edge "30m–1h zone" ka hai — 15m aur 4h pe mar
jaata hai.**
- **30m bhi zinda:** Sharpe 0.87, net +93.5% (1h se ZYADA), maxDD 13.5 (1h ke
  18.3 se KAM). Monthly-Sharpe 1h pe thoda behtar dikhta hai par return+DD
  30m pe behtar — dono ek hi zone ke do chehre hain.
- **15m poison:** −0.26 Sharpe, net negative. Itna chhota bar = whipsaw +
  fees, edge nahi bachta. 10yr flat no-gate pe bhi −243% (sabse kharab).
- **4h ~dead:** Sharpe 0.11, sirf 92 trades/10 saal — signal hi kam milta.
- Pattern no-gate flip pe bhi same: 1h 0.85 / 2h 0.70 behtar, 15m −0.95 sabse
  kharab, 4h 0.47 kamzor. **1h–2h = momentum engine ki natural frequency.**

## 2. Entry-hour 9-10 filter — post-hoc bucket tradeable NAHI bana

| tf | Sharpe w/o filter | Sharpe + entry-9-10 | n |
|---|---:|---:|---:|
| 15m | −0.26 | −0.46 | 468 |
| 30m | 0.87 | **−0.14** | 353 |
| 1h | 1.04 | **0.69** | 171 |
| 2h | 0.65 | 0.17 | 132 |
| 4h | 0.11 | 0.38 | 40 |

**Har timeframe pe filter ne Sharpe GIRAYA (4h chhota sample, ignore).** Entry
lab ka "hour 9-10 best" bucket post-hoc selection tha — jaise hi usse rule
banaya, wo kaat-ta hai kyunki sahi trades bhi 11/12/1/2 pe aati hain. 1h
1.04 → 0.69. **Ship mat karo.** (Weekday no_wed_thu ke opposite — wo 10yr
replay pe zinda nikla tha, ye hour filter nahi.)

## 3. No-gate (flip) baseline — sized book

| tf | n | net% | maxDD% | Sharpe | WR% |
|---|---:|---:|---:|---:|---:|
| 15m | 5648 | −243.84 | 265.69 | **−0.95** ❌ | 32.8 |
| 30m | 2904 | +16.29 | 82.62 | 0.06 | 35.8 |
| **1h** | 1594 | +159.93 | 37.59 | **0.85** | 37.7 |
| 2h | 922 | +106.07 | 29.28 | 0.70 | 43.0 |
| 4h | 470 | +61.05 | 33.36 | 0.47 | 50.0 |

1h/2h solid, 30m flat, 4h weak, 15m kabhi nahi. **Long-only+skip gate ka fayda
har zinda timeframe pe consistent:** DD aadha (1h 37.6→18.3, 2h 29.3→17.9),
Sharpe upar (30m 0.06→0.87, 1h 0.85→1.04).

## Honest

Sab **in-sample**. 30m vs 1h ka Sharpe farak (0.87 vs 1.04) monthly-return
aggregation ka asar hai — 1h ko "unique best" bolna overfit hoga; sahi baat
ye hai ki **edge 30m–1h zone me hai, 15m/4h me nahi**. Ye bhi post-hoc
dekha hua hai — asli faisla forward paper karega. Koi deploy nahi hui.

## Aage ka step

1. Timeframe scan ka jawab: **1h pe hi paper chalega** (already locked —
   6M-MOM-21-SMA50 NIFTY gate wala momentum paper, 30 Sep se). NIFTY 1H engine
   ke liye naya paper pre-register karna ho toh 30m–1h dono parallel chala
   sakte hain — ye 1h artefact nahi, zone effect hai.
2. Entry-hour filter **reject** — STATE/LOG mein record, koi aage ka test nahi.

Files: nifty_timeframe_scan.py · nifty_timeframe_scan.json