#!/bin/sh
N=0
for p in $(ps | awk '/mac_agent/ && !/awk/ {print $1}'); do
  kill -9 $p 2>/dev/null && N=$((N+1))
done
sleep 1
LEFT=$(ps | awk '/mac_agent/ && !/awk/' | wc -l)
echo "killed=$N left=$LEFT"
