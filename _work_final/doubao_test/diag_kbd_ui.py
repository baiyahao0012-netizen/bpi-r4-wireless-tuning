# -*- coding: utf-8 -*-
import time, sys, xml.etree.ElementTree as ET
sys.path.insert(0, r"D:\Desktop\AI 辅助对话\_work_final\doubao_test")
from recon_send import sh

D = r"D:\Desktop\AI 辅助对话\_shots"
# ensure keyboard shown
sh("shell", "input", "tap", "639", "3053"); time.sleep(2.0)
sh("shell", "uiautomator", "dump", "/sdcard/ui_kbd.xml")
sh("pull", "/sdcard/ui_kbd.xml", D + "\\ui_kbd.xml")
root = ET.parse(D + "\\ui_kbd.xml").getroot()
with open(D + "\\ui_kbd.txt", "w", encoding="utf-8") as f:
    for n in root.iter("node"):
        a = n.attrib
        txt = a.get("text","") or ""; desc = a.get("content-desc","") or ""
        rid = (a.get("resource-id","") or "").split("/")[-1]
        cls = (a.get("class","") or "").split(".")[-1]
        b = a.get("bounds","")
        if txt or desc or "send" in rid.lower() or "send" in desc.lower():
            f.write("%-22s clk=%-5s %-14s %-22s txt=%s | desc=%s\n" % (b, a.get("clickable",""), cls, rid, txt, desc))
print(open(D + "\\ui_kbd.txt", encoding="utf-8").read())
