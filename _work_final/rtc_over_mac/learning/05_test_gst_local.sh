#!/bin/bash
# 05 本地功能测试脚本（Pi 上跑，不碰真实网络）
# ================================================
# 目的：在 127.0.0.1 回环上验证媒体层五个基本功能，按退出码统计 PASS/FAIL。
# 运行：bash 05_test_gst_local.sh
#
# 五个检查项：
#   1) H.264 能不能解码
#   2) H.264 能不能打成 RTP
#   3) AAC 能不能转 Opus 并打成 RTP
#   4) 视频 RTP 走本地 UDP + 探针收包统计头字段
#   5) 音频 RTP 走本地 UDP + 探针收包统计头字段
set -u                                  # 引用未定义变量直接报错，避免静默带病运行
cd /home/bai/rtc_test || exit 1         # 素材所在目录；进不去就退出
F=1080p30_1_artemis_origins_85s.mp4     # smoke 主素材
PASS=0
FAIL=0

# 打印分节标题的小函数
section() { echo; echo "===== $* ====="; }

section "0. Environment"
hostname
date
gst-launch-1.0 --version | head -2
ls -lh "$F"

# ---- 1. H.264 解码：fakesink 只丢帧不存文件，能跑完 rc=0 即说明解码没崩 ----
section "1. H.264 decode (85 s clip, fakesink)"
t0=$(date +%s)
timeout 90 gst-launch-1.0 -q filesrc location="$F" ! qtdemux ! h264parse ! avdec_h264 ! fakesink sync=false
rc=$?
t1=$(date +%s)
echo "decode_rc=$rc elapsed=$((t1-t0))s"
[ "$rc" -eq 0 ] && PASS=$((PASS+1)) || FAIL=$((FAIL+1))

# ---- 2. H.264 RTP 打包：不发包，fakesink 接住 payloader 的输出 ----
section "2. H.264 RTP packetization"
timeout 90 gst-launch-1.0 -q -e filesrc location="$F" ! qtdemux ! h264parse ! rtph264pay config-interval=1 pt=96 ! fakesink sync=false
rc=$?
echo "h264_rtp_rc=$rc"
[ "$rc" -eq 0 ] && PASS=$((PASS+1)) || FAIL=$((FAIL+1))

# ---- 3. AAC 解码 -> Opus 编码 -> RTP 打包 ----
section "3. AAC decode -> Opus RTP"
timeout 90 gst-launch-1.0 -q -e filesrc location="$F" ! qtdemux ! aacparse ! avdec_aac ! audioconvert ! audioresample ! opusenc ! rtpopuspay pt=111 ! fakesink sync=false
rc=$?
echo "audio_rtp_rc=$rc"
[ "$rc" -eq 0 ] && PASS=$((PASS+1)) || FAIL=$((FAIL+1))

# ---- 4. 视频 RTP 走本地 UDP，探针后台收包解析头字段 ----
section "4. Video RTP over localhost UDP + RTP header probe"
# 后台起探针：端口 5004，收 14 秒；JSON 存 /tmp/vprobe.json，stderr 存 .err
python3 rtp_probe.py 5004 14 > /tmp/vprobe.json 2>/tmp/vprobe.err &
pid=$!                                  # 记下探针后台进程号
sleep 1                                 # 等探针先绑好端口，避免前几个包漏掉
timeout 10 gst-launch-1.0 -q -e filesrc location="$F" ! qtdemux ! h264parse ! rtph264pay config-interval=1 pt=96 ! udpsink host=127.0.0.1 port=5004 sync=true
rc=$?
wait "$pid" 2>/dev/null || true        # 等探针收尾；探针超时退出不算脚本失败
echo "video_udp_rc=$rc"
echo "probe:"
cat /tmp/vprobe.json 2>/dev/null || true
echo
# 探针输出了 JSON 就算这一项过；空文件记 FAIL
if [ -s /tmp/vprobe.json ]; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); fi
if [ -s /tmp/vprobe.err ]; then echo "probe_err:"; tail -5 /tmp/vprobe.err; fi

# ---- 5. 音频 RTP 走本地 UDP，端口 5006，收 10 秒 ----
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

section "SUMMARY"
echo "PASS=$PASS FAIL=$FAIL"

# 判定口径提醒：
# - rc=0 只代表管线没报错，不代表帧完整率达标；
# - 探针 JSON 里的 seq_gaps=0 只代表本地回环没缺口；
# - 真实无线链路的帧完整率/同步偏差，要在 L1 真实链路测试里另测。
