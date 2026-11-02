#!/bin/bash
cd /root/fitparts
echo "=== FIT DTB header (totalsize must be 0x1000) ==="
xxd -l 8 fit.dtb
xxd -l 8 new_fit.dtb
echo
python3 - <<'PY'
import struct, hashlib
def parse_fit_dtb(path):
    d=open(path,'rb').read()
    magic, totalsize, off_dt_struct, off_dt_strings, off_mem_rsvmap, version, last_comp = struct.unpack('>IIIIIII', d[:28])
    return d, totalsize
d, ts = parse_fit_dtb('/root/fitparts/new_fit.dtb')
print('new FIT DTB totalsize = 0x%x' % ts)
d0, ts0 = parse_fit_dtb('/root/fitparts/fit.dtb')
print('old FIT DTB totalsize = 0x%x' % ts0)

itb=open('/root/fitparts/new.itb','rb').read()
print('new.itb size = %d (0x%x)' % (len(itb), len(itb)))
# image table from mkimage -l offsets we trust: parse via dtc output manually
imgs = {
 'kernel-1': (0x0, 5515772),
 'fdt-1': (0x543000, 0xb8f9),
 'emmc': (0x54f000, 0x60a),
 'rtc': (0x550000, 0x11d),
 'sd': (0x551000, 0x5c2),
 'wifi': (0x552000, 0x8f1),
 'rootfs-1': (0x553000, 0xade000),
}
for name,(off,sz) in imgs.items():
    a=off+ts
    print('%-10s rel=0x%-8x abs=0x%-8x size=%-9d end=0x%x' % (name,off,a,sz,a+sz))
print('last end = 0x%x  target 0x1032000  match=%s' % (0x553000+ts+0xade000, 0x553000+ts+0xade000==0x1032000))

# extract rootfs
a=0x553000+ts
rf=itb[a:a+0xade000]
orig=open('/root/fitparts/rootfs.squashfs','rb').read()
print('rootfs prefix match:', rf[:len(orig)]==orig)
print('rootfs pad region all zero:', all(b==0 for b in rf[len(orig):]))
print('squashfs bytes_used = 11274044, padded device size = %d' % len(rf))
# verify kernel
k=itb[0x0+ts:0x0+ts+5515772]
open('/root/fitparts/k.zst','wb').write(k)
PY
zstd -d -q -f k.zst -o k.bin
echo -n "kernel md5 in FIT: "; md5sum k.bin | cut -d' ' -f1
echo -n "source Image md5 : "; md5sum /root/kbuild/linux-6.6.73/arch/arm64/boot/Image | cut -d' ' -f1
echo "=== copy new.itb to board ==="
scp -o StrictHostKeyChecking=no /root/fitparts/new.itb root@192.168.240.1:/tmp/new.itb 2>&1 | tail -2
ssh -o StrictHostKeyChecking=no root@192.168.240.1 'ls -la /tmp/new.itb; md5sum /tmp/new.itb' 2>&1 | grep -v "WARNING\|vulnerable\|upgraded"
md5sum /root/fitparts/new.itb
echo DONE
