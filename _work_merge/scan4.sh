cd /root/merge
echo "=== sample bytes in production partition after FIT ==="
python3 - <<PYEOF
p="/root/merge/sdcard.img"
f=open(p,"rb")
for off in [0x4000000, 0x4010000, 0x4100000, 0x4610000, 0x4700000, 0x4800000, 0x5000000, 0x6000000, 0x8000000, 0x10000000, 0x20000000, 0x40000000, 0x80000000, 0x180000000, 0x1D0000000]:
    f.seek(off)
    b=f.read(64)
    print(hex(off), b[:32].hex(), "|", "".join(chr(c) if 32<=c<127 else "." for c in b[:32]))
PYEOF
echo "=== unique byte histogram in 0x4800000-0x4C00000 ==="
python3 - <<PYEOF
p="/root/merge/sdcard.img"
f=open(p,"rb"); f.seek(0x4800000); d=f.read(4*1024*1024)
from collections import Counter
c=Counter(d)
print("distinct bytes:", len(c), "top5:", c.most_common(5))
PYEOF
echo "=== tail of image ==="
python3 - <<PYEOF
import os
p="/root/merge/sdcard.img"
s=os.path.getsize(p)
f=open(p,"rb"); f.seek(s-64); print(hex(s-64), f.read(64).hex())
PYEOF
echo "=== FIT configurations ==="
dumpimage -l p7.bin 2>&1 | sed -n "/Configuration/,$p" | head -30
echo "=== our FIT configurations ==="
dumpimage -l "/mnt/d/Desktop/AI 辅助对话/_work_recover/openwrt-24.10.0-bpi-r4-poe-sysupgrade.itb" 2>&1 | sed -n "/Configuration/,$p" | head -30
echo DONE