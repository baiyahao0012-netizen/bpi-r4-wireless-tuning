cd /root/merge
echo "=== wsl filesystems ==="
grep -E "f2fs|ext4|jffs2|squashfs" /proc/filesystems
echo "=== tools ==="
for t in mkfs.f2fs fsck.f2fs dump.f2fs; do printf "%s -> " $t; command -v $t || echo MISSING; done
echo "=== carve overlay candidate ==="
if [ ! -f overlay.bin ]; then dd if=sdcard.img of=overlay.bin bs=1M skip=80 count=512 status=none; fi
ls -la overlay.bin
python3 - <<PYEOF
p="/root/merge/sdcard.img"
f=open(p,"rb")
f.seek(0x509F000)
b=f.read(4096)
print("at 0x509F000:", b[:32].hex())
print("sb @+0x400:", b[0x400:0x400+32].hex())
import struct
magic = b[0x400:0x404]
print("magic", magic.hex())
if magic == b"\x10\x20\xf5\xf2":
    major,minor = struct.unpack("<HH", b[0x404:0x408])
    vals = struct.unpack("<IIIII", b[0x408:0x41C])
    print("f2fs major=%d minor=%d vals=%s" % (major,minor,vals))
PYEOF
echo DONE