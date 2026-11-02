#!/bin/bash
WS="/mnt/d/Desktop/AI 辅助对话"
A="$WS/_work_merge/artifacts"
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
KD=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/linux-6.6.73
rm -rf "$A"; mkdir -p "$A"

echo "=== 1. configs ==="
cp /root/kbuild/linux-6.6.73/.config "$A/config.minimal-tracing"
cp $KD/.config.before-ftrace "$A/config.baseline-sdk-orig"
cp /root/config.full-ftrace "$A/config.full-tracing-reference"

echo "=== 2. kernel image + FIT ==="
cp /root/fitparts/k.bin "$A/Image.minimal-tracing.raw" 2>/dev/null
cp /root/fitparts/new.itb "$A/new.itb.flashed"
ls -la "$A"

echo "=== 3. modules tarball (corrected: modstage + new backports) ==="
rm -rf /root/modfinal; mkdir -p /root/modfinal/lib/modules/6.6.73
cp /root/modstage/lib/modules/6.6.73/*.ko /root/modfinal/lib/modules/6.6.73/
cp /root/bpstage/*.ko /root/modfinal/lib/modules/6.6.73/
echo "count: $(ls /root/modfinal/lib/modules/6.6.73/*.ko | wc -l)"
cd /root/modfinal && tar czf "$A/modules-103-rebuilt.tar.gz" lib
ls -la "$A/modules-103-rebuilt.tar.gz"

echo "=== 4. dscpstats test suite ==="
cp /root/dscptest.tar.gz "$A/dscptest.tar.gz"

echo "=== 5. checksums ==="
cd "$A" && md5sum * > MD5SUMS.txt && cat MD5SUMS.txt
echo "=== total ==="
du -sh "$A"
echo ARTIFACTS_DONE
