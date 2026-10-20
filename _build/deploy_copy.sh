#!/bin/bash
SRC=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mac80211-regular/backports-6.12.6/.pkgdir/kmod-mac80211/lib/modules/6.6.73/mac80211.ko
DST="/mnt/d/Desktop/AI 辅助对话/_build/mac80211.ko"
cp "$SRC" "$DST" && ls -la "$DST" && md5sum "$SRC" "$DST" && echo COPY_DONE
