#!/bin/sh
D=/sys/kernel/debug/ieee80211/phy0
S=$D/netdev:phy0.1-ap0/stations/40:a5:ef:26:e3:47
echo "i,aql_vo,aql_vi,aql_be,aql_bk,aql_tot,tx_us,rx_us,att,succ"
i=0
while [ $i -lt 260 ]; do
  A=$(awk '$1=="VO"||$1=="VI"||$1=="BE"||$1=="BK"||$1=="total"{printf "%s,", $2}' $D/aql_pending 2>/dev/null | head -1)
  TX=$(awk '$1=="TX:"{print $2}' "$S/airtime" 2>/dev/null | head -1)
  RX=$(awk '$1=="RX:"{print $2}' "$S/airtime" 2>/dev/null | head -1)
  ATT=$(awk '$2=="attempts:"{print $3}' $D/mt76/tx_stats 2>/dev/null | head -1)
  SUC=$(awk '$2=="success:"{print $3}' $D/mt76/tx_stats 2>/dev/null | head -1)
  echo "$i,$A$TX,$RX,$ATT,$SUC"
  i=$((i+1))
  sleep 0.1
done
