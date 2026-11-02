#!/bin/bash
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
cd /root/fitparts
echo "=== new FIT structure ==="
dd if=new.itb of=new_fit.dtb bs=1 count=4096 2>/dev/null
dtc -I dtb -O dts new_fit.dtb 2>/dev/null | grep -E "data-size|data-offset|compression|^\s+kernel-1|fdt-1|rootfs-1|fdt-mt|default =|config-mt" | head -40
echo
echo "=== verify kernel decompresses to our Image ==="
python3 - <<'PY'
import struct
d=open('/root/fitparts/new.itb','rb').read(4096)
# parse FIT DTB crudely: find data-offset/data-size for kernel-1
PY
python3 - <<'PY'
import subprocess
out=subprocess.run(['dtc','-I','dtb','-O','dts','/root/fitparts/new_fit.dtb'],capture_output=True,text=True).stdout
import re
# kernel-1 block
i=out.find('kernel-1 {')
blk=out[i:i+700]
off=int(re.search(r'data-offset = <(0x[0-9a-f]+)>',blk).group(1),16)
sz=int(re.search(r'data-size = <(0x[0-9a-f]+)>',blk).group(1),16)
print('kernel-1 data-offset=0x%x data-size=%d' % (off,sz))
abs_off = off + 0x1000
data=open('/root/fitparts/new.itb','rb').read()[abs_off:abs_off+sz]
open('/root/fitparts/kern_extracted.zst','wb').write(data)
i=out.find('rootfs-1 {')
blk=out[i:i+700]
roff=int(re.search(r'data-offset = <(0x[0-9a-f]+)>',blk).group(1),16)
rsz=int(re.search(r'data-size = <(0x[0-9a-f]+)>',blk).group(1),16)
print('rootfs-1 data-offset=0x%x data-size=%d abs=0x%x end=0x%x' % (roff,rsz,roff+0x1000,roff+0x1000+rsz))
d2=open('/root/fitparts/new.itb','rb').read()[roff+0x1000:roff+0x1000+rsz]
open('/root/fitparts/rootfs_extracted.bin','wb').write(d2)
PY
zstd -d -q -f kern_extracted.zst -o kern_decomp.bin 2>&1
echo -n "decompressed md5: "; md5sum kern_decomp.bin | cut -d' ' -f1
echo -n "source Image md5: "; md5sum /root/kbuild/linux-6.6.73/arch/arm64/boot/Image | cut -d' ' -f1
echo "=== rootfs first 11,274,044 bytes match original? ==="
cmp -n 11274044 rootfs_extracted.bin rootfs.squashfs && echo "ROOTFS_PREFIX_OK"
echo "=== rootfs tail is zeros? ==="
python3 -c "
d=open('/root/fitparts/rootfs_extracted.bin','rb').read()
print('total',len(d),'nonzero in pad region:',sum(1 for b in d[11274044:] if b))
"
echo
echo "=== board upgrade scripts ==="
ssh -o StrictHostKeyChecking=no root@192.168.240.1 'cat /lib/upgrade/fit.sh; echo "=== platform.sh (bpi-r4 part) ==="; grep -n -A30 "bpi-r4\|fitblk\|fit_do_upgrade" /lib/upgrade/platform.sh | head -60' 2>&1 | grep -v "WARNING\|vulnerable\|upgraded"
echo DONE
