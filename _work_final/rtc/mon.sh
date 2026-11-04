#!/bin/sh
OUT=/tmp/mon.txt
: > $OUT
i=0
while [ $i -lt 24 ]; do
  i=$((i+1))
  PS=$(cat /sys/kernel/debug/ieee80211/phy0/total_ps_buffered 2>/dev/null)
  D=$(iw dev phy0.1-ap0 station dump | sed -n '/Station c0:35/,/^Station/p')
  TX=$(echo "$D" | awk '/tx packets/{print $3; exit}')
  RX=$(echo "$D" | awk '/rx packets/{print $3; exit}')
  TF=$(echo "$D" | awk '/tx failed/{print $3; exit}')
  echo "$i ps_buf=$PS tx=$TX rx=$RX txf=$TF" >> $OUT
  sleep 1
done
echo DONE >> $OUT
