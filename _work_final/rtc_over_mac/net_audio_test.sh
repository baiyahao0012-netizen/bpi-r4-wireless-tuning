#!/bin/bash
# End-to-end Opus RTP over Wi-Fi -> AP bridge -> macvlan receiver.
set -u
cd /home/bai/rtc_test || exit 1
F=1080p30_1_artemis_origins_85s.mp4
RX_WAV=/tmp/rx_audio.wav
RX_LOG=/tmp/net_audio_rx.log
rm -f "$RX_WAV" "$RX_LOG"

echo "===== NETWORK OPUS RTP TEST ====="
echo "sender:   wlan1 192.168.240.126"
echo "receiver: rtc0  192.168.240.154 (netns rtcns)"
echo "path: Pi Wi-Fi -> AP bridge -> Pi Ethernet/macvlan"

printf '%s\n' '12345678' | sudo -S ip netns exec rtcns \
  timeout 18 gst-launch-1.0 -q \
  udpsrc address=192.168.240.154 port=5006 \
  caps="application/x-rtp,media=audio,encoding-name=OPUS,payload=111,clock-rate=48000" \
  ! rtpjitterbuffer latency=100 \
  ! rtpopusdepay ! opusdec ! audioconvert ! audioresample \
  ! audio/x-raw,rate=48000,channels=2 \
  ! wavenc ! filesink location="$RX_WAV" >"$RX_LOG" 2>&1 &
rxpid=$!

sleep 2
echo "receiver pid=$rxpid; sending 10 s of audio..."
t0=$(date +%s)
timeout 10 gst-launch-1.0 -q -e filesrc location="$F" \
  ! qtdemux ! aacparse ! avdec_aac ! audioconvert ! audioresample \
  ! opusenc ! rtpopuspay pt=111 \
  ! udpsink host=192.168.240.154 port=5006 bind-address=192.168.240.126 sync=true
send_rc=$?
t1=$(date +%s)
echo "sender_rc=$send_rc elapsed=$((t1-t0))s"

wait "$rxpid" 2>/dev/null || true
echo "rx_wav_size=$(stat -c %s "$RX_WAV" 2>/dev/null || echo 0) bytes"
python3 - "$RX_WAV" <<'PY'
import sys, wave, os
p=sys.argv[1]
if not os.path.exists(p) or os.path.getsize(p) < 44:
    print("wav=missing")
    raise SystemExit
w=wave.open(p,'rb')
print("wav_channels=%d rate=%d frames=%d duration=%.2fs" % (w.getnchannels(), w.getframerate(), w.getnframes(), w.getnframes()/w.getframerate()))
PY
echo "receiver_log_tail:"
tail -20 "$RX_LOG" 2>/dev/null || true
if [ -s "$RX_WAV" ]; then echo "RESULT=PASS"; else echo "RESULT=FAIL"; fi
