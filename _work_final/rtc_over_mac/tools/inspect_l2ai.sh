#!/bin/bash
for f in /tmp/l2ai_*.csv; do
  [ -f "$f" ] || continue
  echo "== $f"
  awk -F, 'NR>1{c[$2]++} END{for(k in c) printf "%s=%d ", k, c[k]; print ""}' "$f"
  echo -n "   ai tx (flow0 tx): "
  awk -F, 'NR>1 && $2=="tx" && $3=="0"{n++} END{print n+0}' "$f"
done
