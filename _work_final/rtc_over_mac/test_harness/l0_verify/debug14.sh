#!/bin/bash
# debug14.sh — T5 闭环：rtpbin 发出 SR，字段级解析探针核对 SSRC/NTP/RTP/包数/字节数
set -u
cd /home/bai/rtc_test
OUT=/tmp/l0
pkill -f gst-launch 2>/dev/null; sleep 1

python3 /home/bai/rtc_test/l0/rtcp_sr_probe.py 5035 16 >"$OUT/t5_sr.json" 2>"$OUT/t5_sr.err" &
CP=$!
sleep 1
timeout 14 gst-launch-1.0 -q -e rtpbin name=R \
    filesrc location=clip10.mp4 ! qtdemux ! h264parse ! \
    rtph264pay config-interval=1 pt=96 ! R.send_rtp_sink_0 \
    R.send_rtp_src_0 ! udpsink host=127.0.0.1 port=5034 \
    R.send_rtcp_src_0 ! udpsink host=127.0.0.1 port=5035 sync=false async=false \
    2>"$OUT/t5_sr.gst.err"
T5_RC=$?
wait "$CP" 2>/dev/null || true
echo "gst_rc=$T5_RC"
echo "=== SR 解析结果 ==="
cat "$OUT/t5_sr.json"
echo
echo "=== 管线错误行 ==="
grep -icE 'error|fail|corrupt|wrong' "$OUT/t5_sr.gst.err" || true
