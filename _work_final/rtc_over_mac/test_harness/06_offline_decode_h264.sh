#!/bin/bash
# =============================================================================
# 06_offline_decode_h264.sh — 离线解码 AP 落盘的 rx.h264，数帧数、算帧完整率
#
# 跑在哪：树莓派 5（ffmpeg 7.1.5 已装）；也可在 PC 上用便携 ffmpeg 跑。
# 目的：AP 只落盘不解码；把 rx.h264 取回 Pi，离线解码数帧，
#       与源片帧数对比，算"帧完整率"（最核心的质量指标）。
#
# 帧完整率 = 成功解码帧数 / 源片总帧数
#   注意：0.1% 包丢失在 20 Mbps 下会放大成约 6.8% 整帧废弃，
#   所以"包收到了"不等于"帧完整"，必须按帧统计。
# =============================================================================

set -u
cd /home/bai/rtc_test || exit 1

SRC=1080p30_1_artemis_origins_85s.mp4     # 源片
RX=/tmp/rx.h264                            # AP 落盘文件（先 scp 回来）

# --- 1. 从 AP 取回落盘文件 ---------------------------------------------------
# AP 免密 root@192.168.240.1；rx.h264 是 05 脚本写出的原始 H.264。
echo "===== 1. fetch $RX from AP ====="
scp -o BatchMode=yes root@192.168.240.1:$RX /home/bai/rtc_test/rx.h264 || {
  echo "ERROR: 取 rx.h264 失败；先确认 AP 上 05 接收端在跑且文件非空。"
  exit 1
}
RX=/home/bai/rtc_test/rx.h264
ls -lh "$RX"

# --- 2. 数源片帧数 -----------------------------------------------------------
# nb_frames 是容器里写好的总帧数；对 MP4 通常可信，先取它。
echo "===== 2. source frames ====="
SRC_FRAMES=$(ffprobe -v error -select_streams v:0 \
  -show_entries stream=nb_frames -of csv=p=0 "$SRC")
echo "source: $SRC_FRAMES frames"

# --- 3. 解码 rx.h264 逐帧数帧 ----------------------------------------------
# -count_frames 要求逐帧解码才计数（nb_read_frames）；
# 这一步同时暴露解码错误：缺 NAL、坏帧会在 stderr 里报。
echo "===== 3. decode & count received frames ====="
RX_FRAMES=$(ffprobe -v error -count_frames -select_streams v:0 \
  -show_entries stream=nb_read_frames -of csv=p=0 "$RX")
echo "received decoded: $RX_FRAMES frames"

# --- 4. 帧完整率 ------------------------------------------------------------
# 纯 bash 算浮点不方便，用 python3 做除法，输出百分比。
echo "===== 4. completeness ====="
python3 - <<PY
src = int("$SRC_FRAMES") if "$SRC_FRAMES" else 0
rx  = int("$RX_FRAMES")  if "$RX_FRAMES"  else 0
if src == 0:
    print("ERROR: 源片帧数为 0，无法计算")
else:
    rate = rx / src * 100
    print(f"source={src}  decoded={rx}  frame_completeness={rate:.2f}%")
    if rx > src:
        print("WARN: 解码帧数多于源片，检查是否混入上一轮残留文件。")
PY

# --- 5. （后续）画质对比 -----------------------------------------------------
# 基线阶段先保证帧完整率；M6 矩阵阶段再做 PSNR/SSIM/VMAF：
#   ffmpeg -i "$SRC" -i "$RX" -filter_complex "[0:v][1:v]psnr" -f null -
# 注意：两路分辨率/帧率/GOP 必须一致，否则画质指标不可比。

# -----------------------------------------------------------------------------
# 常见问题排查：
#   - ffprobe 报 non-existing PPS / missing SPS：发送侧 config-interval=1
#     是否带了配置帧；或落盘流被截断（timeout 收尾时 EOS 没回填）。
#   - 解码帧数明显偏少：先看 AP 落盘文件大小是否 ≈ 源视频码率 × 时长；
#     再回 04 脚本核对四条硬证据，确认走的是无线而不是有线。
# -----------------------------------------------------------------------------
