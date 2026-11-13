#!/bin/bash
# Local GStreamer media-layer functional test on Raspberry Pi.
set -u
cd /home/bai/rtc_test || exit 1
F=1080p30_1_artemis_origins_85s.mp4
PASS=0
FAIL=0

section() { echo; echo "===== $* ====="; }

section "0. Environment"
hostname
date
gst-launch-1.0 --version | head -2
ls -lh "$F"

section "1. H.264 decode (85 s clip, fakesink)"
t0=$(date +%s)
timeout 90 gst-launch-1.0 -q filesrc location="$F" ! qtdemux ! h264parse ! avdec_h264 ! fakesink sync=false
rc=$?
t1=$(date +%s)
echo "decode_rc=$rc elapsed=$((t1-t0))s"
[ "$rc" -eq 0 ] && PASS=$((PASS+1)) || FAIL=$((FAIL+1))

section "2. H.264 RTP packetization"
timeout 90 gst-launch-1.0 -q -e filesrc location="$F" ! qtdemux ! h264parse ! rtph264pay config-interval=1 pt=96 ! fakesink sync=false
rc=$?
echo "h264_rtp_rc=$rc"
[ "$rc" -eq 0 ] && PASS=$((PASS+1)) || FAIL=$((FAIL+1))

section "3. AAC decode -> Opus RTP"
timeout 90 gst-launch-1.0 -q -e filesrc location="$F" ! qtdemux ! aacparse ! avdec_aac ! audioconvert ! audioresample ! opusenc ! rtpopuspay pt=111 ! fakesink sync=false
rc=$?
echo "audio_rtp_rc=$rc"
[ "$rc" -eq 0 ] && PASS=$((PASS+1)) || FAIL=$((FAIL+1))

section "4. Video RTP over localhost UDP + RTP header probe"
python3 rtp_probe.py 5004 14 > /tmp/vprobe.json 2>/tmp/vprobe.err &
pid=$!
sleep 1
timeout 10 gst-launch-1.0 -q -e filesrc location="$F" ! qtdemux ! h264parse ! rtph264pay config-interval=1 pt=96 ! udpsink host=127.0.0.1 port=5004 sync=true
rc=$?
wait "$pid" 2>/dev/null || true
echo "video_udp_rc=$rc"
echo "probe:"
cat /tmp/vprobe.json 2>/dev/null || true
echo
if [ -s /tmp/vprobe.json ]; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); fi
if [ -s /tmp/vprobe.err ]; then echo "probe_err:"; tail -5 /tmp/vprobe.err; fi

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
