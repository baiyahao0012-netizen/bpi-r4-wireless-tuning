#!/bin/bash
exec > /root/build4.log 2>&1
export http_proxy=http://172.25.112.1:7897
export https_proxy=http://172.25.112.1:7897
export NO_PROXY=localhost,127.0.0.1
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
cd "$SDK"
pkill -f menuconfig 2>/dev/null
sleep 2
echo "=== make defconfig ==="
make defconfig 2>&1 | tail -10
echo "DEFCONFIG_RC=$?"
grep CONFIG_HAVE_DOT_CONFIG .config | head -1
echo "=== make target/linux/prepare (FORCE) ==="
make FORCE=1 target/linux/prepare V=s 2>&1 | tail -30
echo "PREPARE_PIPE_RC=${PIPESTATUS[0]}"
echo "=== kernel .config ==="
ls -la build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/linux-6.6.73/.config 2>/dev/null
echo BUILD4_DONE
