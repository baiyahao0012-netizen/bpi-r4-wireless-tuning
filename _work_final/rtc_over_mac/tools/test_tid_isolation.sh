#!/bin/bash
# Runs on Pi. Decisive A/B: AI on same TID as bulk (prio 0) vs separate TID (prio 3).
# No TC at all; bulk offered 120 Mbps (link capacity ~66 Mbps -> saturated).
A="ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new root@192.168.240.1"
AP_MAC=36:19:86:e0:2e:0f
PI_MAC=90:de:80:1c:6a:7a
$A 'tc qdisc del dev phy0.1-ap0 root 2>/dev/null; echo no_tc'

run_arm() {
  local tag="$1" prio="$2"
  local b0=$(cat /sys/class/net/wlan1/statistics/rx_bytes)
  ( sleep 5; $A 'cat /sys/kernel/debug/ieee80211/phy0/aql_pending 2>/dev/null' > /tmp/aql2_$tag.txt ) &
  $A "cd /tmp && (./l2_ai_ap_tx phy0.1-ap0 $PI_MAC 1200 120 14 $prio >/tmp/ap_tx.log 2>&1 &)"
  sleep 1
  echo 12345678 | sudo -S python3 /tmp/l2_ai_client.py --dst-mac $AP_MAC \
    --seconds 8 --msg-base $((5500000 + RANDOM)) --out /tmp/tid_$tag.json 2>/dev/null >/dev/null
  local cli=$(cat /tmp/tid_$tag.json)
  sleep 5
  local b1=$(cat /sys/class/net/wlan1/statistics/rx_bytes)
  echo "ARM $tag (ai_prio=$prio)"
  echo "  client: $cli"
  echo "  link_mbps: $(( (b1 - b0) * 8 / 14 / 1000000 ))"
  echo "  aql: $(cat /tmp/aql2_$tag.txt 2>/dev/null | tr '\n' ' ')"
}

run_arm same_tid0 0
run_arm diff_tid3 3
run_arm diff_tid5 5
echo TID_AB_DONE
