#!/bin/bash
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
echo "=== U-Boot FIT-loader error strings ==="
strings -a -n 6 /root/uboot/sd_first70m.bin 2>/dev/null | grep -E "ERROR %d - image not loaded|image not loaded" | sort -u
echo "=== decompressor mentions ==="
strings -a -n 5 /root/uboot/sd_first70m.bin 2>/dev/null | grep -iE "zstd|lzma|gzip" | sort -u | head -25
echo
echo "=== squashfs info ==="
which unsquashfs mksquashfs 2>&1
unsquashfs -s /root/fitparts/rootfs.squashfs 2>&1 | head -20
echo "=== squashfs superblock (manual) ==="
python3 -c "
import struct
d=open('/root/fitparts/rootfs.squashfs','rb').read(96)
magic, inodes, mkfs_time, block_size, fragments, compression, block_log, flags, no_ids, s_major, s_minor, root_inode, bytes_used, id_table_start, xattr_id_table_start, inode_table_start, directory_table_start, fragment_table_start, lookup_table_start = struct.unpack('<IIIIHHHHHHQQQQQQQQ', d)
print('magic=%08x inodes=%d block_size=%d compression=%d bytes_used=%d' % (magic, inodes, block_size, compression, bytes_used))
print('compression name:', {1:'gzip',2:'lzma',3:'lzo',4:'xz',5:'lz4',6:'zstd'}.get(compression,'?'))
print('filesystem size on disk (bytes_used):', bytes_used)
"
echo "=== mkimage zstd/lzma support test ==="
cd /root/fitparts
head -c 100000 /dev/urandom > t.bin
zstd -19 -q -c t.bin > t.zst 2>/dev/null
$SDK/staging_dir/host/bin/mkimage -f /dev/null /dev/null 2>&1 | head -2
echo "mkimage -C support:"
$SDK/staging_dir/host/bin/mkimage 2>&1 | head -30
echo DONE
