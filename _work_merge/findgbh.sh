#!/bin/bash
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
echo "--- package dirs ---"
ls $SDK/package/kernel/ | head -30
echo "--- search gpio-button ---"
find $SDK -maxdepth 4 -iname "*gpio-button*" 2>/dev/null | head
echo "--- search ko anywhere ---"
find $SDK -name "gpio-button-hotplug.ko" 2>/dev/null | head
echo DONE
