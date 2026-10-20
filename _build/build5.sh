#!/bin/bash
exec > /root/build5.log 2>&1
export http_proxy=http://172.25.112.1:7897
export https_proxy=http://172.25.112.1:7897
export NO_PROXY=localhost,127.0.0.1
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
cd "$SDK"
echo "=== mac80211 package download ==="
make package/kernel/mac80211/download V=s 2>&1 | tail -25
echo "DL_PIPE_RC=${PIPESTATUS[0]}"
echo "=== dl/ contents (mac80211) ==="
ls -la dl/ 2>/dev/null | grep -i "mac80211\|backport" | head
echo "=== find backports source dirs ==="
ls -d build_dir/target-aarch64_cortex-a53_musl/*mac80211* 2>/dev/null | head
ls -d build_dir/target-aarch64_cortex-a53_musl/*backport* 2>/dev/null | head
echo "=== find fq.c ==="
find build_dir/target-aarch64_cortex-a53_musl -name "fq.c" 2>/dev/null | head -5
echo BUILD5_DONE
