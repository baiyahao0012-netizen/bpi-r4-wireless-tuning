SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
OUT=/mnt/d/Desktop/AI\ 辅助对话/_work_recover
cd /root
echo "=== actual uncompressed size of p7 backup ==="
gzip -dc "$OUT/p7_raw_pre_kernelflash_20261102.img.gz" | wc -c
echo "=== extract to /root/p7.img ==="
if [ ! -s /root/p7.img ]; then gzip -dc "$OUT/p7_raw_pre_kernelflash_20261102.img.gz" > /root/p7.img; fi
ls -la /root/p7.img
echo "=== dumpimage -l ==="
ls $SDK/staging_dir/host/bin/ | grep -i "image\|fit" 
$SDK/staging_dir/host/bin/dumpimage -l /root/p7.img 2>&1 | head -40
echo "=== hexdump of first 64 bytes ==="
xxd -l 64 /root/p7.img
echo DONE