#!/bin/bash
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
KD=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/linux-6.6.73
NEW=/root/kbuild/linux-6.6.73
export PATH=$SDK/staging_dir/host/bin:$SDK/staging_dir/toolchain-aarch64_cortex-a53_gcc-13.3.0_musl/bin:$PATH
export STAGING_DIR=$SDK/staging_dir

echo "=== new vmlinux.symvers lines: $(wc -l < $NEW/vmlinux.symvers) ==="
echo "=== sdk orig Module.symvers lines: $(wc -l < /root/Module.symvers.sdk-orig 2>/dev/null) ==="

python3 - <<'PY'
new='/root/kbuild/linux-6.6.73/vmlinux.symvers'
sdk='/root/Module.symvers.sdk-orig'
out='/root/Module.symvers.merged2'
d={}
for line in open(new):
    p=line.rstrip('\n').split('\t')
    if len(p)>=2: d[p[1]]=line.rstrip('\n')
for line in open(sdk):
    p=line.rstrip('\n').split('\t')
    if len(p)>=2 and p[1] not in d: d[p[1]]=line.rstrip('\n')
with open(out,'w') as f:
    for k,v in d.items(): f.write(v+'\n')
print('merged symbols:', len(d))
print('trace_event_raw_init present:', 'trace_event_raw_init' in d)
print('consume_skb present:', 'consume_skb' in d)
PY

cp /root/Module.symvers.merged2 $KD/Module.symvers
cp $NEW/.config $KD/.config
echo "=== rebuild mac80211 ==="
cd $SDK
date
make package/kernel/mac80211/compile V=s -j24 > /root/mac_out3.log 2>&1
echo "compile rc=$?"
date
KO=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mac80211-regular/backports-6.12.6/.pkgdir/kmod-mac80211/lib/modules/6.6.73/mac80211.ko
CFG=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mac80211-regular/backports-6.12.6/.pkgdir/kmod-cfg80211/lib/modules/6.6.73/cfg80211.ko
ls -la $KO $CFG 2>&1
NM=$SDK/staging_dir/toolchain-aarch64_cortex-a53_gcc-13.3.0_musl/bin/aarch64-openwrt-linux-musl-nm
echo "=== undefined trace symbols in mac80211.ko ==="
$NM -u $KO 2>/dev/null | grep -c trace
echo "=== wifi_dscp strings ==="
strings $KO | grep -c wifi_dscp
md5sum $KO $CFG
echo MAC80211_REBUILD_DONE
