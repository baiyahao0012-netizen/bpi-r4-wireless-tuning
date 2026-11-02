#!/bin/bash
set -e
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
cd "$SDK"
echo "=== clean ==="
make package/kernel/mt76/clean V=s >/tmp/mt76_clean_merge.log 2>&1 || true
echo "=== prepare ==="
make package/kernel/mt76/prepare V=s >/tmp/mt76_prep_merge.log 2>&1
TREE=$(ls -d build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6)
echo "TREE=$TREE"
echo "=== apply A+ ==="
python3 "/mnt/d/Desktop/AI 辅助对话/_build/apply_aplus.py" "$TREE"
echo "=== apply txwi_rate ==="
python3 "/mnt/d/Desktop/AI 辅助对话/_build/apply_txwi_rate.py" "$TREE"
echo "=== apply 355 (tx retry reporting) ==="
python3 - "$TREE" <<'PY'
import sys
p = sys.argv[1] + "/mt7996/mac.c"
s = open(p, encoding="utf-8").read()
old = "\t\t\tinfo->status.ampdu_ack_len =\n\t\t\t\t!!(info->flags & IEEE80211_TX_STAT_ACK);\n\n\t\t\tinfo->status.rates[0].idx = -1;\n"
new = ("\t\t\tinfo->status.ampdu_ack_len =\n\t\t\t\t!!(info->flags & IEEE80211_TX_STAT_ACK);\n\n"
       "\t\t\t/*\n"
       "\t\t\t * Report the real number of transmission attempts so\n"
       "\t\t\t * mac80211 can account per-frame TX retries. Leaving the\n"
       "\t\t\t * legacy status rates untouched makes them alias the\n"
       "\t\t\t * rate-control union and leak the requested retry count\n"
       "\t\t\t * on the free path.\n"
       "\t\t\t */\n"
       "\t\t\tinfo->status.rates[0].idx = 0;\n"
       "\t\t\tinfo->status.rates[0].count =\n"
       "\t\t\t\tFIELD_GET(MT_TXS5_F0_TX_COUNT, txs_data[5]);\n")
assert s.count(old) == 1, ("355 anchor count", s.count(old))
open(p, "w", encoding="utf-8").write(s.replace(old, new, 1))
print("355 APPLIED")
PY
echo "=== force default EEPROM (diagnostic, matches current board) ==="
python3 - "$TREE" <<'PY'
import sys
p = sys.argv[1] + "/mt7996/eeprom.c"
s = open(p, encoding="utf-8").read()
old = "\treturn mt7996_eeprom_check_or_use_default(dev, use_default);"
new = "\tdev_warn(dev->mt76.dev, \"mt7996: DIAG force default EEPROM\\n\");\n\treturn mt7996_eeprom_check_or_use_default(dev, true);"
assert s.count(old) == 1
open(p, "w", encoding="utf-8").write(s.replace(old, new, 1))
print("EEPROM FORCED")
PY
rm -f "$TREE"/mt76.o "$TREE"/tx.o "$TREE"/debugfs.o "$TREE"/mt7996/debugfs.o "$TREE"/mt7996/mac.o "$TREE"/mt7996/eeprom.o "$TREE"/mt76.ko "$TREE"/mt76-connac-lib.ko "$TREE"/mt7996/mt7996e.ko
echo "=== compile ==="
make package/kernel/mt76/compile V=s -j8 >/tmp/mt76_build_merge.log 2>&1 || true
for f in "$TREE/mt76.ko" "$TREE/mt76-connac-lib.ko" "$TREE/mt7996/mt7996e.ko"; do
  if [ -f "$f" ]; then echo "OK $f $(stat -c%s "$f") $(md5sum "$f" | cut -d' ' -f1)"; else echo "MISSING $f"; fi
done
echo "=== errors ==="
grep -E "error:" /tmp/mt76_build_merge.log | head -10 || true
mkdir -p /mnt/c/Temp/dsh_build
cp "$TREE/mt76.ko" /mnt/c/Temp/dsh_build/merged-mt76.ko 2>/dev/null || true
cp "$TREE/mt76-connac-lib.ko" /mnt/c/Temp/dsh_build/merged-mt76-connac-lib.ko 2>/dev/null || true
cp "$TREE/mt7996/mt7996e.ko" /mnt/c/Temp/dsh_build/merged-mt7996e.ko 2>/dev/null || true
echo BUILD_DONE
