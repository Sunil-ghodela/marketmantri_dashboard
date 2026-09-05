# 6-mo momentum + regime gate variants — WHERE losses + kaunsa gate chalega (5 Sep 2026)

**Sawaal:** 30-40% DD kab hota hai? Prev-month NIFTY BULL-LEAN gate lagane se kya
badalta hai? (User ki suggestion thi: "6M-MOM-21 + BULL-LEAN-GATE → CAGR 32-34%,
Sharpe 1.45, MDD -24%, green 11/11" — expectation test karna tha, confirm nahi.)

## 1. Loss 30-40% KAB hota hai (baseline 6M-MOM-21, daily path)

**Sabse bada DD -40.6%: 2020-02-06 → 2020-11-11 = COVID crash.** Ek mahina hi sab
kuch: **Feb 2020 = -25%** (basket ka worst month). Baaki drawdown episodes:
- -17.6% · 2021-10 → 2022-08 (rate-hike bear)
- -15.9% · 2024-09 → 2025-06
- -14.9% · 2026-02 → 2026-04

Big loss months: 2020-02 **-25%** · 2026-02 **-13.4%** · 2024-09 -9.0% · 2020-01
-8.9% · 2019-06 -8.0% · 2018-08 -7.8% · 2022-04 -7.4% · 2016-11 -7.3% ·
2022-12 -6.2% · 2025-01 -5.3%.

**Kyun:** strategy mein koi stop loss nahi — mahine bhar top-21 pakdo, chahe
market gire. Feb 2020 mein top momentum names hi market ke saath gire.

## 2. Gate variants ka ASLI result (0.1% rt, daily path, 2016-02 → 2026-04)

| Variant | Total | CAGR | Sharpe | Daily MDD | Green yr |
|---|---|---|---|---|---|
| BASELINE (no gate) | +978% | 27.5% | 1.30 | -40.6% | 10/11 |
| **Prev-mo BEAR/AVOID → CASH** | +321% | 15.8% | 0.93 | **-40.6%** | 10/11 |
| Prev-mo BEAR/AVOID → 50% | +583% | 21.7% | 1.17 | -40.6% | 11/11 |
| Prev-mo BEAR/CHOP-DOWN → CASH | +167% | 10.6% | 0.81 | -22.1% | 8/11 |
| **NIFTY < SMA200 → CASH** (monthly) | +543% | 21.0% | 1.21 | **-20.0%** | — |
| **NIFTY < SMA200 → 50%** | +746% | 24.4% | 1.31 | **-27.4%** | — |

## 3. Honest conclusions (suggestion se alag)

1. **Suggestion ke expected numbers data se NAHI aate.** CAGR 32-34% nahi mila —
   best realistic 24-27%. Sharpe 1.45 nahi — 1.31 max. MDD -24% wala bhi sirf
   aggressive gate se, wo CAGR 21% pe gir jaata hai.
2. **Prev-month BEAR gate FAIL:** CAGR 27.5% → 15.8% (returns aadhe) aur MDD
   -40.6% pe hi rehta hai! Kyon: **scenario gate lagged hai** — Feb 2020 crash
   se pehle Jan 2020 ki scenario CHOP-DOWN thi (BEAR nahi), isliye gate khula
   tha aur crash poora laga. Monthly-regime gate crash ko pakad nahi pata.
3. **SMA200 gate behtar hai:** NIFTY jab rebalance din pe SMA200 se neeche →
   cash/half. Full cash: MDD -20% (aadha!) par CAGR 21%. 50%: Sharpe 1.31 =
   baseline ke barabar, MDD -27%, return -746%. **Best balance = SMA200-50%.**
4. **2026 note:** archive data 2026-04-09 tak hai — 2026 ka pura saal nahi,
   sirf Q1. Baseline 2026 (Q1) ≈ -2% (daily path). "2026 -5%" wala number is
   data mein pura nahi dikhta; Feb 2026 -13.4% wala month BEAR gate bhi nahi
   bacha paata (wo month ke ANDAR hua, rebalance month-end pe tha).
5. **Sab in-sample hai.** Ye variants test karke "ye best hai" bolna overfit
   trap hai — asli faisla forward paper (1-2 saal, edge/cost ≥1.3x) karega.

## 4. Aage ka test (next natural steps)
- [ ] SMA200-50% gate ka **year-wise** table + trade/month cadence
- [ ] Drawdown control ke aur variants: (a) portfolio-level hard stop (e.g. -8%
      month-to-date → cash), (b) NIFTY 1H MACD cross se entry timing (suggestion
      ka TRIGGER part), (c) ADANI-cluster max-1 cap
- [ ] Sabse acha 1-2 variants → forward paper pre-registration (rules pehle
      likh ke, phir paper)

Files: /tmp/gate_variants.py + /tmp/gate_details.py (exploratory, in-sample)
