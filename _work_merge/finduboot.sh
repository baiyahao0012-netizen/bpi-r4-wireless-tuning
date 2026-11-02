#!/bin/bash
echo "=== board SD: first 64KB hexdump head ==="
ssh -o StrictHostKeyChecking=no root@192.168.240.1 'dd if=/dev/mmcblk0 bs=512 count=2 2>/dev/null | hexdump -C | head -8' 2>&1 | grep -v "WARNING\|vulnerable\|upgraded"
echo "=== region at 6656k (check if zeros) ==="
xxd -s $((6656*1024)) -l 64 /root/uboot/uboot_region.bin
echo "=== count non-zero bytes in that 6MB ==="
python3 -c "
d=open('/root/uboot/uboot_region.bin','rb').read()
print('len',len(d),'nonzero',sum(1 for b in d if b))
"
echo "=== scan first 70MB of board SD for U-Boot strings ==="
ssh -o StrictHostKeyChecking=no root@192.168.240.1 'dd if=/dev/mmcblk0 bs=1M count=70 2>/dev/null' > /root/uboot/sd_first70m.bin 2>/dev/null
ls -la /root/uboot/sd_first70m.bin
for pat in "U-Boot 20" "ZSTD" "zstd" "LZMA" "lzma" "gzip" "Uncompressing"; do
  n=$(strings -a -n 6 /root/uboot/sd_first70m.bin 2>/dev/null | grep -c "$pat")
  echo "$pat -> $n"
done
echo "=== sample U-Boot strings ==="
strings -a -n 8 /root/uboot/sd_first70m.bin 2>/dev/null | grep -iE "U-Boot|zstd|lzma" | sort -u | head -20
echo DONE
