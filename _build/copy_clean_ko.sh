#!/bin/bash
TREE=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6
DEST="/mnt/d/Desktop/AI 辅助对话/mt7996e-ampdu.ko"
cp "$TREE/mt7996/mt7996e.ko" "$DEST"
ls -l "$DEST"
md5sum "$DEST"
