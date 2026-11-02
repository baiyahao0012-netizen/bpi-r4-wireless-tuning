cd /root/merge/fit
names=(kernel-1 fdt-1 fdt-emmc fdt-rtc fdt-sd fdt-wifi rootfs-1)
i=0
for name in "${names[@]}"; do
  dumpimage -T flat_dt -p $i -o "$name.bin" ../p7.bin 2>&1 | head -3
  i=$((i+1))
done
ls -la
echo "=== rtc overlay ==="
dtc -I dtb -O dts fdt-rtc.bin 2>&1 | head -60
echo "=== base dtb rtc refs ==="
dtc -I dtb -O dts fdt-1.bin 2>/dev/null > fdt-1.dts; wc -l fdt-1.dts
grep -n -i -E "rtc|pcf|ds3231|8563|hym|rx8025|i2c" fdt-1.dts | head -50
echo DONE