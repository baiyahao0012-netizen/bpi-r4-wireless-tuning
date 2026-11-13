#!/bin/bash
# srtp_run.sh — 运行 SRTP 回环闭环（免 sudo typelib 环境）
set -u
export GI_TYPELIB_PATH=/home/bai/.local/gi/usr/lib/aarch64-linux-gnu/girepository-1.0
cd /home/bai/rtc_test
python3 /home/bai/rtc_test/l0/srtp_loopback.py 2>&1
