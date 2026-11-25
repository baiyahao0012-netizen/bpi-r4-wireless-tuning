#!/bin/bash
# Diagnose the dedup-test loss composition from the client event CSV.
f=/tmp/l2ai_dedup2.csv
[ -f "$f" ] || { echo NO_CSV; exit 0; }
echo "events:"; awk -F, 'NR>1{c[$2]++} END{for(k in c) printf "  %s=%d\n", k, c[k]}' "$f"
echo "--- msg 分析 ---"
awk -F, 'NR>1{
  mid=$3
  if($2=="tx_req") tx[mid]++
  if($2=="resend") rs[mid]++
  if($2=="ttft") ok[mid]++
}
END{
  lost=0; lost_resend=0; lost_noresend=0
  for(m in tx){ if(!(m in ok)){ lost++; if(rs[m]>0) lost_resend++; else lost_noresend++ } }
  printf "requests=%d delivered=%d lost=%d\n", length(tx), length(ok), lost
  printf "lost_with_resend(ACK丢失->dup路径)=%d\n", lost_resend
  printf "lost_without_resend(响应丢失且无请求重传)=%d\n", lost_noresend
}' "$f"
