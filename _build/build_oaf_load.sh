#!/bin/bash
set -e
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
CC="$SDK/staging_dir/toolchain-aarch64_cortex-a53_gcc-13.3.0_musl/bin/aarch64-openwrt-linux-musl-gcc"
"$CC" -O2 -static -o /mnt/c/Temp/oaf_load "/mnt/d/Desktop/AI 辅助对话/_build/oaf_min_load.c"
file /mnt/c/Temp/oaf_load
