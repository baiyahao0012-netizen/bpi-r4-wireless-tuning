#!/bin/bash
# =============================================================================
# run_l0.sh — L0 本地回环媒体层验证（127.0.0.1，不碰无线网络）
#
# 跑在哪：树莓派 5（RPI-5）
# 被测对象：GStreamer 开源元件组装的媒体层；本脚本只做编排与记录。
#
# 验证分层：
#   字段级：RTP 头版本/PT/序号/SSRC/时间戳（rtp_probe）
#   帧级  ：接收端拆包→解码→降采样写 YUV，按每帧字节数反算帧数，与源片对账
#   功能级：rtpbin RTCP SR；jitterbuffer 链接；NACK/PLI/RTX、SRTP 加解密、
#           音画偏差、PSNR 在本地无丢包/无锚点条件下验不了，按计划延后。
#
# 结果写 /tmp/l0/results.env（KEY=VALUE），日志在 /tmp/l0/*.err。
# =============================================================================

set -u

DIR="$(cd "$(dirname "$0")" && pwd)"
cd /home/bai/rtc_test || exit 1

SRC=1080p30_1_artemis_origins_85s.mp4
CLIP=clip10.mp4
OUT=/tmp/l0
mkdir -p "$OUT"
RES="$OUT/results.env"
: > "$RES"

# 视频 RTP caps（接收端 udpsrc 必须显式给出，depayloader 才能协商格式）
VCAPS="application/x-rtp,media=video,clock-rate=90000,encoding-name=H264,pt=96"
# 降采样对账参数：320x180 I420，每帧字节数 = 宽×高×3/2
RW=320; RH=180; RPER=$((RW*RH*3/2))

put() { echo "$1=$2" >> "$RES"; }

echo "[L0] ==== 0. 环境信息 ===="
put HOST "$(hostname)"
put DATE "$(date '+%F %T')"
put GST_VERSION "$(gst-launch-1.0 --version | head -1)"

# -----------------------------------------------------------------------------
# 准备 10 秒片段（流复制，不重编码）；源帧数以 ffprobe 计数为准
# -----------------------------------------------------------------------------
if [ ! -f "$CLIP" ]; then
    ffmpeg -y -t 10 -i "$SRC" -c copy "$CLIP" >"$OUT/clip.log" 2>&1
fi
CLIP_FRAMES=$(ffprobe -v error -count_frames -select_streams v:0 \
    -show_entries stream=nb_read_frames \
    -of default=noprint_wrappers=1:nokey=1 "$CLIP")
CLIP_RES=$(ffprobe -v error -select_streams v:0 \
    -show_entries stream=width,height -of csv=p=0 "$CLIP")
put CLIP_FRAMES "$CLIP_FRAMES"
put CLIP_RES "$CLIP_RES"
echo "[L0] 片段帧数=$CLIP_FRAMES 分辨率=$CLIP_RES"

# =============================================================================
# T1 解封装 + 解码（帧级：解码管线跑完、解码器无报错；帧数参照=源片 ffprobe 302）
# 管线：filesrc ! qtdemux ! h264parse ! avdec_h264 ! fakesink
# =============================================================================
echo "[L0] ==== T1 解封装+解码 ===="
timeout 30 gst-launch-1.0 -q filesrc location="$CLIP" ! qtdemux ! h264parse ! \
    avdec_h264 ! fakesink sync=false 2>"$OUT/t1.err"
T1_RC=$?
put T1_GST_RC "$T1_RC"

# 参照解码：ffmpeg -f null，统计帧数与错误行
ffmpeg -i "$CLIP" -an -f null - 2>"$OUT/t1_ff.log"
T1_FF_FRAMES=$(grep -oE 'frame=[ ]*[0-9]+' "$OUT/t1_ff.log" | tail -1 | grep -oE '[0-9]+')
put T1_FF_REF_FRAMES "${T1_FF_FRAMES:-NA}"
T1_ERR=$(grep -icE 'error|fail|corrupt|wrong' "$OUT/t1.err" || true)
put T1_DECODER_ERRORS "$T1_ERR"
echo "[L0] T1 gst_rc=$T1_RC ffmpeg_ref=${T1_FF_FRAMES:-NA} decoder_err_lines=$T1_ERR"

# =============================================================================
# T2 视频 RTP 打包（字段级：探针拆头统计）
# =============================================================================
echo "[L0] ==== T2 视频 RTP 头字段 ===="
python3 "$DIR/rtp_probe.py" 5004 14 >"$OUT/t2.json" 2>"$OUT/t2.err" &
PP=$!
sleep 1
timeout 12 gst-launch-1.0 -q -e filesrc location="$CLIP" ! qtdemux ! h264parse ! \
    rtph264pay config-interval=1 pt=96 ! udpsink host=127.0.0.1 port=5004 sync=true \
    2>"$OUT/t2.gst.err"
T2_RC=$?
wait "$PP" 2>/dev/null || true
put T2_GST_RC "$T2_RC"
python3 - "$OUT/t2.json" "$RES" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
with open(sys.argv[2], "a") as f:
    f.write("T2_PACKETS=%d\n" % d["packets"])
    f.write("T2_SEQ_GAPS=%d\n" % d["seq_gaps"])
    f.write("T2_SSRCS=%s\n" % ",".join(str(x) for x in d["ssrcs"]))
    f.write("T2_TIMESTAMPS=%d\n" % d["timestamps"])
    f.write("T2_PT=%s\n" % (d["first"][3] if d["first"] else "NA"))
print("T2 packets=%d gaps=%d ssrcs=%s ts=%s pt=%s" % (
    d["packets"], d["seq_gaps"], d["ssrcs"], d["timestamps"],
    (d["first"][3] if d["first"] else None)))
PY

# =============================================================================
# T3 回环拆包重组 + 解码对账（帧级闭环）
# 接收：udpsrc(显式 caps) ! queue ! jitterbuffer ! depay ! h264parse !
#       avdec_h264 ! videoscale ! videoconvert ! I420 320x180 ! filesink rx.yuv
# 帧数对账：rx.yuv 字节数 / 每帧字节数 = 解码帧数，与源片帧数比较
# =============================================================================
echo "[L0] ==== T3 回环拆包重组 + 解码对账 ===="
pkill -f gst-launch 2>/dev/null; sleep 1
rm -f "$OUT/rx.yuv"
timeout 22 gst-launch-1.0 -q \
    udpsrc port=5014 caps="$VCAPS" ! queue ! rtpjitterbuffer ! rtph264depay ! \
    h264parse ! avdec_h264 ! videoscale ! videoconvert ! \
    video/x-raw,format=I420,width=$RW,height=$RH ! filesink location="$OUT/rx.yuv" \
    2>"$OUT/t3.recv.err" &
RP=$!
sleep 2
timeout 12 gst-launch-1.0 -q -e filesrc location="$CLIP" ! qtdemux ! h264parse ! \
    rtph264pay config-interval=1 pt=96 ! udpsink host=127.0.0.1 port=5014 sync=true \
    2>"$OUT/t3.send.err"
T3_SEND_RC=$?
wait "$RP" 2>/dev/null; T3_RECV_RC=$?
put T3_SEND_RC "$T3_SEND_RC"
put T3_RECV_RC "$T3_RECV_RC"

T3_SZ=$(stat -c%s "$OUT/rx.yuv" 2>/dev/null || echo 0)
T3_RX_FRAMES=$((T3_SZ / RPER))
put T3_RX_BYTES "$T3_SZ"
put T3_RX_FRAMES "$T3_RX_FRAMES"
put T3_PER_FRAME "$RPER"
T3_ERR=$(grep -icE 'error|fail|corrupt|wrong|non-existing' "$OUT/t3.recv.err" "$OUT/t3.send.err" || true)
put T3_PIPELINE_ERRORS "$T3_ERR"
echo "[L0] T3 send_rc=$T3_SEND_RC recv_rc=$T3_RECV_RC rx_frames=$T3_RX_FRAMES/$CLIP_FRAMES err=$T3_ERR"

# =============================================================================
# T4 SRTP 加解密
# L0 现状：srtpenc 有 key 属性；srtpdec 只能经 request-key 信号喂密钥，
#           gst-launch 无法连接回调；Python GStreamer typelib 未装。
#           功能闭环按 M2 计划补（PSK + 代码级管线）。此处只登记元件可用性。
# =============================================================================
echo "[L0] ==== T4 SRTP 元件可用性 ===="
put T4_SRTPENC_PRESENT "$(gst-inspect-1.0 srtpenc >/dev/null 2>&1 && echo yes || echo no)"
put T4_SRTPDEC_PRESENT "$(gst-inspect-1.0 srtpdec >/dev/null 2>&1 && echo yes || echo no)"
put T4_STATUS "DEFERRED-M2: srtpdec 经 request-key 信号供钥，需代码级管线；本地未跑加解密闭环"

# =============================================================================
# T5 rtpbin RTCP SR（功能级：RTCP 通道开启且发出 SR）
# 官方写法：面板名带会话序号 _0；send_rtp_sink_0 进，send_rtp_src_0 出 RTP，
#           send_rtcp_src_0 出 RTCP；RTCP udpsink 配 sync=false async=false。
# RTCP PT：200=SR, 201=RR, 205=RTPFB(NACK), 206=PSFB(PLI)
# =============================================================================
echo "[L0] ==== T5 rtpbin RTCP SR ===="
pkill -f gst-launch 2>/dev/null; sleep 1
python3 "$DIR/rtcp_probe.py" 5035 16 >"$OUT/t5.json" 2>"$OUT/t5.err" &
CP=$!
sleep 1
timeout 14 gst-launch-1.0 -q -e rtpbin name=R \
    filesrc location="$CLIP" ! qtdemux ! h264parse ! \
    rtph264pay config-interval=1 pt=96 ! R.send_rtp_sink_0 \
    R.send_rtp_src_0 ! udpsink host=127.0.0.1 port=5034 \
    R.send_rtcp_src_0 ! udpsink host=127.0.0.1 port=5035 sync=false async=false \
    2>"$OUT/t5.gst.err"
T5_RC=$?
wait "$CP" 2>/dev/null || true
put T5_GST_RC "$T5_RC"
python3 - "$OUT/t5.json" "$RES" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
with open(sys.argv[2], "a") as f:
    f.write("T5_RTCP_PACKETS=%d\n" % d["packets"])
    f.write("T5_RTCP_PT=%s\n" % json.dumps(d["pt_counts"]))
print("T5 rtcp_packets=%d pt=%s" % (d["packets"], d["pt_counts"]))
PY
T5_ERR=$(grep -icE 'error|fail|corrupt|wrong' "$OUT/t5.gst.err" || true)
put T5_PIPELINE_ERRORS "$T5_ERR"

# =============================================================================
# T6 抖动缓冲（jitterbuffer）
# 本地回环无抖动/无乱序，只能验证：元件可链接进管线（T3 已走该元件）、
# 关键属性在位。乱序/丢包缓冲行为留到 L1 注入乱序后验。
# =============================================================================
echo "[L0] ==== T6 jitterbuffer 链接与属性 ===="
put T6_JB_PRESENT "$(gst-inspect-1.0 rtpjitterbuffer >/dev/null 2>&1 && echo yes || echo no)"
put T6_JB_LATENCY_PROP "$(gst-inspect-1.0 rtpjitterbuffer 2>/dev/null | grep -c 'latency')"
put T6_JB_MODE_PROP "$(gst-inspect-1.0 rtpjitterbuffer 2>/dev/null | grep -c 'mode')"
put T6_STATUS "LINKED-OK (T3 管线经 jitterbuffer)；乱序/丢包缓冲行为 DEFERRED-L1"

# =============================================================================
# T7 NACK / PLI / RTX 能力登记
# 本地无丢包，无法触发反馈；只确认 rtpbin/jitterbuffer 重传相关属性在位。
# 丢包恢复闭环留到 M5（注入 0.01/0.1/0.5% 丢包）。
# =============================================================================
echo "[L0] ==== T7 NACK/PLI/RTX 属性登记 ===="
put T7_RTPBIN_RETX "$(gst-inspect-1.0 rtpbin 2>/dev/null | grep -c 'do-retransmission')"
put T7_JB_RETX "$(gst-inspect-1.0 rtpjitterbuffer 2>/dev/null | grep -c 'do-retransmission')"
put T7_JB_RTX_PROPS "$(gst-inspect-1.0 rtpjitterbuffer 2>/dev/null | grep -c 'rtx-')"
put T7_STATUS "PROPS-PRESENT；丢包恢复闭环 DEFERRED-M5"

# =============================================================================
# T8 音频 Opus RTP（字段级：PT=111，独立 SSRC）
# 音画同步偏差需锚点素材（未部署到 Pi），留 M2 测。
# =============================================================================
echo "[L0] ==== T8 音频 Opus RTP ===="
pkill -f gst-launch 2>/dev/null; sleep 1
python3 "$DIR/rtp_probe.py" 5006 12 >"$OUT/t8.json" 2>"$OUT/t8.err" &
AP=$!
sleep 1
timeout 10 gst-launch-1.0 -q -e filesrc location="$CLIP" ! qtdemux ! aacparse ! \
    avdec_aac ! audioconvert ! audioresample ! opusenc ! \
    rtpopuspay pt=111 ! udpsink host=127.0.0.1 port=5006 sync=true \
    2>"$OUT/t8.gst.err"
T8_RC=$?
wait "$AP" 2>/dev/null || true
put T8_GST_RC "$T8_RC"
python3 - "$OUT/t8.json" "$RES" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
with open(sys.argv[2], "a") as f:
    f.write("T8_PACKETS=%d\n" % d["packets"])
    f.write("T8_SEQ_GAPS=%d\n" % d["seq_gaps"])
    f.write("T8_SSRCS=%s\n" % ",".join(str(x) for x in d["ssrcs"]))
    f.write("T8_PT=%s\n" % (d["first"][3] if d["first"] else "NA"))
print("T8 packets=%d gaps=%d ssrcs=%s pt=%s" % (
    d["packets"], d["seq_gaps"], d["ssrcs"],
    (d["first"][3] if d["first"] else None)))
PY
put T8_STATUS "SYNC-SKEW DEFERRED-M2（锚点素材未部署）"

# =============================================================================
# T9 画质（PSNR/SSIM）
# 本地回环无损伤，PSNR 对比无意义；画质指标留到 L1 baseline 与 L2 差分。
# =============================================================================
put T9_STATUS "PSNR/SSIM DEFERRED-L1（本地回环无损伤，不构成画质对照）"

echo "[L0] ==== 结果汇总 ===="
cat "$RES"
echo "[L0] 完成。日志目录：$OUT"
