#!/bin/sh
# MAC instrumentation agent: per-STA cumulative counters + total airtime + PHY rate.
# Sampling is 800 ms on purpose: iw station dump blocks for seconds when the
# medium is saturated, so a higher rate only queues up.
D=/sys/kernel/debug/ieee80211/phy0
IF=phy0.0-ap0
STA=40:a5:ef:26:e3:47
DST=$1
PORT=$2
while true; do
  DUMP=$(iw dev $IF station dump 2>/dev/null)
  V=$(echo "$DUMP" | awk -v s=$STA '
    /^Station /{cur=$2}
    cur==s && /tx packets/{p=$3}
    cur==s && /tx bytes/{b=$3}
    cur==s && /tx duration/{d=$3}
    cur==s && /tx retries/{r=$3}
    cur==s && /tx failed/{f=$3}
    cur==s && /tx bitrate/{br=$3}
    /tx duration/{t+=$3}
    END{printf "%d %d %d %d %d %d %d", p+0, b+0, d+0, r+0, f+0, t+0, br*10}')
  P=$(echo $V | cut -d' ' -f1)
  BY=$(echo $V | cut -d' ' -f2)
  DU=$(echo $V | cut -d' ' -f3)
  R=$(echo $V | cut -d' ' -f4)
  F=$(echo $V | cut -d' ' -f5)
  TD=$(echo $V | cut -d' ' -f6)
  BR=$(echo $V | cut -d' ' -f7)
  AQL=$(awk '$1=="total"{print $2}' $D/aql_pending 2>/dev/null | head -1)
  [ -z "$AQL" ] && AQL=0
  [ -z "$P" ] && P=0
  [ -z "$BY" ] && BY=0
  [ -z "$DU" ] && DU=0
  [ -z "$R" ] && R=0
  [ -z "$F" ] && F=0
  [ -z "$TD" ] && TD=0
  [ -z "$BR" ] && BR=0
  echo "MACR,$AQL,$P,$BY,$DU,$R,$F,$TD,$BR" | nc $DST $PORT 2>/dev/null
  usleep 800000 2>/dev/null || sleep 1
done
