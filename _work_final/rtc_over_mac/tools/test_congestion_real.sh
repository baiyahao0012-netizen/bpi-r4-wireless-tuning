#!/bin/bash
# Runs on Pi. Real congestion: iperf3 UDP bulk 300M (link ~215M) + C AI responder.
A="ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new root@192.168.240.1"
AP_MAC=36:19:86:e0:2e:0f
PI_MAC=90:de:80:1c:6a:7a
$A 'tc qdisc del dev phy0.1-ap0 root 2>/dev/null; echo no_tc'
pkill -f "iperf3 -s" 2>/dev/null; sleep 1
iperf3 -s -B 192.168.240.126 -p 5201 -D
sleep 1

run_arm() {
  local tag="$1" prio="$2" rate="$3"
  ( sleep 5; $A 'cat /sys/kernel/debug/ieee80211/phy0/aql_pending 2>/dev/null' > /tmp/aql3_$tag.txt ) &
  $A "cd /tmp && (./l2_ai_ap_tx phy0.1-ap0 $PI_MAC 1200 0 14 $prio >/tmp/ap_ai.log 2>&1 &)"
  sleep 1
  $A "cd /tmp && (iperf3 -c 192.168.240.126 -u -b ${rate}M -t 12 -p 5201 >/tmp/ap_iperf.log 2>&1 &)"
  sleep 1
  echo 12345678 | sudo -S python3 /tmp/l2_ai_client.py --dst-mac $AP_MAC \
    --seconds 8 --msg-base $((6500000 + RANDOM)) --out /tmp/cong_$tag.json 2>/dev/null >/dev/null
  local cli=$(cat /tmp/cong_$tag.json)
  sleep 6
  echo "ARM $tag (ai_prio=$prio, bulk=${rate}M offered)"
  echo "  client: $cli"
  echo "  iperf: $($A 'grep -E "receiver" /tmp/ap_iperf.log | tail -n 1')"
  echo "  aql: $(cat /tmp/aql3_$tag.txt 2>/dev/null | tr '\n' ' ')"
}

run_arm tid0_300 0 300
run_arm tid3_300 3 300
run_arm tid0_150 0 150
pkill -f "iperf3 -s" 2>/dev/null
echo CONG_TEST_DONE
