#!/bin/bash
BR=/root/src/openwrt-24.10.0
echo "--- buildroot package ---"
ls -la $BR/package/kernel/gpio-button-hotplug/ 2>&1
echo "--- source ---"
head -30 $BR/package/kernel/gpio-button-hotplug/src/Makefile 2>&1
echo "--- find any built ko in buildroot ---"
find $BR -name "gpio-button-hotplug.ko" 2>/dev/null | head
echo DONE
