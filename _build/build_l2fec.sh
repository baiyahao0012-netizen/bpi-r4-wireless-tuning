#!/bin/bash
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
CC="$SDK/staging_dir/toolchain-aarch64_cortex-a53_gcc-13.3.0_musl/bin/aarch64-openwrt-linux-musl-gcc"
"$CC" -O2 -static -o /mnt/c/Temp/l2fec_send "/mnt/d/Desktop/AI 辅助对话/_work_final/rtc_over_wifi/l2fec_send.c"