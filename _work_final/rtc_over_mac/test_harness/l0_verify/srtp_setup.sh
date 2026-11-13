#!/bin/bash
# srtp_setup.sh — 免 sudo 安装 GStreamer GI typelib 到用户目录，验证 PyGI 可加载 Gst
set -u
mkdir -p "$HOME/.local/gi"
cd /tmp/l0 || exit 1

echo "=== 1. 下载 gir deb（无需 sudo）==="
apt-get download gir1.2-gstreamer-1.0 2>&1 | tail -5
ls -l *.deb 2>/dev/null

echo "=== 2. 解包到 ~/.local/gi ==="
for d in *.deb; do [ -e "$d" ] && dpkg-deb -x "$d" "$HOME/.local/gi"; done

echo "=== 3. typelib 落点 ==="
find "$HOME/.local/gi" -name '*.typelib'

TYPEDIR=$(find "$HOME/.local/gi" -type d -name girepository-1.0 | head -1)
echo "TYPEDIR=$TYPEDIR"
export GI_TYPELIB_PATH="$TYPEDIR${GI_TYPELIB_PATH:+:$GI_TYPELIB_PATH}"

echo "=== 4. PyGI 加载测试 ==="
python3 -c "import gi; gi.require_version('Gst','1.0'); from gi.repository import Gst; print('Gst loaded, version=', Gst.version())"
