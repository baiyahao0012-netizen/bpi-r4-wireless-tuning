#!/bin/bash
B=192.168.240.1
S="ssh -o StrictHostKeyChecking=no -o ConnectTimeout=6 root@$B"
$S '
  echo "=== encoders ==="
  for t in ffmpeg x264 gst-launch-1.0; do command -v $t >/dev/null 2>&1 && echo "$t: yes" || echo "$t: no"; done
  echo "=== ALSA ==="
  cat /proc/asound/cards 2>/dev/null || echo none
  ls /dev/snd/ 2>/dev/null || echo no-dev-snd
  echo "=== usb ===
  ls /sys/bus/usb/devices/ 2>/dev/null | head -6
  echo "=== video dev ==="
  ls /dev/video* 2>/dev/null || echo no-video
  echo "=== cpu ==="
  nproc
  echo "=== ffmpeg encoders ==="
  ffmpeg -hide_banner -encoders 2>/dev/null | grep -iE "264|aac|opus" | head -6
  echo "=== libs ==="
  ls /usr/lib/libasound* /usr/lib/libopus* 2>/dev/null | head -5
' 2>&1 | grep -v "WARNING\|post-quantum\|store now\|upgraded\|openssh.com"
echo CAP_DONE
