set -e
cd /root/merge
echo "=== extract FIT components ==="
mkdir -p fit
cd fit
for img in kernel-1 fdt-1 fdt-mt7988a-bananapi-bpi-r4-emmc fdt-mt7988a-bananapi-bpi-r4-rtc fdt-mt7988a-bananapi-bpi-r4-sd fdt-mt7988a-bananapi-bpi-r4-wifi-mt7996a rootfs-1; do
  dumpimage -T flat_dt -p 0 -i ../p7.bin -o "$img.bin" ../p7.bin >/dev/null 2>&1 || true
done
ls -la
echo "=== extract all with dumpimage -p index ==="
i=0
for name in kernel-1 fdt-1 fdt-emmc fdt-rtc fdt-sd fdt-wifi rootfs-1; do
  dumpimage -T flat_dt -p $i -i ../p7.bin -o "$name.bin" ../p7.bin >/dev/null 2>&1 && echo "extracted $name ($i)" || echo "FAIL $name ($i)"
  i=$((i+1))
done
ls -la
echo "=== rtc overlay decompile ==="
dtc -I dtb -O dts fdt-rtc.bin 2>/dev/null || echo "dtc failed"
echo "=== base dtb: rtc/pcf/ds3231 mentions ==="
dtc -I dtb -O dts fdt-1.bin 2>/dev/null > fdt-1.dts || true
wc -l fdt-1.dts 2>/dev/null || true
grep -n -i -E "rtc|pcf|ds3231|pcf8563|hym8563|rx8025" fdt-1.dts | head -40
echo DONE