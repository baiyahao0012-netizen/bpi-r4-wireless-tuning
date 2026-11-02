#!/bin/bash
echo "=== search gzip magic in first 12MB ==="
for off in 0 4096 0x560000 0x561000 0x56c000 0x100000; do
  printf "offset %s: " "$off"
  xxd -s $((off)) -l 16 /root/p7.img | head -1
done
echo "=== python: find first 1f8b ==="
python3 - <<'EOF'
data = open('/root/p7.img','rb').read(12*1024*1024)
i = data.find(b'\x1f\x8b')
print("first gzip magic at:", hex(i) if i>=0 else "none")
# list all 1f8b occurrences in first 8MB
offs = []
p = 0
while True:
    p = data.find(b'\x1f\x8b', p)
    if p < 0 or p > 8*1024*1024: break
    offs.append(hex(p)); p += 1
print("gzip magics:", offs[:20])
# check FIT fdt totalsize
print("fdt header bytes:", data[0:40].hex())
EOF
echo "=== gzip the new kernel ==="
gzip -9 -c /root/kbuild/linux-6.6.73/arch/arm64/boot/Image > /root/new_Image.gz
ls -la /root/new_Image.gz
echo "old kernel compressed size: $((0x55f59a))"
echo "new kernel compressed size: $(stat -c %s /root/new_Image.gz)"
echo DONE
