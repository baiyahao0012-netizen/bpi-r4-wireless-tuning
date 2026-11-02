#!/bin/bash
A="/mnt/d/Desktop/AI 辅助对话/_work_merge/artifacts"
rm -rf /root/oafpkg; mkdir -p /root/oafpkg
cp /root/oafbuild/oaf.ko /root/oafpkg/
cp /root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/package/OpenAppFilter/oaf/Makefile /root/oafpkg/oaf-Makefile.KernelPackage
cp /root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/package/OpenAppFilter/oaf/src/Makefile /root/oafpkg/oaf-src-Makefile.Kbuild
cd /root/oafpkg && tar czf "$A/oaf-rebuilt-0x480.tar.gz" .
cd "$A" && md5sum * > MD5SUMS.txt
cat MD5SUMS.txt
du -sh "$A"
echo ART2_DONE
