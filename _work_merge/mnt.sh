cd /root/merge
python3 - <<PYEOF
p="/root/merge/sdcard.img"
base=0x509F000
end=0x20000000
f=open(p,"rb"); f.seek(base); data=f.read(end-base)
open("/root/merge/overlay.img","wb").write(data)
print("wrote", len(data), "from", hex(base))
# trim trailing 0xFF for a smaller copy
t=len(data)
while t>0 and data[t-1]==0xFF: t-=1
print("last non-0xFF at", hex(base+t))
PYEOF
ls -la overlay.img
echo "=== fsck dry ==="
fsck.f2fs -f -d 0 overlay.img 2>&1 | head -30 || true
echo "=== mount ==="
mkdir -p /root/merge/ovl
mount -t f2fs -o ro,loop overlay.img /root/merge/ovl 2>&1 && echo MOUNT_OK || echo MOUNT_FAIL
echo "=== list overlay ==="
ls -la /root/merge/ovl 2>&1 | head -30
echo "=== upper ==="
ls -la /root/merge/ovl/upper 2>&1 | head -40
echo "=== work ==="
ls -la /root/merge/ovl/work 2>&1 | head -10
echo DONE