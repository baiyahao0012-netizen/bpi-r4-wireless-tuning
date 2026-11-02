#!/bin/bash
BR=/root/src/openwrt-24.10.0
echo "=== find Kernel/Patch definitions ==="
grep -rn "Kernel/Patch" $BR/include/*.mk 2>/dev/null | head -20
echo "=== kernel-defaults.mk patch section ==="
grep -n "Patch" $BR/include/kernel-defaults.mk 2>/dev/null | head -20
echo "=== kernel-build.mk patch section ==="
grep -n "Patch" $BR/include/kernel-build.mk 2>/dev/null | head -20
echo "=== PATCH_DIR / patch commands ==="
grep -rn "patch -p1\|PATCH_DIR\|PATCHES" $BR/include/kernel-defaults.mk $BR/include/kernel-build.mk 2>/dev/null | head -20
echo DONE
