#!/usr/bin/env bash
# VPS daily NIFTY state auto-update: 12:45 server time (16:15 IST) Mon-Fri
cd /root/marketmantri_dashboard
LOG=/root/marketmantri_dashboard/state/update.log
echo "=== $(date '+%F %T %Z') ===" >> "$LOG"
python3 state/update_prices.py >> "$LOG" 2>&1 || { echo "UPDATE FAILED" >> "$LOG"; exit 1; }
if ! git -C /root/marketmantri_dashboard diff --quiet -- state/; then
  git -C /root/marketmantri_dashboard add state/
  git -C /root/marketmantri_dashboard -c user.name="MM State Bot" -c user.email="state@marketmantri.local" \
      commit -m "state: daily NIFTY update $(date +%F)" >> "$LOG" 2>&1
  git -C /root/marketmantri_dashboard push >> "$LOG" 2>&1 && echo "pushed $(date +%F)" >> "$LOG" || echo "PUSH FAILED" >> "$LOG"
else
  echo "no change" >> "$LOG"
fi
