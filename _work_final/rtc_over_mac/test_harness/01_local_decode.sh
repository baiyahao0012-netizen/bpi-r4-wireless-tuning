#!/bin/bash
# =============================================================================
# 01_local_decode.sh  —  本地媒体层功能测试（不碰网络）
#
# 跑在哪：树莓派 5（RPI-5）
# 目的：在本机 127.0.0.1 层面证明 GStreamer 的解码 / RTP 打包 / 音频转换是好的。
#       这一步所有输出都用 fakesink 丢弃，只看退出码 rc，不存文件。
#
# 为什么先测本地：先把"软件问题"和"网络问题"彻底分开。
#       本地都跑不通，后面上无线一定是软件问题；本地通了，上无线再出问题才往链路查。
#
# 被测对象：GStreamer 现成元件（开源媒体层）
# 本脚本角色：流程编排（按顺序起管线、记退出码、统计 PASS/FAIL）
# =============================================================================

set -u                                  # 引用未定义变量直接报错，避免空参数悄悄跑错
cd /home/bai/rtc_test || exit 1         # 脚本与素材在同一目录；进不去就退出

# 测试素材：1080p30，H.264 + AAC 立体声
F=1080p30_1_artemis_origins_85s.mp4

PASS=0
FAIL=0

# 打印分节标题的小函数
section() { echo; echo "===== $* ====="; }

# -----------------------------------------------------------------------------
# 0. 环境信息：记录主机名、时间、GStreamer 版本、素材大小
#    这些信息进日志，后面出问题时用来核对环境是否一致。
# -----------------------------------------------------------------------------
section "0. Environment"
hostname
date
gst-launch-1.0 --version | head -2
ls -lh "$F"

# -----------------------------------------------------------------------------
# 1. H.264 解码测试
#
# 管线：
#   filesrc      读 MP4 文件字节
#   qtdemux      解封装 MP4，拆出视频轨（不解码）
#   h264parse    整理 H.264 NAL 单元序列
#   avdec_h264   解码成 YUV 原始画面
#   fakesink     画面直接丢弃（不显示、不落盘）
#
# sync=false：fakesink 不需要按时钟同步，尽快跑完即可。
# timeout 90：最多跑 90 秒，防止管线卡死把脚本挂住。
# 判据：rc=0 即解码管线正常。
# -----------------------------------------------------------------------------
section "1. H.264 decode (85 s clip, fakesink)"
t0=$(date +%s)
timeout 90 gst-launch-1.0 -q filesrc location="$F" ! qtdemux ! h264parse ! avdec_h264 ! fakesink sync=false
rc=$?
t1=$(date +%s)
echo "decode_rc=$rc elapsed=$((t1-t0))s"
[ "$rc" -eq 0 ] && PASS=$((PASS+1)) || FAIL=$((FAIL+1))

# -----------------------------------------------------------------------------
# 2. H.264 RTP 打包测试
#
# 管线：
#   filesrc → qtdemux → h264parse
#   rtph264pay   把 H.264 NAL 打成 RTP 包（RFC 6184）
#                pt=96        动态载荷类型号（接收侧要对上）
#                config-interval=1  每隔 1 个关键帧带一次 SPS/PPS 配置
#   fakesink     RTP 包直接丢弃（这一步只验证"能打成 RTP"，不发网络）
#
# -e：管线收到 EOS（文件读完）时正常结束。
# -----------------------------------------------------------------------------
section "2. H.264 RTP packetization"
timeout 90 gst-launch-1.0 -q -e filesrc location="$F" ! qtdemux ! h264parse ! rtph264pay config-interval=1 pt=96 ! fakesink sync=false
rc=$?
echo "h264_rtp_rc=$rc"
[ "$rc" -eq 0 ] && PASS=$((PASS+1)) || FAIL=$((FAIL+1))

# -----------------------------------------------------------------------------
# 3. AAC 解码 → Opus 编码 → Opus RTP 打包测试
#
# 管线：
#   aacparse       解析 AAC 帧
#   avdec_aac      AAC 解码成 PCM
#   audioconvert   采样格式/声道转换到编码器要求
#   audioresample  重采样到 48 kHz
#   opusenc        PCM → Opus
#   rtpopuspay     Opus 打成 RTP（RFC 7587），pt=111
#
# 为什么音频要转 Opus：Opus 是 RTC 标准音频编码（RFC 6716），
#   延迟低（端到端 15–30 ms）、RTP 封装简单、内置 FEC/PLC；
#   AAC 延迟高、RFC 3640 封装参数复杂、抗丢包弱。
# -----------------------------------------------------------------------------
section "3. AAC decode -> Opus RTP"
timeout 90 gst-launch-1.0 -q -e filesrc location="$F" ! qtdemux ! aacparse ! avdec_aac ! audioconvert ! audioresample ! opusenc ! rtpopuspay pt=111 ! fakesink sync=false
rc=$?
echo "audio_rtp_rc=$rc"
[ "$rc" -eq 0 ] && PASS=$((PASS+1)) || FAIL=$((FAIL+1))

# -----------------------------------------------------------------------------
# 4. 视频 RTP 走本机 UDP + RTP 头探针（见 02_rtp_probe.py）
#
# 先后台起探针监听 127.0.0.1:5004，再用 udpsink 把 RTP 发到本机回环；
# 探针统计包数/序号缺口/SSRC/PT，结果写 /tmp/vprobe.json。
# 这一步验证：RTP 包能经 UDP 发出、能被收端按 RTP 头解析。
# -----------------------------------------------------------------------------
section "4. Video RTP over localhost UDP + RTP header probe"
python3 rtp_probe.py 5004 14 > /tmp/vprobe.json 2>/tmp/vprobe.err &
pid=$!
sleep 1                                       # 等探针先 bind 端口
timeout 10 gst-launch-1.0 -q -e filesrc location="$F" ! qtdemux ! h264parse ! rtph264pay config-interval=1 pt=96 ! udpsink host=127.0.0.1 port=5004 sync=true
rc=$?
wait "$pid" 2>/dev/null || true               # 等探针退出
echo "video_udp_rc=$rc"
echo "probe:"
cat /tmp/vprobe.json 2>/dev/null || true
echo
if [ -s /tmp/vprobe.json ]; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); fi
if [ -s /tmp/vprobe.err ]; then echo "probe_err:"; tail -5 /tmp/vprobe.err; fi

# -----------------------------------------------------------------------------
# 5. 音频 RTP 走本机 UDP + 探针（端口 5006，避免和视频 5004 冲突）
# -----------------------------------------------------------------------------
section "5. Audio RTP over localhost UDP + RTP header probe"
python3 rtp_probe.py 5006 10 > /tmp/aprobe.json 2>/tmp/aprobe.err &
pid=$!
sleep 1
timeout 7 gst-launch-1.0 -q -e filesrc location="$F" ! qtdemux ! aacparse ! avdec_aac ! audioconvert ! audioresample ! opusenc ! rtpopuspay pt=111 ! udpsink host=127.0.0.1 port=5006 sync=true
rc=$?
wait "$pid" 2>/dev/null || true
echo "audio_udp_rc=$rc"
echo "probe:"
cat /tmp/aprobe.json 2>/dev/null || true
echo
if [ -s /tmp/aprobe.json ]; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); fi
if [ -s /tmp/aprobe.err ]; then echo "probe_err:"; tail -5 /tmp/aprobe.err; fi

# -----------------------------------------------------------------------------
# 汇总：PASS/FAIL 计数。注意 rc=124 是 timeout 主动掐断，属预期，不算失败。
# -----------------------------------------------------------------------------
section "SUMMARY"
echo "PASS=$PASS FAIL=$FAIL"
