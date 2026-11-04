#!/bin/bash
B=192.168.240.1
S="ssh -o StrictHostKeyChecking=no -o ConnectTimeout=6 root@$B"
$S 'echo ===cpu===; nproc; echo ===usb===; ls /sys/bus/usb/devices/ 2>/dev/null | head -6; echo ===video===; ls /dev/video* 2>/dev/null || echo none; echo ===libs===; ls /usr/lib/libasound* /usr/lib/libopus* 2>/dev/null | head -5; echo ===opkg===; opkg list-installed 2>/dev/null | grep -icE "ffmpeg|alsa|opus|x264"' 2>&1 | grep -v "WARNING\|post-quantum\|store now\|upgraded\|openssh.com"
echo CAP2_DONE
