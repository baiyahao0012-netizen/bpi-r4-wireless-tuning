#!/bin/bash
set -e
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
cd "$SDK"
make package/kernel/mt76/clean V=s >/tmp/mt76_clean_tr.log 2>&1 || true
make package/kernel/mt76/prepare V=s >/tmp/mt76_prep_tr.log 2>&1
TREE=$(ls -d build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6)
python3 "/mnt/d/Desktop/AI 辅助对话/_build/apply_aplus.py" "$TREE"
python3 "/mnt/d/Desktop/AI 辅助对话/_build/apply_txwi_rate.py" "$TREE"
python3 - "$TREE" <<'PY'
import sys
p=sys.argv[1]+"/mt7996/eeprom.c"
s=open(p).read()
old="\treturn mt7996_eeprom_check_or_use_default(dev, use_default);"
new="\tdev_warn(dev->mt76.dev, \"mt7996: DIAG force default EEPROM\\n\");\n\treturn mt7996_eeprom_check_or_use_default(dev, true);"
assert s.count(old)==1
open(p,"w").write(s.replace(old,new))
PY
rm -f "$TREE"/mt76.o "$TREE"/tx.o "$TREE"/debugfs.o "$TREE"/mt7996/debugfs.o "$TREE"/mt7996/mac.o "$TREE"/mt76.ko "$TREE"/mt76-connac-lib.ko "$TREE"/mt7996/mt7996e.ko
make package/kernel/mt76/compile V=s -j8 >/tmp/mt76_build_tr.log 2>&1 || true
for f in "$TREE/mt76.ko" "$TREE/mt76-connac-lib.ko" "$TREE/mt7996/mt7996e.ko"; do
  [ -f "$f" ] && echo "OK $f $(stat -c%s "$f") $(md5sum "$f" | cut -d' ' -f1)" || echo "MISSING $f"
done
strings "$TREE/mt7996/mt7996e.ko" | grep force_rate | head || true
grep -E "error:" /tmp/mt76_build_tr.log | head -10 || true
cp "$TREE/mt76.ko" /mnt/c/Temp/dsh_build/tr-mt76.ko
cp "$TREE/mt76-connac-lib.ko" /mnt/c/Temp/dsh_build/tr-mt76-connac-lib.ko
cp "$TREE/mt7996/mt7996e.ko" /mnt/c/Temp/dsh_build/tr-mt7996e.ko
