# NIFTY State Strategy (v1) — Stage Map se Decision Matrix tak

> Data: 3,047 din (2015–Sep 2026) · Daily State pipeline se har roz 16:20 IST auto-update.
> Har din ka state → `nifty_state_dashboard.html` → "Strategy" section:
> stage chip + action card + decision matrix + cycle map + cadence. Koi manual
> calculation nahi — dashboard khud bata deta hai aaj kya karna hai.

---

## 1. Har din 1 label: STAGE (10 buckets, mutually exclusive)

Priority se banta hai (PANIC sabse pehle): regime (ADX+DI) → RSI bands → structure (SMA50/200 + MACD). Ek din sirf ek stage.

| Stage | % din | +20d avg | Win | Action | Matlab (kya hai) |
|---|---|---|---|---|---|
| CHOP-MID | 41.2% | +0.72% | 64% | STAND-ASIDE | No-trend base — RSI ~45-60, MACD flat |
| CHOP-UP | 28.4% | +1.20% | 75% | WATCH | Chop ke andar recovery shuru (RSI 60+ ya RSI 52+ & MACD+) |
| CHOP-DOWN | 16.1% | -0.24% | 50% | STAND-ASIDE | Weak chop (RSI≤45 ya MACD ≤ -15) — neeche jhukta |
| ALL-ALIGN BULL | 5.8% | +4.51% | 100% | BUY / HOLD | TREND UP + RSI 55-71 + SMA200 upar — sab green |
| STRONG-FLOW | 1.5% | +2.61% | 93% | BUY | Trend ban raha (SMA200 upar, SMA50 up, ADX≥20, MACD+) |
| EARLY-UP | 1.8% | +6.31% | 100% | HOLD | TREND UP andar, momentum thanda (pullback) |
| TOP-WARNING | 1.3% | +0.30% | 61% | NO-NEW | RSI 72+ ya bearish divergence — trim/lock |
| WEAK | 1.2% | -8.55% | 6% | NO-BUY | RSI≤38 + SMA50 neeche — exit zone |
| PANIC | 1.6% | -8.39% | 18% | NO-TOUCH | Falling knife — RSI≤35 + TREND DOWN |
| BEAR | 1.1% | +5.12% | 94% | AVOID | TREND DOWN regime (mild) |

> In-sample numbers (NIFTY overall upar gaya isliye drift hai). Ye **context hai, proof nahi**.
> Asli edge proof = forward paper test (Section 6).

**Guardrails jo data ne sikhaaye (todna mana):**
1. ❌ RSI < 40 pe kabhi kharido — knife (-7.7%/+20d). PANIC/WEAK zone.
2. ❌ Chop mein MACD cross ya divergence chhappar — T3 no-edge (f10 -0.24%, win 43%).
3. ❌ TOP-WARNING pe naya long (RSI 72+ / bear div) — wahin se partial lock.
4. ✅ Strength follow karo — RSI 60-70 zone sabse kaam ka (2020 ke baad ka index yahi karta hai).

---

## 2. Entry plan (day entry) — Tiers

| Tier | Trigger (close par confirm) | Entry | 12-saal count | ~/saal | +20d avg | Verdict |
|---|---|---|---|---|---|---|
| T1 fresh-trend | Regime **TREND UP** bane (pehla din) | Next open | 6 | 0.5 | +4.92% | ✅ Core trade |
| T2 re-accel | EARLY-UP (pullback) ke baad **ALL-ALIGN/STRONG-FLOW** wapas | Next open | 11 | 0.9 | +2.71% | ✅ Add/hold |
| T3 chop-trigger | CHOP-UP + CROSS_UP / BULL_DIV | ❌ | 208 | 17.3 | +0.26% (win 59%) | ⛔ NO EDGE — trade NAHI |

**Verdict honest hai:** NIFTY index **daily** pe quality entries sirf **17 in 12 saal (~1.5/saal)**.
TREND UP regime poori history mein sirf **6 baar** bana (avg 36 din, sabse lamba 164 din).
Matlab single index + daily timeframe = **bahut kam, par lambi** trades.

### Entry rules (v1)
1. Entry sirf T1/T2 din — **close ke baad confirm**, trade **next open** (kal subah).
2. Time: 09:15-10:15 IST window hi entry order (10-2 PM wala issue yaad rakho — signal time, entry time alag).
3. Instrument: NIFTY options (CE/PE paper) — monthly expiry ~3-4 week bacha ho tabhi (time decay).
4. Size: **1x base**. 2x sirf jab stage = ALL-ALIGN BULL **aur** RSI 60-70 (sabse high-quality cell).
5. Consecutive same-tier din pe dobara entry nahi (run ka pehla din hi entry).

---

## 3. Exit plan (week plan) — flow profile se

Data bola: TREND UP din ke baad move **+1d +0.24 → +5d +1.21 → +10d +2.42 → +20d +4.91** — asli paisa week-2 se week-4 mein. Isliye hold-tolerance rakho, jaldi mat becho.

| Window | Rule |
|---|---|
| Week 1 (din 1-5) | **Hold.** Exit sirf: stop lage ya stage WEAK/BEAR/PANIC ho jaye |
| Week 2 (din 5-10) | +4% close → **50% book**; baaki ka stop breakeven pe trail |
| Week 3+ (din 10-15) | TOP-WARNING stage → baaki **lock**. Din 15 = **max hold, force exit** (agar zinda ho) |
| Har roz 16:20 | Dashboard ka **stage** check — CHOP-DOWN/WEAK 2 din lagatar = next open exit (chop bleed se bachao) |

- **Stop (initial):** entry − 2×ATR14 (~600 pts abhi). Entry ke baad +2×ATR profit → stop breakeven.
- **Trail:** close se 3×ATR14 neeche (profit lock, trend ko space deke).
- ATR14 abhi ~300 pts — 2×ATR ≈ 600 pts ≈ 2.5%. Ye Basket wale "fees khaye" wale lesson se bhi bada hai — **spread+fees calculate karke hi enter**.

---

## 4. Cadence — "month me 1-4 trades" ka sach

Quality entries (T1+T2) ka month distribution (12 saal):

| Mahine me trades | % months |
|---|---|
| 0 | 93.2% |
| 1 | 3.0% |
| 2 | 2.3% |
| 3 | 0.8% |
| 4+ | 0.8% |

**Matlab:** ~93% mahino mein quality entry **nahi aayegi**. Jab aayegi (trend months 2020-21, 2023-24 wale), us mahine 1-4 aa sakti hai + agle 2-4 hafte hold hota hai.

**"Har mahine 1-4 trade" single NIFTY index + daily timeframe pe impossible hai bina edge khoye.** Options:
1. **Isko maan lo** — 1-2 saal me 3-6 quality trend trades, har ek +5-15% ka target = realistic long-only.
2. T3 (chop triggers) mat lo — 17/saal aate hain par edge zero; yahi wali "activity" thi jo August paper ko -1.8% pe le gayi.
3. **Monthly cadence chahiye toh universe chahiye** (basket/stocks) — wahi MarketMantri Basket Restart plan ka point hai. Stage map wahan har stock pe lagake weekly signals mileinge.

---

## 5. Daily routine (5 min)

| Time | Kya |
|---|---|
| 16:20 IST | VPS cron auto: fetch → rebuild → push → dashboard update (kuch karna nahi) |
| Evening | Dashboard kholo → **Action card** dekho (stage + action) |
| Kal subah | Agar action = BUY (T1/T2 confirm hua) → open pe entry order. WATCH = sirf confirm. Baaki = no action |

Dashboard action card khud bolta hai: BUY / HOLD / WATCH / NO-NEW / STAND-ASIDE / NO-BUY / AVOID / NO-TOUCH. Koi indicator-pandit ki zaroorat nahi.

---

## 6. Forward test (proof gate — Basket restart jaisa)

1. Ye rules ek paper log mein 3-6 mahine chalao (aaj se).
2. Har T1/T2 entry: date, open entry, stop, exit (stage/stop/time), P&L.
3. **Edge/cost ≥ 1.3x** aur win ≥ 45% ho → next: existing NIFTY engine mein 10-2PM window + stage-gate integrate karo.
4. Real paisa tabhi jab forward paper edge dikhaye. In-sample numbers se koi bharosa nahi.

**Ek line:** Stage map se ab pata hai — 93% mahine rukna hi trade hai; jab stage BUY bole, tab poora dhyan, 2-4 hafte ka dhairya, aur week-3 se paisa book karna shuru.
