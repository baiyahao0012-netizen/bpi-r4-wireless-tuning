#!/bin/sh
iw dev phy0.1 survey dump 2>&1 | head -24
echo '--- station airtime fields ---'
iw dev phy0.1-ap0 station dump | grep -E '^Station|tx duration|tx packets' | head -12
