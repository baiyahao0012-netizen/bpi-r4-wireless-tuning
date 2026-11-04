#!/bin/bash
B=192.168.240.1
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=6 root@$B '
  echo "=== 桥端口 hairpin 模式（同 BSS 中继必需）==="
  for p in phy0.0-ap0 phy0.1-ap0 lan2 eth1; do
    v=$(cat /sys/class/net/$p/brport/hairpin_mode 2>/dev/null); echo "$p hairpin=$v";
  done
  echo "=== 桥端口隔离/转发延迟 ==="
  for p in phy0.0-ap0 phy0.1-ap0; do
    echo "$p isolate=$(cat /sys/class/net/$p/brport/isolated 2>/dev/null) fwd_delay=$(cat /sys/class/net/$p/brport/forward_delay 2>/dev/null)";
  done
  echo "=== bridge 命令可用性 ==="
  command -v bridge || echo no-bridge-cmd
  echo "=== 5G AP 是否独立于 br-lan ==="
  brctl show 2>/dev/null | grep -E "bridge|phy0"
' 2>&1 | grep -v "WARNING\|post-quantum\|store now\|upgraded\|openssh.com"
echo HP_DONE
