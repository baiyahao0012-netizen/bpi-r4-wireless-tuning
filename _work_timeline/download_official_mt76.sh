#!/bin/bash
# Download official kmod-mt76 ipk packages and deploy to board
set -e

BASE_URL="https://downloads.openwrt.org/releases/24.10.0/targets/mediatek/filogic/packages"
WORKDIR="/tmp/mt76-ipk"

mkdir -p $WORKDIR
cd $WORKDIR

# Download kmod-mt76 related packages
echo "Downloading kmod-mt76..."
wget -q $BASE_URL/kmod-mt76_*.ipk -O mt76.ipk
wget -q $BASE_URL/kmod-mt76-connac-lib_*.ipk -O mt76-connac-lib.ipk
wget -q $BASE_URL/kmod-mt7996e_*.ipk -O mt7996e.ipk

echo "Downloaded:"
ls -la *.ipk

# Extract ipk to get the ko files
echo "Extracting ipk..."
for f in *.ipk; do
    mkdir -p ${f%.ipk}
    tar -xzf $f -C ${f%.ipk}
done

# Find the ko files
echo "Finding ko files..."
find . -name "*.ko" | xargs ls -la

# Copy ko files to /tmp on board
echo "Copying to board..."
for ko in $(find . -name "*.ko"); do
    scp -O $ko root@192.168.240.1:/tmp/$(basename $ko)
done

echo "Done! Now run on board:"
echo "cp /tmp/mt76.ko /lib/modules/$(uname -r)/mt76.ko"
echo "cp /tmp/mt76-connac-lib.ko /lib/modules/$(uname -r)/mt76-connac-lib.ko"
echo "cp /tmp/mt7996e.ko /lib/modules/$(uname -r)/mt7996e.ko"
echo "reboot -f"
