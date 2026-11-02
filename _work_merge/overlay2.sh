cd /root/merge
echo "=== grep fitrw/f2fs/ext4 in other rootfs ==="
grep -rl "fitrw" rootfs_other 2>/dev/null | head -20
echo "--- f2fs ---"
grep -rl "f2fs" rootfs_other 2>/dev/null | head -20
echo "--- mkfs mentions in preinit/mount_root ---"
grep -rn -E "mkfs|fitrw|rootfs_data|loop" rootfs_other/lib/preinit/ rootfs_other/etc/preinit rootfs_other/lib/functions/*.sh 2>/dev/null | head -40
echo "=== list preinit ==="
ls rootfs_other/lib/preinit/
echo "=== hexdump around fitrw start ==="
python3 - <<PYEOF
p="/root/merge/sdcard.img"
f=open(p,"rb")
for off in [0x509F000, 0x50A0000, 0x50A0400, 0x50A1400, 0x50B0000, 0x5100000]:
    f.seek(off); b=f.read(48)
    print(hex(off), b.hex())
PYEOF
echo "=== non-zero 256KB map 0x4000000-0x20000000 ==="
python3 - <<PYEOF
p="/root/merge/sdcard.img"
f=open(p,"rb")
bs=256*1024
start=0x4000000; end=0x20000000
f.seek(start)
runs=[]; cur=None
off=start
while off<end:
    b=f.read(bs)
    if not b: break
    nz=any(b)
    if nz and cur is None: cur=off
    if (not nz) and cur is not None: runs.append((cur,off)); cur=None
    off+=len(b)
if cur is not None: runs.append((cur,off))
print("runs:", len(runs))
for a,b in runs[:60]: print("  %#x - %#x  (%.1f MiB)" % (a,b,(b-a)/1048576))
PYEOF
echo DONE