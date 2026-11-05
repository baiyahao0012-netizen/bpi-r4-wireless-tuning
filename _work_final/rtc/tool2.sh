#!/bin/sh
for t in iperf3 iperf udhcpc; do
  p=$(command -v $t 2>/dev/null)
  if [ -n "$p" ]; then echo "$t -> $p"; else echo "$t -> none"; fi
done
