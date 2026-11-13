#!/bin/bash
# debug8.sh — T3 缺帧归因：源片与接收端 YUV 320x180 首/尾帧哈希对比
set -u
cd /home/bai/rtc_test
OUT=/tmp/l0
PF=86400

ffmpeg -y -v error -i clip10.mp4 -vf scale=320:180 -pix_fmt yuv420p "$OUT/src320.yuv"
SRC_SZ=$(stat -c%s "$OUT/src320.yuv")
RX_SZ=$(stat -c%s "$OUT/rx.yuv")
echo "src_bytes=$SRC_SZ src_frames=$((SRC_SZ/PF))"
echo "rx_bytes=$RX_SZ rx_frames=$((RX_SZ/PF))"

# 首帧哈希
head -c "$PF" "$OUT/src320.yuv" | md5sum | sed 's/^/src_frame0=/'
head -c "$PF" "$OUT/rx.yuv" | md5sum | sed 's/^/rx_frame0=/'

# 源片最后一帧（第 302 帧，偏移 (302-1)*PF）
SRC_LAST_OFF=$(((302-1)*PF))
tail -c +$((SRC_LAST_OFF+1)) "$OUT/src320.yuv" | head -c "$PF" | md5sum | sed 's/^/src_last=/'
# 接收端最后一帧（第 300 帧）
RX_LAST_OFF=$(((300-1)*PF))
tail -c +$((RX_LAST_OFF+1)) "$OUT/rx.yuv" | head -c "$PF" | md5sum | sed 's/^/rx_last=/'

# 源片第 300 帧（与接收端最后一帧同位对比）
SRC_300_OFF=$(((300-1)*PF))
tail -c +$((SRC_300_OFF+1)) "$OUT/src320.yuv" | head -c "$PF" | md5sum | sed 's/^/src_frame300=/'
