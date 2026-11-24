#!/bin/bash
# Runs on Pi. Two-STA: bulk downlink to wlan0 (.150), AI downlink to wlan1 (.126).
# Tests per-STA AQL on the AP (bulk STA lowered vs default) and airtime weight.
A="ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new root@192.168.240.1"
AP_MAC=36:19:86:e0:2e:0f
AI_MAC=90:de:80:1c:6a:7a
BULK_IP=192.168.240.150
BULK_MAC=88:a2:9e:7e:c0:3b
$A 'tc qdisc del dev phy0.1-ap0 root 2>/dev/null; echo no_tc'
pkill -f "iperf3 -s" 2>/dev/null; sleep 1
iperf3 -s -B 192.168.240.150 -p 5202 -D
sleep 1
echo "=== AP stations ==="
$A 'iw dev phy0.1-ap0 station dump | grep "^Station"'

run_arm() {
  local tag="$1" aql="$2" weight="$3"
  # apply per-STA knobs for the bulk STA
  if [ -n "$aql" ]; then
    $A "echo 'limit 2 $aql' > /sys/kernel/debug/ieee80211/phy0/netdev:phy0.1-ap0/stations/$BULK_MAC/aql 2>/dev/null"
  else
    $A "echo 'limit 2 5000 12000' > /sys/kernel/debug/ieee80211/phy0/netdev:phy0.1-ap0/stations/$BULK_MAC/aql 2>/dev/null"
  fi
  if [ -n "$weight" ]; then
    $A "iw dev phy0.1-ap0 station set $BULK_MAC airtime_weight $weight 2>/dev/null"
  fi
  ( sleep 5; $A 'cat /sys/kernel/debug/ieee80211/phy0/aql_pending 2>/dev/null' > /tmp/aql4_$tag.txt ) &
  $A "cd /tmp && (./l2_ai_ap_tx phy0.1-ap0 $AI_MAC 1200 0 14 0 >/tmp/ap_ai.log 2>&1 &)"
  sleep 1
  $A "cd /tmp && (iperf3 -c $BULK_IP -u -b 300M -t 12 -p 5202 >/tmp/ap_iperf2.log 2>&1 &)"
  sleep 1
  echo 12345678 | sudo -S python3 /tmp/l2_ai_client.py --dst-mac $AP_MAC \
    --seconds 8 --msg-base $((7500000 + RANDOM)) --out /tmp/two_$tag.json 2>/dev/null >/dev/null
  local cli=$(cat /tmp/two_$tag.json)
  sleep 6
  echo "ARM $tag (bulk_aql='$aql' weight='$weight')"
  echo "  client: $cli"
  echo "  iperf: $($A 'grep -E "receiver" /tmp/ap_iperf2.log | tail -n 1')"
  echo "  aql: $(cat /tmp/aql4_$tag.txt 2>/dev/null | tr '\n' ' ')"
  $A 'cat /sys/kernel/debug/ieee80211/phy0/netdev:phy0.1-ap0/stations/'"$BULK_MAC"'/aql 2>/dev/null | grep -E "Q depth|Q limit" | head -n 2'
}

run_arm base "" ""
run_arm aql_low "2000 6000" ""
run_arm weight_low "" 128
pkill -f "iperf3 -s" 2>/dev/null
$A "echo 'limit 2 5000 12000' > /sys/kernel/debug/ieee80211/phy0/netdev:phy0.1-ap0/stations/$BULK_MAC/aql 2>/dev/null; iw dev phy0.1-ap0 station set $BULK_MAC airtime_weight 256 2>/dev/null; echo restored"
echo TWO_STA_DONE
