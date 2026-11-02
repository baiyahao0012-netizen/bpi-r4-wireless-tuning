#!/bin/bash
echo "=== rebooting ==="
ssh -o StrictHostKeyChecking=no root@192.168.240.1 'sync; sleep 1; reboot' 2>/dev/null &
sleep 8
echo "=== polling for board ==="
for i in $(seq 1 40); do
  sleep 10
  if ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no root@192.168.240.1 'echo UP' 2>/dev/null | grep -q UP; then
    echo "BOARD UP after ~$((i*10+8))s"
    break
  fi
  echo "  wait $i"
done
