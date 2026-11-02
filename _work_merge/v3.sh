#!/bin/bash
cd /root/fitparts
xxd -l 8 fit.dtb
xxd -l 8 new_fit.dtb
python3 - <<'PY'
import struct
def ts(p):
    d=open(p,'rb').read()
    return struct.unpack('>I', d[4:8])[0]
t=ts('/root/fitparts/new_fit.dtb'); t0=ts('/root/fitparts/fit.dtb')
print('new totalsize=0x%x  old totalsize=0x%x' % (t,t0))
itb=open('/root/fitparts/new.itb','rb').read()
print('new.itb size=%d' % len(itb))
imgs={'kernel-1':(0x0,5515772),'fdt-1':(0x543000,0xb8f9),'emmc':(0x54f000,0x60a),
      'rtc':(0x550000,0x11d),'sd':(0x551000,0x5c2),'wifi':(0x552000,0x8f1),
      'rootfs-1':(0x553000,0xade000)}
for n,(o,s) in imgs.items():
    print('%-9s rel=0x%-7x abs=0x%-7x size=%-8d end=0x%x' % (n,o,o+t,s,o+t+s))
end=0x553000+t+0xade000
print('last end=0x%x target=0x1032000 match=%s' % (end,end==0x1032000))
rf=itb[0x553000+t:0x553000+t+0xade000]
orig=open('/root/fitparts/rootfs.squashfs','rb').read()
print('rootfs prefix match:', rf[:len(orig)]==orig)
print('rootfs pad all zero:', all(b==0 for b in rf[len(orig):]))
k=itb[t:t+5515772]
open('/root/fitparts/k.zst','wb').write(k)
PY
zstd -d -q -f k.zst -o k.bin
echo -n "FIT kernel md5: "; md5sum k.bin | cut -d' ' -f1
echo -n "Image md5     : "; md5sum /root/kbuild/linux-6.6.73/arch/arm64/boot/Image | cut -d' ' -f1
echo DONE
