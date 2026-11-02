SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
echo "=== SDK bison ==="
ls -la $SDK/staging_dir/host/bin/bison 2>&1
echo "=== SDK bison share dir ==="
ls $SDK/staging_dir/host/share/bison/ 2>&1
ls $SDK/staging_dir/host/share/bison/m4sugar/ 2>&1 | head
echo "=== system bison ==="
which bison; bison --version 2>&1 | head -1
echo "=== system flex ==="
which flex; flex --version 2>&1 | head -1
echo "=== does /builder exist? ==="
ls -d /builder 2>&1
echo "=== other host tools with hardcoded /builder? ==="
for t in bison flex pahole dtc m4; do
  b=$SDK/staging_dir/host/bin/$t
  [ -f "$b" ] && echo "$t: $(strings $b 2>/dev/null | grep -c "/builder")"
done
echo DONE