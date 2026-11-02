set -e
cd /root/merge
OURS="/mnt/d/Desktop/AI 辅助对话/_work_recover/openwrt-24.10.0-bpi-r4-poe-sysupgrade.itb"
ls -la "$OURS"
echo "=== dumpimage -l ==="
dumpimage -l "$OURS" 2>&1 | head -70
echo "=== extract images ==="
mkdir -p ours_fit && cd ours_fit
n=$(dumpimage -l "$OURS" 2>/dev/null | grep -c "^ Image")
echo "images=$n"
i=0
while [ $i -lt $n ]; do
  nm=$(dumpimage -l "$OURS" 2>/dev/null | grep "^ Image $i" | sed "s/.*(\(.*\))/\1/")
  echo "--- $i $nm"
  dumpimage -T flat_dt -p $i -o "$i-$nm.bin" "$OURS" >/dev/null 2>&1 || true
  i=$((i+1))
done
ls -la
echo DONE