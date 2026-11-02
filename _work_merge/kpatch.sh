BR=/root/src/openwrt-24.10.0
echo "=== generic patch dirs ==="
ls -d $BR/target/linux/generic/*/ 2>&1
echo "=== mediatek patch dirs ==="
ls -d $BR/target/linux/mediatek/*/ 2>&1
echo "=== patches touching MISSING top-level paths ==="
for p in Kconfig Kbuild certs/ init/ io_uring/ ipc/ rust/ samples/ usr/ virt/ Documentation/ MAINTAINERS; do
  n=$(grep -rl "^+++ b/$p\|^--- a/$p" $BR/target/linux/generic/*/*.patch $BR/target/linux/mediatek/*/*.patch 2>/dev/null | wc -l)
  echo "$p -> $n patches"
done
echo "=== total generic+mediatek patches ==="
ls $BR/target/linux/generic/*/*.patch 2>/dev/null | wc -l
ls $BR/target/linux/mediatek/*/*.patch 2>/dev/null | wc -l
echo "=== kernel version in buildroot ==="
grep -rn "LINUX_VERSION-6.6\|LINUX_KERNEL_HASH" $BR/include/kernel-6.6 2>/dev/null | head -5
echo "=== internet check ==="
curl -s -o /dev/null -w "%{http_code}" --max-time 10 https://cdn.kernel.org/pub/linux/kernel/v6.x/ 2>&1
echo
echo "=== openwrt sources dir ==="
curl -s -o /dev/null -w "%{http_code}" --max-time 10 https://sources.openwrt.org/linux-6.6.73.tar.xz 2>&1
echo
echo DONE