cd /root/merge
OTH="/mnt/d/Desktop/AI 辅助对话/_work_merge/other_overlay"
echo "=== other overlay modules sha256 ==="
sha256sum "$OTH"/lib/modules/6.6.151/*.ko* 2>/dev/null
echo "=== sizes ==="
ls -la "$OTH"/lib/modules/6.6.151/
echo "=== vermagic ==="
for f in "$OTH"/lib/modules/6.6.151/*; do printf "%-40s " "$(basename "$f")"; strings -a "$f" 2>/dev/null | grep -oE "vermagic=[^ ]* [^ ]* [^ ]* [^ ]*" | head -1; done
echo "=== their mt7996e.patched feature strings ==="
strings -a "$OTH/lib/modules/6.6.151/mt7996e.ko.patched-20261027-120214" | grep -iE "dscp|edca|aifs|cwmin|wmm|wdrr|txq|trace|aci|retry" | sort -u | head -80
echo "=== their mt7996e.ko (current) feature strings ==="
strings -a "$OTH/lib/modules/6.6.151/mt7996e.ko" | grep -iE "dscp|edca|aifs|cwmin|wmm|wdrr|txq|trace|aci|retry" | sort -u | head -80
echo "=== their mac80211.ko feature strings ==="
strings -a "$OTH/lib/modules/6.6.151/mac80211.ko" | grep -iE "dscp|wifi_dscp|wdrr|trace_|txq|wmm|edca" | sort -u | head -80
echo DONE