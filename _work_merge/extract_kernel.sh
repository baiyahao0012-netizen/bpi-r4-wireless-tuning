#!/bin/bash
mkdir -p /root/kbuild
cd /root/kbuild
if [ ! -d linux-6.6.73 ]; then
  tar -xf /root/dl/linux-6.6.73.tar.xz
fi
echo "=== extracted ==="
ls -d /root/kbuild/linux-6.6.73
find /root/kbuild/linux-6.6.73 -type f | wc -l
echo EXTRACT_DONE
