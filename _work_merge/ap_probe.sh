#!/bin/bash
B=192.168.240.1
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=6 root@$B '
  echo "=== AP 接口 ==="
  iw dev | grep -E "Interface|type|ssid|channel" | head -12
  echo "=== AP 上有无已连 STA ==="
  iw dev phy0.0-ap0 station dump 2>/dev/null | head -20
  echo "(空则说明当前无客户端)"
  echo "=== AP 口是否在 br-lan ==="
  brctl show 2>/dev/null | head -6
  echo "=== 能否按 ethertype 分类 (nft) ==="
  nft describe ether_type 2>/dev/null | head -4
  echo "=== 每 STA 上行统计可用字段 ==="
  ls /sys/kernel/debug/ieee80211/phy0/netdev:phy0.0-ap0/stations/ 2>/dev/null | head -3
' 2>&1 | grep -v "WARNING\|post-quantum\|store now\|upgraded\|openssh.com"
echo AP_DONE
