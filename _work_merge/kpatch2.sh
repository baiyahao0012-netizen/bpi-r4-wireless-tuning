BR=/root/src/openwrt-24.10.0
echo "=== KPATCH definition ==="
grep -rn "KPATCH" $BR/include/*.mk 2>/dev/null | head -10
echo "=== patch-kernel.sh ==="
cat $BR/scripts/patch-kernel.sh 2>&1
echo "=== patch dirs and counts ==="
for d in generic/backport-6.6 generic/pending-6.6 generic/hack-6.6; do
  echo "$d: $(ls $BR/target/linux/$d/*.patch 2>/dev/null | wc -l) patches; series=$(test -f $BR/target/linux/$d/series && echo yes || echo no)"
done
echo "mediatek/patches-6.6: $(ls $BR/target/linux/mediatek/patches-6.6/*.patch 2>/dev/null | wc -l) patches"
echo "=== files dirs ==="
ls -d $BR/target/linux/generic/files $BR/target/linux/mediatek/files* 2>&1
echo "=== first/last patch names in each dir ==="
for d in generic/backport-6.6 generic/pending-6.6 generic/hack-6.6 mediatek/patches-6.6; do
  echo "--- $d ---"; ls $BR/target/linux/$d/ 2>/dev/null | sort | head -2; echo "  ..."; ls $BR/target/linux/$d/ 2>/dev/null | sort | tail -2
done
echo DONE