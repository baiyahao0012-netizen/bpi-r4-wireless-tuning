#!/bin/bash
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
KD=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/linux-6.6.73
NEW=/root/kbuild/linux-6.6.73
export PATH=$SDK/staging_dir/host/bin:$SDK/staging_dir/toolchain-aarch64_cortex-a53_gcc-13.3.0_musl/bin:$PATH

echo "=== check new vmlinux.symvers has the missing symbols ==="
grep -c "consume_skb" $NEW/vmlinux.symvers
grep -c "trace_event_printf" $NEW/vmlinux.symvers
grep -c "trace_event_raw_init" $NEW/vmlinux.symvers
wc -l $NEW/vmlinux.symvers

echo "=== merge: new vmlinux.symvers (wins) + old SDK Module.symvers ==="
python3 - <<'PYEOF'
newp='/root/kbuild/linux-6.6.73/vmlinux.symvers'
oldp='/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/linux-6.6.73/Module.symvers'
outp='/root/Module.symvers.merged'
def load(p):
    r=[]
    for l in open(p, errors='replace'):
        l=l.rstrip('\n')
        if not l.strip(): continue
        f=l.split('\t')
        r.append((f[1] if len(f)>1 else l, l))
    return r
seen=set(); out=[]
for sym,l in load(newp)+load(oldp):
    if sym in seen: continue
    seen.add(sym); out.append(l)
open(outp,'w').write('\n'.join(out)+'\n')
print("merged lines:", len(out))
PYEOF
wc -l /root/Module.symvers.merged

echo "=== install merged Module.symvers ==="
cp $KD/Module.symvers /root/Module.symvers.sdk-orig
cp /root/Module.symvers.merged $KD/Module.symvers
grep -c "consume_skb" $KD/Module.symvers

echo "=== rebuild mac80211 -j24 ==="
cd $SDK
date
make package/kernel/mac80211/compile V=s -j24 > /root/mac80211_build3.log 2>&1
echo "compile rc=$?"
date
KO=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mac80211-regular/backports-6.12.6/.pkgdir/kmod-mac80211/lib/modules/6.6.73/mac80211.ko
ls -la $KO 2>&1
echo "=== tracepoints in new ko ==="
strings -a $KO 2>/dev/null | grep -c "__tracepoint"
readelf -SW $KO 2>/dev/null | grep -ci "tracepoint"
strings -a $KO 2>/dev/null | grep -c "wifi_dscp"
echo MAC80211_DONE
