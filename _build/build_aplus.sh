#!/bin/bash
set -e
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
cd "$SDK"
echo "=== clean ==="
make package/kernel/mt76/clean V=s >/tmp/mt76_clean_aplus.log 2>&1 || true
echo "=== prepare ==="
make package/kernel/mt76/prepare V=s >/tmp/mt76_prep_aplus.log 2>&1
TREE=$(ls -d build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6)
echo "TREE=$TREE"
echo "=== apply A+ ==="
python3 "/mnt/d/Desktop/AI 辅助对话/_build/apply_aplus.py" "$TREE"
echo "=== force default EEPROM ==="
python3 - "$TREE" <<'PY'
import sys
p=sys.argv[1]+"/mt7996/eeprom.c"
s=open(p).read()
old="\treturn mt7996_eeprom_check_or_use_default(dev, use_default);"
new="\tdev_warn(dev->mt76.dev, \"mt7996: DIAG force default EEPROM\\n\");\n\treturn mt7996_eeprom_check_or_use_default(dev, true);"
assert s.count(old)==1
open(p,"w").write(s.replace(old,new))
print("eeprom forced")
PY
rm -f "$TREE"/mt76.o "$TREE"/tx.o "$TREE"/debugfs.o "$TREE"/mt76.ko "$TREE"/mt76-connac-lib.ko "$TREE"/mt7996/mt7996e.ko
echo "=== compile ==="
make package/kernel/mt76/compile V=s -j8 >/tmp/mt76_build_aplus.log 2>&1 || true
for f in "$TREE/mt76.ko" "$TREE/mt76-connac-lib.ko" "$TREE/mt7996/mt7996e.ko"; do
  if [ -f "$f" ]; then
    echo "OK $f $(stat -c%s "$f") $(md5sum "$f" | cut -d' ' -f1)"
  else
    echo "MISSING $f"
  fi
done
strings "$TREE/mt76.ko" | grep -E 'sta_weight|tx_weight' | head || true
grep -E "error:" /tmp/mt76_build_aplus.log | head -10 || true
mkdir -p /mnt/c/Temp/dsh_build
cp "$TREE/mt76.ko" /mnt/c/Temp/dsh_build/aplus-mt76.ko 2>/dev/null || true
cp "$TREE/mt76-connac-lib.ko" /mnt/c/Temp/dsh_build/aplus-mt76-connac-lib.ko 2>/dev/null || true
cp "$TREE/mt7996/mt7996e.ko" /mnt/c/Temp/dsh_build/aplus-mt7996e.ko 2>/dev/null || true
