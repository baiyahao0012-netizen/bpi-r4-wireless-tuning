#!/bin/bash
exec > /root/build6.log 2>&1
export http_proxy=http://172.25.112.1:7897
export https_proxy=http://172.25.112.1:7897
export NO_PROXY=localhost,127.0.0.1
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
cd "$SDK"
echo "=== mac80211 prepare (extract+patch backports) ==="
make package/kernel/mac80211/prepare V=s 2>&1 | tail -15
echo "PREPARE_PIPE_RC=${PIPESTATUS[0]}"
echo "=== locate backports build dir ==="
ls -d build_dir/target-aarch64_cortex-a53_musl/*backport* 2>/dev/null
BP=$(ls -d build_dir/target-aarch64_cortex-a53_musl/*backport* 2>/dev/null | head -1)
echo "BP=$BP"
echo "=== find fq.c ==="
find "$BP" -name "fq.c" 2>/dev/null
FQ=$(find "$BP" -name "fq.c" 2>/dev/null | head -1)
echo "FQ=$FQ"
if [ -n "$FQ" ]; then
  echo "=== fq.c key functions (DRR) ==="
  grep -n "deficit\|quantum\|fq_tin_deficit\|fq_flow_deficit" "$FQ" | head -30
  echo "=== wc ==="
  wc -l "$FQ"
fi
echo BUILD6_DONE
