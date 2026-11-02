cd /root/merge
echo "=== sha256 of all relevant modules ==="
sha256sum /mnt/d/Desktop/AI*/*/_work_merge/other_overlay/lib/modules/6.6.151/*.ko* 2>/dev/null
echo "--- ours (repo root + backup_sem) ---"
sha256sum "/mnt/d/Desktop/AI 辅助对话/mt7996e-edca.ko" "/mnt/d/Desktop/AI 辅助对话/mt7996e-ampdu.ko" "/mnt/d/Desktop/AI 辅助对话/_build/mac80211.ko" "/mnt/d/Desktop/AI 辅助对话/_build/m.ko" 2>/dev/null
ls -la /mnt/d/Desktop/AI*/*/_work_merge/our_side/backup_sem/modules/ 2>/dev/null
sha256sum /mnt/d/Desktop/AI*/*/_work_merge/our_side/backup_sem/modules/* 2>/dev/null
echo "=== vermagic each ==="
for f in /mnt/d/Desktop/AI*/*/_work_merge/other_overlay/lib/modules/6.6.151/*.ko* /mnt/d/Desktop/AI*/*/_work_merge/our_side/backup_sem/modules/* /mnt/d/Desktop/AI 辅助对话/mt7996e-*.ko; do
  printf "%-90s " "$(basename "$f")"; strings -a "$f" 2>/dev/null | grep -oE "vermagic=[^ ]*" | head -1; echo;
done
echo "=== other mt7996e.patched strings: dscp/edca/trace ==="
strings -a /mnt/d/Desktop/AI*/*/_work_merge/other_overlay/lib/modules/6.6.151/mt7996e.ko.patched-20261027-120214 | grep -iE "dscp|wifi_dscp|edca|aifs|cwmin|wmm|wdrr|txq|trace_|__tracepoint" | sort -u | head -60
echo "=== our mt7996e-edca strings ==="
strings -a "/mnt/d/Desktop/AI 辅助对话/mt7996e-edca.ko" | grep -iE "dscp|wifi_dscp|edca|aifs|cwmin|wmm|wdrr|txq|trace_|__tracepoint" | sort -u | head -60
echo DONE