cd /root/merge
echo "=== tools ==="
for t in dumpimage unsquashfs sqfstar dtc binwalk mksquashfs fdtget fdtgrep; do printf "%s -> " $t; command -v $t || echo MISSING; done
echo "=== apt cache? ==="
apt-cache policy u-boot-tools squashfs-tools device-tree-compiler 2>/dev/null | head -20 || true
echo "=== carve p7 ==="
if [ ! -f p7.bin ]; then dd if=sdcard.img of=p7.bin bs=1M skip=64 count=448 status=none; fi
ls -la p7.bin
echo "=== squashfs at 0x610000 in p7 ==="
python3 - <<PYEOF
import os
f=open("/root/merge/p7.bin","rb")
f.seek(0x610000)
head=f.read(96)
print(head[:64].hex())
import struct
magic,ino,mod,size,bsize,frag,comp,blog,flags,noi,fragidx,ver = struct.unpack("<IIIIHHHHHHHH", head[:32])
print("magic=%08x inodes=%d mkfs=%o blocksize=%d comp=%d ver=%d.%d" % (magic,ino,mod,bsize,comp,ver>>8,ver&0xff))
PYEOF
echo DONE