#!/bin/sh
# Detect active phone Doubao traffic (mark=1900) and auto install/remove acceleration.
# Uses conntrack byte deltas, not just flow existence: idle ESTABLISHED/TIME_WAIT
# connections must not keep acceleration ON forever.
PHONE_IP="192.168.240.219"
APP_ID="1900"
IDLE_SEC=20
SLEEP=2

log() { logger -t oaf-auto "$*"; echo "$(date '+%F %T') $*"; }

ai_flows() {
  grep "$PHONE_IP" /proc/net/nf_conntrack 2>/dev/null | grep -c "mark=$APP_ID"
}

ai_bytes() {
  grep "$PHONE_IP" /proc/net/nf_conntrack 2>/dev/null | grep "mark=$APP_ID" | \
    awk '{for(i=1;i<=NF;i++) if($i ~ /^bytes=/) {split($i,a,"="); s+=a[2]}} END{print s+0}'
}

installed=0
last_bytes=0
last_active=$(date +%s)
log "start phone=$PHONE_IP app=$APP_ID idle=$IDLE_SEC"

while true; do
  b=$(ai_bytes)
  n=$(ai_flows)
  now=$(date +%s)
  if [ "$b" -gt "$last_bytes" ]; then
    last_active=$now
    if [ "$installed" = "0" ]; then
      /root/oaf_accel.sh install "$APP_ID" ef >/dev/null 2>&1
      installed=1
      log "AI bytes=$b flows=$n -> accel ON"
    fi
  fi
  if [ "$installed" = "1" ] && [ $((now - last_active)) -ge "$IDLE_SEC" ]; then
    /root/oaf_accel.sh remove >/dev/null 2>&1
    installed=0
    log "AI idle $IDLE_SEC s (bytes=$b flows=$n) -> accel OFF"
  fi
  last_bytes=$b
  sleep "$SLEEP"
done
