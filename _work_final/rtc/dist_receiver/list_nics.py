# -*- coding: utf-8 -*-
"""列出本机所有可用的 Npcap 网卡，供 --iface / --fb-iface 选择。"""
import l2sock

devs = l2sock.list_devices()
print("本机可用网卡 (%d 个):\n" % len(devs))
for i, d in enumerate(devs):
    print("  [%d] %s" % (i, d))
print("")
print("用法: --iface 后面填名称的一段子串, 例如 8852 / GbE / WiFi")
