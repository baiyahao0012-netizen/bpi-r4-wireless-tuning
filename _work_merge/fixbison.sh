#!/bin/bash
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
mkdir -p /builder/shared-workdir
if [ ! -e /builder/shared-workdir/build ]; then
  ln -s "$SDK" /builder/shared-workdir/build
fi
ls -la /builder/shared-workdir/
echo "=== test bison ==="
export PATH=$SDK/staging_dir/host/bin:$PATH
bison --version 2>&1 | head -2
echo "bison rc=$?"
echo "=== test flex ==="
flex --version 2>&1 | head -2
echo FIX_DONE
