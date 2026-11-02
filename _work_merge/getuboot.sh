#!/bin/bash
BR=/root/src/openwrt-24.10.0
echo "=== look for u-boot source ==="
ls $BR/dl/ 2>/dev/null | grep -i uboot
find / -maxdepth 6 -name "u-boot-2024.10*" -o -maxdepth 6 -name "uboot-mediatek-2024.10*" 2>/dev/null | head
ls -la /root/dl/ 2>/dev/null
echo "=== build_dir uboot ==="
find /root -maxdepth 5 -type d -name "u-boot-*" 2>/dev/null | head
echo "=== try downloading u-boot 2024.10 source ==="
cd /root/dl 2>/dev/null || cd /root
if [ ! -f u-boot-2024.10.tar.bz2 ]; then
  curl -sL -o u-boot-2024.10.tar.bz2 https://ftp.denx.de/pub/u-boot/u-boot-2024.10.tar.bz2 --max-time 300 && echo "downloaded" || echo "download failed"
fi
ls -la u-boot-2024.10.tar.bz2 2>/dev/null
echo DONE
