#!/bin/bash
# debug2.sh — 修复验证：udpsrc 显式 RTP caps；rtpbin 正确引用语法
set -u
cd /home/bai/rtc_test
CLIP=clip10.mp4
OUT=/tmp/l0
mkdir -p "$OUT"
VCAPS="application/x-rtp,media=video,clock-rate=90000,encoding-name=H264,pt=96"

run_recv () {
    local name="$1"; local chain="$2"; local port=5014
    rm -f "$OUT/$name.h264"
    pkill -f gst-launch 2>/dev/null; sleep 1
    timeout 20 gst-launch-1.0 -q $chain filesink location="$OUT/$name.h264" 2>"$OUT/$name.recv.err" &
    sleep 1.5
    timeout 12 gst-launch-1.0 -q -e filesrc location="$CLIP" ! qtdemux ! h264parse ! \
        rtph264pay config-interval=1 pt=96 ! udpsink host=127.0.0.1 port=$port \
        2>"$OUT/$name.send.err"
    wait 2>/dev/null
    echo "--- $name ---"
    ls -la "$OUT/$name.h264" 2>/dev/null || echo "no file"
    if [ -s "$OUT/$name.h264" ]; then
        ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames \
            -of default=noprint_wrappers=1:nokey=1 "$OUT/$name.h264" | sed 's/^/rx_frames=/'
    fi
    echo "recv_err:"; cat "$OUT/$name.recv.err"
}

# R1：显式 caps，最简链
run_recv "fix1" "udpsrc port=5014 caps=\"$VCAPS\" ! rtph264depay !"
# R2：显式 caps + jitterbuffer
run_recv "fix2" "udpsrc port=5014 caps=\"$VCAPS\" ! rtpjitterbuffer ! rtph264depay !"
# R3：完整 T3 链
run_recv "fix3" "udpsrc port=5014 caps=\"$VCAPS\" ! rtpjitterbuffer ! rtph264depay ! h264parse !"

echo "=== T5 rtpbin 修正语法 ==="
python3 /home/bai/rtc_test/l0/rtcp_probe.py 5035 16 >"$OUT/t5b.json" 2>"$OUT/t5b.err" &
CP=$!
sleep 1
timeout 14 gst-launch-1.0 -q -e rtpbin name=R. \
    filesrc location="$CLIP" ! qtdemux ! h264parse ! rtph264pay config-interval=1 pt=96 ! R.send_rtp_sink \
    R.send_rtp_src ! udpsink host=127.0.0.1 port=5034 \
    R.send_rtcp_src ! udpsink host=127.0.0.1 port=5035 sync=false \
    2>"$OUT/t5b.gst.err"
echo "t5b_rc=$?"
wait "$CP" 2>/dev/null || true
echo "t5b json:"; cat "$OUT/t5b.json"
echo "t5b err:"; cat "$OUT/t5b.gst.err"
echo "=== DONE ==="
