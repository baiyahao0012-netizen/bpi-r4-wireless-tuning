cd /root/merge
echo "=== non-zero 4MiB block map (first 1.5GB) ==="
python3 - <<PYEOF
p="/root/merge/sdcard.img"
bs=4*1024*1024
f=open(p,"rb")
i=0
runs=[]
cur=None
import os
total=os.path.getsize(p)
limit=min(total, 2*1024*1024*1024)
while i < limit:
    b=f.read(bs)
    if not b: break
    nz=any(b)
    off=i*bs
    if nz and cur is None: cur=off
    if (not nz) and cur is not None:
        runs.append((cur, off)); cur=None
    i+=1
if cur is not None: runs.append((cur, i*bs))
for a,b in runs:
    print("nonzero %10d - %10d  (%6.1f MiB)" % (a,b,(b-a)/1048576))
PYEOF
echo "=== overlay filesystem signatures in production partition ==="
python3 - <<PYEOF
import struct
p="/root/merge/sdcard.img"
f=open(p,"rb")
# ext4 magic 0x53ef at offset+1080 within 1KiB-aligned superblocks; scan first 600MB
start=67*1024*1024; end=600*1024*1024
step=1024
found=[]
f.seek(start)
data=f.read(end-start)
idx=0
while True:
    i=data.find(b"\x53\xef", idx)
    if i<0: break
    # check plausible ext superblock: s_inodes_count>0 and s_log_block_size small
    base=(start+i) & ~0x3ff
    if base+1082 <= start+len(data):
        pass
    found.append(start+i)
    idx=i+1
    if len(found)>20: break
print("ext4-magic candidates:", [hex(x) for x in found])
for mg,name in [(b"\x19\x85","jffs2"),(b"\x10\x20\xf5\xf2","f2fs"),(b"\x45\x3f\x9a\x3d","?"),(b"hsqs","squashfs")]:
    idx=0; hits=[]
    while True:
        i=data.find(mg, idx)
        if i<0: break
        hits.append(start+i); idx=i+1
        if len(hits)>10: break
    print(name, [hex(x) for x in hits])
PYEOF
echo "=== preinit / mount_root overlay location ==="
grep -rn -E "fitrw|fit0|loop|rootfs_data" rootfs_other/lib/preinit rootfs_other/sbin/mount_root 2>/dev/null | head -40
echo DONE