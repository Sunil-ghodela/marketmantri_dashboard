# NIFTY LIVE-ENGINE VERIFY — books + entry-lab + state-gate combine (6 Sep 2026)

> Script: `state/multistock/nifty_verify_books.py` · Data: `state/nifty_15m_full.feather`
> (62,437 15m bars, 2016-07-25 → 2026-09-04) + `state/nifty_daily_state.csv`
> Engine = live B config ka exact replay: 1H MACD(12/26/**5**) completed-bar cross,
> no div, bidirectional flip, 2% stop (15m closes), 18-bar max-hold, 0.06% rt cost.
> Sawaal: (1) sizing vs no-sizing verify, (2) entry-hour/weekday lab, (3) daily-state
> strategy ke saath combine kitna milta hai.

## 1. Books verify — jo live paper engine dikhata hai (1x / B+sized / filter)

| Book | n | WR% | net% | avg/trade | maxDD | Sharpe(m) |
|---|---:|---:|---:|---:|---:|---:|
| flat 1x | 1594 | 37.7 | +46.02 | +0.0289 | 25.61 | 0.45 |
| **B+sized (W/L 2x/2.5x/3x)** | 1594 | 37.7 | **+159.93** | +0.1003 | 37.59 | **0.85** |
| filter(cl≥2) 1x | 1594 | 14.9* | +73.19 | +0.0459 | **13.71** | 0.96 |

*WR sirf "taken" trades pe 14.9% isliye kyunki filter haar-ke-baad wale trades leta
hai (sabse kam WR bucket) — par net positive, kyunki unka avg zyada hai.
Doc comparison (NIFTY-B-SIZED-CANDIDATE, 21 Jul tak data): flat +47.3 / sized +165.3.
Naye 22 Jul–4 Sep ke CHOP din jodne se sized ~5% kam hua. Verify ✅ consistent.

### Yearly (sized book; flat parens me)
2016 +4.74(-5.13) · 2017 +13.35(-0.70) · 2018 +16.84(+3.10) · 2019 +22.71(+9.98) ·
2020 +16.58(-1.42) · 2021 +19.96(+21.57) · 2022 +27.05(+17.86) · 2023 +0.16(-6.58) ·
2024 +26.62(-3.43) · 2025 +5.90(+11.23) · 2026 +6.02(-0.46) → **sized 11/11 saal green**

## 2. Entry-hour lab (10 saal, flat 1x) — morning behtar, 11 baje sabse kharab

| Entry hour | n | WR% | net% | avg% |
|---|---:|---:|---:|---:|
| 9 | 221 | 39.4 | +28.31 | **+0.1281** |
| 10 | 400 | 41.2 | +31.46 | **+0.0787** |
| 11 | 231 | 30.7 | −21.19 | **−0.0917** |
| 12 | 158 | 40.5 | +11.69 | +0.0740 |
| 13 | 191 | 34.6 | −4.42 | −0.0231 |
| 14 | 171 | 35.1 | −3.75 | −0.0219 |
| 15 | 218 | 39.4 | +1.97 | +0.0090 |

Matlab: subah (9–10) ke entries behtar, dopahar 11 ke sabse kharab — par ye post-hoc
bucket hai, tradeable signal nahi (entry hour entry pe pata hota hai → isliye aage
pre-registered test ke layak, direct ship nahi).

### Weekday lab (flat 1x)
Fri +48.90 (avg +0.158) · Thu +25.04 · Mon −6.55 · Tue −10.44 · Wed −12.52 (sabse kharab).
Direction basket ke `no_wed_thu` finding se consistent (Wed kharab), Fri NIFTY pe best.

## 3. Daily-state strategy ke saath combine (prev-day scenario gate, sized)

| Variant | n | net(sized)% | maxDD | Sharpe(m) | WR% |
|---|---:|---:|---:|---:|---:|
| no-gate (live, flip) | 1594 | +159.93 | 37.59 | 0.85 | 37.7 |
| gate: bull→long / bear→short | 685 | +76.54 | 30.83 | 0.52 | 38.4 |
| **gate: long sirf (BEAR/AVOID prev-day pe entry nahi)** | 389 | +81.16 | **18.28** | **1.04** | 40.1 |

### Prev-day scenario bucket — long vs short split (flat)
| dir | bucket | n | WR% | net% | avg% |
|---|---|---|---|---|---|
| long | BEAR/AVOID | 410 | 42.2 | +38.18 | +0.0931 |
| long | BULL-LEAN | 299 | 39.1 | +33.68 | +0.1126 |
| long | CHOP-MID | 88 | 43.2 | +10.34 | +0.1175 |
| short | BEAR/AVOID | 387 | 37.7 | −1.20 | −0.0031 |
| short | BULL-LEAN | 333 | 31.8 | −21.41 | −0.0643 |
| short | CHOP-MID | 77 | 27.3 | −13.57 | −0.1762 |

**Seedha matlab:**
1. **Longs har bucket me positive** (BEAR/AVOID ke baad bhi +0.09 avg) — index drift.
2. **Shorts sirf BEAR/AVOID me ~flat**, BULL-LEAN/CHOP me nuksan — shorts bekaar (NIFTY-B
   doc ka 1 Aug wala "shorts bekaar" finding ab full-data pe confirm).
3. State gate ka asli faida **sizing ke saath long-only + BEAR/AVOID-skip** me: return
   aadha par **maxDD aadha (−18% vs −38%) aur Sharpe 1.04** (sabse behtar risk-adjusted).
4. **State strategy ke saath combine = "long-only ban jao"** — ye momentum engine ko
   daily-scenario filter ke saath jodne ka sabse saaf jawab hai.

## ⚠️ Honest
Sab **in-sample** hai. Entry-hour/weekday/long-only ye sab post-hoc dekhe hue hain —
forward paper (jo pre-registered hai) hi decide karega. Koi nayi deploy nahi hui;
ye verify + direction-finding tha. `nifty_verify_books.json` raw numbers.
