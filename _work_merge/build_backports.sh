#!/bin/bash
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
export PATH=$SDK/staging_dir/host/bin:$SDK/staging_dir/toolchain-aarch64_cortex-a53_gcc-13.3.0_musl/bin:$PATH
export STAGING_DIR=$SDK/staging_dir
cd $SDK
echo "=== mac80211 backports ==="
make package/kernel/mac80211/compile V=s -j24 > /root/mac_pkg.log 2>&1
echo "mac rc=$?"
echo "=== mt76 merge ==="
bash "/mnt/d/Desktop/AI 辅助对话/_build/build_merge_mt76.sh" > /root/mt76_merge2.log 2>&1
echo "mt76 rc=$?"
echo BACKPORTS_DONE
