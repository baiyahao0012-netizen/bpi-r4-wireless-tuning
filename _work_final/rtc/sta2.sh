#!/bin/sh
iw dev phy0.1-ap0 station dump | grep -E "^Station|tx bitrate|rx bitrate|signal:"
