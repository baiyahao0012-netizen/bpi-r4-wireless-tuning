#!/bin/bash
# VM 阶段一：OpenWrt SDK 编译环境搭建（直接粘贴执行，约 10-20 分钟）
set -e
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq build-essential zstd unzip file rsync wget curl gawk gettext quilt python3 2>&1 | tail -2
cd /root
mkdir -p sdk src
cd /root/sdk
if [ ! -f openwrt-sdk.tar.zst ]; then
  echo "== [1/6] downloading SDK (~208MB) =="
  wget -q https://downloads.openwrt.org/releases/24.10.0/targets/mediatek/filogic/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64.tar.zst -O openwrt-sdk.tar.zst
fi
if [ ! -d openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64 ]; then
  echo "== [2/6] extracting SDK =="
  tar --zstd -xf openwrt-sdk.tar.zst
fi
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
cd /root
if [ ! -f openwrt-src.tar.gz ]; then
  echo "== [3/6] downloading openwrt v24.10.0 source =="
  wget -q https://codeload.github.com/openwrt/openwrt/tar.gz/refs/tags/v24.10.0 -O openwrt-src.tar.gz
  tar -xzf openwrt-src.tar.gz -C src
fi
SRC=$(ls -d /root/src/openwrt-* | head -1)
echo "== [4/6] copying mt76 + mac80211 packages into SDK =="
cp -r "$SRC/package/kernel/mt76" "$SRC/package/kernel/mac80211" "$SDK/package/kernel/"
cd "$SDK"
echo "== [5/6] downloading mac80211 backports source =="
make package/kernel/mac80211/download 2>&1 | tail -3
echo "== [6/6] extracting backports (patched) =="
make package/kernel/mac80211/prepare 2>&1 | tail -3
echo "== locate fq.c =="
find build_dir -name fq.c | head -3
echo VM_STAGE1_DONE
