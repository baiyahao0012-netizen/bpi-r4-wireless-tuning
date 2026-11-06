#!/bin/sh
echo "=== interfaces ==="
iw dev | awk '/Interface/{print $2} /ssid/{print "  ssid", $2}'
echo "=== stations on 5G ==="
for i in $(iw dev | awk '/Interface/{print $2}'); do
  n=$(iw dev $i station dump 2>/dev/null | grep -c "^Station")
  if [ "$n" -gt 0 ]; then
    echo "--- $i ($n) ---"
    iw dev $i station dump | grep -E "^Station|signal:" | head -12
  fi
done
