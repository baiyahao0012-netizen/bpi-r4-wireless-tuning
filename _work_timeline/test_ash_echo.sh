#!/bin/sh
CAP=/sys/kernel/debug/ieee80211/phy0/mt76/agg_win_cap
echo "== what does echo write =="
echo 8 | od -c | head
printf '8' | od -c | head
printf '8\n' | od -c | head
echo "== try printf (no newline) =="
printf '8' > "$CAP" 2>&1
echo "rc=$?"
cat "$CAP" 2>&1
echo "== try manual write then immediate read =="
echo 0 > "$CAP" 2>&1
echo "rc0=$?"
cat "$CAP" 2>&1
