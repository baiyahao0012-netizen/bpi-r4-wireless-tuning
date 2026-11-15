#!/bin/bash
# Capture pcap evidence for representative arms: A (no loss), B (video RTX on), E (SRTP).
set -u
export LC_ALL=C
export GI_TYPELIB_PATH=/home/bai/.local/gi/usr/lib/aarch64-linux-gnu/girepository-1.0
LAB=/tmp/file_av_lab.py
F=/tmp/retest_clips/1080p25_3_bbb_trailer_33s_10s.mp4
V=(--video-rtp-port 5223 --video-rtcp-port 5224 --video-feedback-port 5225)
A=(--audio-rtp-port 5323 --audio-rtcp-port 5324 --audio-feedback-port 5325)

cap_arm() {  # tag sender_extra receiver_extra
  local tag="$1" sx="$2" rx="$3"
  echo 12345678 | sudo -S tcpdump -i lo -s 0 -w "/tmp/pcap_${tag}.pcap" udp 2>/dev/null &
  local tp=$!
  sleep 2
  python3 "$LAB" receiver --file "$F" --seconds 14 "${V[@]}" "${A[@]}" $rx > "/tmp/pcap_${tag}_rx.log" 2>&1 &
  local rp=$!
  sleep 2
  python3 "$LAB" sender --file "$F" --seconds 10 "${V[@]}" "${A[@]}" $sx > "/tmp/pcap_${tag}_tx.log" 2>&1
  wait $rp 2>/dev/null || true
  sleep 1
  sudo kill $tp 2>/dev/null || true
  wait $tp 2>/dev/null || true
  echo "CAP ${tag} $(ls -l /tmp/pcap_${tag}.pcap 2>/dev/null | awk '{print $5}') bytes"
}

cap_arm A_bbb "" ""
cap_arm B_rtx_on "--video-rtx --video-loss 0.05" "--video-rtx"
cap_arm E_srtp "--srtp" "--srtp"
echo PCAP_DONE
