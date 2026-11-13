#!/bin/bash
# env_probe.sh — SRTP 闭环卡点与绑定现状探测
echo "=== dpkg 绑定现状 ==="
dpkg -l 2>/dev/null | grep -E 'gir1.2-gstreamer|gir1.2-gst-plugins-base|python3-gi' || echo "none"

echo "=== PyGI import 测试 ==="
python3 -c "import gi; print('gi module ok')" 2>&1
python3 -c "import gi; gi.require_version('Gst','1.0'); import gi.repository.Gst as Gst; print('Gst typelib ok')" 2>&1

echo "=== apt 候选版本 ==="
apt-cache policy gir1.2-gstreamer-1.0 2>/dev/null | grep -E 'Candidate|Installed'
apt-cache policy gir1.2-gst-plugins-base-1.0 2>/dev/null | grep -E 'Candidate|Installed'

echo "=== srtpdec 信号/属性 ==="
gst-inspect-1.0 srtpdec 2>/dev/null | grep -E 'request-key|clear-keys|remove-key|replay-window|stats'

echo "=== 磁盘空间 ==="
df -h / | tail -1
