#!/bin/bash
# Runs on Pi. AP TC matrix: off / prio-only / prio+quota20 / prio+quota10.
A="ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new root@192.168.240.1"
AP_MAC=36:19:86:e0:2e:0f
PI_MAC=90:de:80:1c:6a:7a

setup_off() { $A 'tc qdisc del dev phy0.1-ap0 root 2>/dev/null; echo tc_off'; }
setup_prio() {  # same rate both classes, AI higher prio
  $A 'tc qdisc del dev phy0.1-ap0 root 2>/dev/null
tc qdisc add dev phy0.1-ap0 root handle 1: htb default 20
tc class add dev phy0.1-ap0 parent 1: classid 1:10 htb rate 20mbit ceil 20mbit prio 0 2>/dev/null
tc class add dev phy0.1-ap0 parent 1: classid 1:20 htb rate 20mbit ceil 20mbit prio 1 2>/dev/null
tc filter add dev phy0.1-ap0 parent 1: protocol all basic match "meta(priority eq 0)" flowid 1:10 2>/dev/null
echo tc_prio'
}
setup_pq() {  # AI unlimited prio0, bulk limited to $1
  $A "tc qdisc del dev phy0.1-ap0 root 2>/dev/null
tc qdisc add dev phy0.1-ap0 root handle 1: htb default 20
tc class add dev phy0.1-ap0 parent 1: classid 1:10 htb rate 200mbit ceil 200mbit prio 0 2>/dev/null
tc class add dev phy0.1-ap0 parent 1: classid 1:20 htb rate ${1}mbit ceil ${1}mbit prio 1 2>/dev/null
tc filter add dev phy0.1-ap0 parent 1: protocol all basic match \"meta(priority eq 0)\" flowid 1:10 2>/dev/null
echo tc_pq_${1}"
}

run_arm() {
  local tag="$1"
  $A "cd /tmp && (./l2_ai_ap_tx phy0.1-ap0 $PI_MAC 1200 40 14 >/tmp/ap_tx.log 2>&1 &)"
  sleep 1
  echo 12345678 | sudo -S python3 /tmp/l2_ai_client.py --dst-mac $AP_MAC \
    --seconds 8 --msg-base $((3500000 + RANDOM * 10)) --out /tmp/arm_$tag.json 2>/dev/null >/dev/null
  local cli=$(cat /tmp/arm_$tag.json)
  sleep 5
  local snd=$($A 'tail -n 1 /tmp/ap_tx.log')
  local cls=$($A 'tc -s class show dev phy0.1-ap0 2>/dev/null | grep -A1 "class htb 1:20" | grep Sent')
  echo "ARM $tag"
  echo "  client: $cli"
  echo "  sender: $snd"
  echo "  bulk_class: $cls"
}

setup_off;    run_arm off
setup_prio;   run_arm prio
setup_pq 20;  run_arm pq20
setup_pq 10;  run_arm pq10
$A 'tc qdisc del dev phy0.1-ap0 root 2>/dev/null; echo cleaned'
echo AP_TC_MATRIX_DONE
