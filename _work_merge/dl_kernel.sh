#!/bin/bash
mkdir -p /root/dl
cd /root/dl
if [ ! -s linux-6.6.73.tar.xz ]; then
  for u in \
    https://mirrors.tuna.tsinghua.edu.cn/kernel/v6.x/linux-6.6.73.tar.xz \
    https://mirrors.aliyun.com/linux-kernel/v6.x/linux-6.6.73.tar.xz \
    https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-6.6.73.tar.xz ; do
    echo "trying $u"
    curl -sL --connect-timeout 15 --max-time 1800 -o linux-6.6.73.tar.xz "$u" && [ -s linux-6.6.73.tar.xz ] && break
  done
fi
echo "=== sha256 ==="
sha256sum linux-6.6.73.tar.xz
echo "=== size ==="
ls -la linux-6.6.73.tar.xz
echo DOWNLOAD_DONE
