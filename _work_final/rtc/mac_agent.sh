#!/bin/sh
D=/sys/kernel/debug/ieee80211/phy0
IF=phy0.1-ap0
S=$D/netdev:phy0.1-ap0/stations/40:a5:ef:26:e3:47
DST=$1
PORT=$2
while true; do
  TOT=$(awk '$1=="total"{print $2}' $D/aql_pending 2>/dev/null | head -1)
  BE=$(awk '$1=="BE"{print $2}' $D/aql_pending 2>/dev/null | head -1)
  TX=$(awk '$1=="TX:"{print $2}' "$S/airtime" 2>/dev/null | head -1)
  ST=$(iw dev $IF station dump 2>/dev/null)
  R=$(echo "$ST" | awk '/tx retries/{print $3; exit}')
  F=$(echo "$ST" | awk '/tx failed/{print $3; exit}')
  [ -z "$TOT" ] && TOT=0
  [ -z "$BE" ] && BE=0
  [ -z "$TX" ] && TX=0
  [ -z "$R" ] && R=0
  [ -z "$F" ] && F=0
  echo "MACR,$TOT,$BE,$TX,$R,$F" | nc $DST $PORT 2>/dev/null
  sleep 0.1
done
