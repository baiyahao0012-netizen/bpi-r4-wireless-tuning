#!/bin/bash
B=/root/uboot/sd_first70m.bin
echo "=== all '*ERROR*' strings near image loading ==="
strings -a -n 6 $B | grep -iE "ERROR|must RESET|not loaded|Unsupported" | sort -u | head -40
echo
echo "=== compressor name strings ==="
strings -a -n 5 $B | grep -E "^(gzip|bzip2|lzma|lzo|lz4|zstd|none) compressed" | sort -u
echo
echo "=== 'image not loaded' variants ==="
strings -a -n 6 $B | grep -E "image not loaded|image not (loaded|found)" | sort -u
echo
echo "=== zstd lib limits ==="
strings -a -n 6 $B | grep -iE "zstd.*(window|workspace|size)|ZSTD_|windowLog" | sort -u | head -20
echo DONE
