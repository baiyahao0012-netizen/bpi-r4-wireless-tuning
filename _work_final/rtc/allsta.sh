#!/bin/sh
for i in $(iw dev | awk '/Interface/{print $2}'); do
  n=$(iw dev $i station dump 2>/dev/null | grep -c "^Station")
  echo "$i : $n station(s)"
done
