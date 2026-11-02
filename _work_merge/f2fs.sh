cd /root/merge
echo "=== try f2fs module ==="
modprobe f2fs 2>&1 || echo "modprobe failed"
grep f2fs /proc/filesystems || echo "no f2fs in /proc/filesystems"
ls /lib/modules/$(uname -r)/kernel/fs/ 2>/dev/null | head
echo "=== install f2fs-tools ==="
export DEBIAN_FRONTEND=noninteractive
apt-get install -y -qq f2fs-tools > /tmp/f2fs.log 2>&1 && echo APT_OK || (echo APT_FAIL; tail -5 /tmp/f2fs.log)
for t in dump.f2fs fsck.f2fs mkfs.f2fs; do printf "%s -> " $t; command -v $t || echo MISSING; done
echo "=== extract overlay f2fs region ==="
python3 - <<PYEOF
import os
p="/root/merge/sdcard.img"
base=0x50A0000
size=(0x20000000-base)  # to end of production partition
f=open(p,"rb"); f.seek(base)
data=f.read(size)
open("/root/merge/overlay_f2fs.img","wb").write(data)
print("wrote", len(data), "bytes from", hex(base))
# trim trailing 0xFF
trim=len(data)
while trim>0 and data[trim-1]==0xFF: trim-=1
print("last non-0xFF byte at", hex(base+trim))
open("/root/merge/overlay_f2fs_trim.img","wb").write(data[:trim+1])
PYEOF
ls -la overlay_f2fs*.img
echo "=== dump.f2fs superblock ==="
dump.f2fs -s 0 overlay_f2fs_trim.img 2>&1 | head -60
echo DONE