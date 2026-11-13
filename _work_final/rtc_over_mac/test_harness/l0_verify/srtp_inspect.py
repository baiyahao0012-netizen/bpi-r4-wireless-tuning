#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""srtp_inspect.py — 内省 srtpenc/srtpdec 属性与 request-key 信号签名"""
import gi
gi.require_version("Gst", "1.0")
from gi.repository import Gst, GLib

Gst.init(None)

for name in ("srtpenc", "srtpdec"):
    fac = Gst.ElementFactory.find(name)
    print("=== %s ===" % name)
    e = fac.create(name)
    for prop in e.list_properties():
        val = e.get_property(prop.name)
        print("  prop %-22s type=%-28s default=%s" % (prop.name, prop.value_type.name, val))
    # 信号列表
    try:
        for sig in Gst.Object.list_signals(e):
            print("  signal:", sig)
    except Exception as ex:
        print("  signal list err:", ex)
