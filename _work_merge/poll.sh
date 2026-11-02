#!/bin/bash
for i in $(seq 1 30); do
  sleep 10
  if ping -c1 -W2 192.168.240.1 >/dev/null 2>&1; then
    if ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -o BatchMode=yes root@192.168.240.1 'echo UP' 2>/dev/null | grep -q UP; then
      echo "BOARD UP after $((i*10))s"
      ssh -o StrictHostKeyChecking=no root@192.168.240.1 'uname -r; cat /proc/uptime; dmesg | head -3; ls /sys/kernel/tracing/events/ 2>/dev/null | head' 2>/dev/null
      exit 0
    fi
  fi
  echo "poll $i: not up yet"
done
echo "BOARD DID NOT COME BACK"
