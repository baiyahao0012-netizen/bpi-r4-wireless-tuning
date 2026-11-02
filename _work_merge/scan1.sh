set -e
cd /root/merge
echo "=== GPT full ==="
sgdisk -p sdcard.img 2>&1 || fdisk -l sdcard.img 2>&1
echo "=== FIT p7 header strings ==="
dd if=sdcard.img bs=1 skip=67108864 count=4096 2>/dev/null | strings | head -40
echo "=== search magic across whole image (squashfs/gzip/cpio/ext4) ==="
python3 - <<PYEOF
import mmap
p="/root/merge/sdcard.img"
f=open(p,"rb")
m=mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ)
n=len(m)
print("image size", n)
magics={b"hsqs":"squashfs-le",b"sqsh":"squashfs-be",b"\x1f\x8b\x08":"gzip",b"070701":"cpio-newc",b"\x28\xb5\x2f\xfd":"zstd",b"\xfd7zXZ":"xz"}
for mg,name in magics.items():
    idx=[]
    start=0
    while True:
        i=m.find(mg,start)
        if i<0 or len(idx)>=12: break
        idx.append(i)
        start=i+1
    print(name, [hex(x) for x in idx])
# ext4 magic 0x53ef at offset+1080 for each 1MiB aligned candidate is too slow; skip
f.close()
PYEOF
echo DONE