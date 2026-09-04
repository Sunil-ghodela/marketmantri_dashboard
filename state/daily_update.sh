#!/usr/bin/env bash
# Daily NIFTY state auto-update.
#
# Kya karta hai:
#   1. state/update_prices.py — Yahoo ^NSEI se naye din fetch karta hai,
#      nifty_prices.csv mein append karta hai aur sab kuch rebuild karta hai
#      (CSVs + JSON + dono maps).
#   2. Agar data badla hai -> git commit + push -> Vercel auto redeploy.
#
# Kaise schedule karein (roz 16:15 IST, market close ke baad):
#   crontab -e   mein ye line add karo:
#   15 16 * * 1-5  /bin/bash /home/vaibhav/AI/yr2026/Investment/marketmantri_dashboard/state/daily_update.sh >> /home/vaibhav/AI/yr2026/Investment/marketmantri_dashboard/state/update.log 2>&1
#
# Zaroorat: is script ko repo ke andar se hi chalana hai (git remote set hai).

set -e
cd "$(dirname "$0")/.."
LOG="state/update.log"

echo "===== $(date '+%Y-%m-%d %H:%M:%S %Z') =====" >> "$LOG"

# 1. Fetch + rebuild
python3 state/update_prices.py >> "$LOG" 2>&1 || { echo "UPDATE FAILED" >> "$LOG"; exit 1; }

# 2. Commit + push (sirf jab kuch badla ho)
if ! git diff --quiet -- state/; then
    git add state/
    git commit -m "state: daily NIFTY update $(date '+%Y-%m-%d')" >> "$LOG" 2>&1
    git push >> "$LOG" 2>&1 || { echo "PUSH FAILED" >> "$LOG"; exit 1; }
    echo "updated + pushed" >> "$LOG"
else
    echo "no change (data already current)" >> "$LOG"
fi
