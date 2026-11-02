#!/bin/bash
ssh -o StrictHostKeyChecking=no root@192.168.240.1 '
echo "--- total ko count ---"
find /lib/modules/6.6.73 -name "*.ko" | wc -l
echo "--- layout (dirs) ---"
find /lib/modules/6.6.73 -type d | head -20
echo "--- flat listing head ---"
ls /lib/modules/6.6.73/ | head -20
echo "--- modules in subdirs ---"
find /lib/modules/6.6.73 -mindepth 2 -name "*.ko" | head -20
echo "--- rom vs overlay ---"
echo "rom:     $(find /rom/lib/modules/6.6.73 -name '*.ko' 2>/dev/null | wc -l)"
echo "overlay: $(find /overlay/upper/lib/modules/6.6.73 -name '*.ko' 2>/dev/null | wc -l)"
echo "--- overlay module files ---"
find /overlay/upper/lib/modules/6.6.73 -name "*.ko" 2>/dev/null
echo "--- modules.d ---"
ls /etc/modules.d/ | head -40
' 2>/dev/null
