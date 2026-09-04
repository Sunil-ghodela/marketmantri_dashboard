#!/usr/bin/env bash
# Daily NIFTY state auto-update (canonical — local ya VPS dono pe chalega).
#
#   1. git pull --ff-only  -> repo ka latest code + data origin se le lo
#      (taaki naya code version bhi roz khud aa jaye, sirf data nahi)
#   2. state/update_prices.py -> Yahoo ^NSEI se naye din fetch karta hai,
#      nifty_prices.csv mein append karta hai aur sab rebuild karta hai
#      (CSVs + JSON + teeno maps + state cycle)
#   3. Agar data badla -> git commit + push -> Vercel auto redeploy
#
# Schedule (market close ke baad, Mon-Fri):
#   Europe/Berlin box -> roz 12:50 (16:20 IST):  50 12 * * 1-5 bash <repo>/state/cron_run.sh
#   India box         -> roz 16:20 IST:           20 16 * * 1-5 bash <repo>/state/cron_run.sh

set -e
cd "$(dirname "$0")/.."
LOG="state/update.log"

echo "===== $(date '+%Y-%m-%d %H:%M:%S %Z') =====" >> "$LOG"

# 1. latest code + data
git pull --ff-only --quiet >> "$LOG" 2>&1 \
  || echo "git pull: no remote changes / offline — aage badho" >> "$LOG"

# 2. fetch + rebuild
python3 state/update_prices.py >> "$LOG" 2>&1 || { echo "UPDATE FAILED" >> "$LOG"; exit 1; }

# 3. commit + push (sirf jab kuch badla ho)
if ! git diff --quiet -- state/; then
    git add state/
    git -c user.name="MM State Bot" -c user.email="state@marketmantri.local" \
        commit -m "state: daily NIFTY update $(date '+%Y-%m-%d')" >> "$LOG" 2>&1 || true
    git push >> "$LOG" 2>&1 || echo "PUSH FAILED (agla run dobara karega)" >> "$LOG"
    echo "updated + pushed" >> "$LOG"
else
    echo "no change (data already current)" >> "$LOG"
fi
