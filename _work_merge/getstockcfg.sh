#!/bin/bash
cd /root
echo "=== FIT DTB kernel offset ==="
dd if=p7.img of=/tmp/fit0.dtb bs=4096 count=1 2>/dev/null
dtc -I dtb -O dts /tmp/fit0.dtb 2>/dev/null | grep -E "kernel-1|data-offset|data-size|compression" | head -8
echo "=== extract original kernel ==="
dd if=p7.img of=/root/kern_orig.gz bs=1 skip=4096 count=5633434 2>/dev/null
ls -la /root/kern_orig.gz
gunzip -c /root/kern_orig.gz > /root/kern_orig.bin 2>/dev/null
ls -la /root/kern_orig.bin
echo "=== extract-ikconfig ==="
/root/kbuild/linux-6.6.73/scripts/extract-ikconfig /root/kern_orig.bin > /root/stock_kernel.config 2>/root/ikconfig.err
echo "rc=$?"
wc -l /root/stock_kernel.config 2>/dev/null
head -3 /root/stock_kernel.config
cat /root/ikconfig.err | head -3
echo DONE
