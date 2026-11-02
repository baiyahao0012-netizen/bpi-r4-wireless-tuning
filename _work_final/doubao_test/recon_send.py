# -*- coding: utf-8 -*-
"""Recon: tap input, type ASCII, dump UI, find the send button."""
import subprocess, sys, os, time, re, xml.etree.ElementTree as ET

ADB = r"D:\Desktop\AI 辅助对话\_work_recover\platform-tools\platform-tools\adb.exe"
PKG = "com.larus.nova"

def sh(*args, timeout=30):
    r = subprocess.run([ADB] + list(args), capture_output=True, timeout=timeout)
    return r.returncode, r.stdout.decode("utf-8", "replace"), r.stderr.decode("utf-8", "replace")

def dump_ui():
    sh("shell", "uiautomator", "dump", "/sdcard/ui.xml")
    sh("pull", "/sdcard/ui.xml", r"D:\Desktop\AI 辅助对话\_shots\ui_live.xml")
    return r"D:\Desktop\AI 辅助对话\_shots\ui_live.xml"

def parse(path, out):
    root = ET.parse(path).getroot()
    with open(out, "w", encoding="utf-8") as f:
        n = 0
        for node in root.iter("node"):
            a = node.attrib
            txt = a.get("text", "") or ""
            desc = a.get("content-desc", "") or ""
            rid = (a.get("resource-id", "") or "").split("/")[-1]
            cls = (a.get("class", "") or "").split(".")[-1]
            b = a.get("bounds", "")
            clk = a.get("clickable", "")
            if txt or desc or rid or cls in ("EditText", "Button", "ImageButton"):
                f.write("%-22s clk=%-5s %-14s %-24s txt=%s | desc=%s\n" % (b, clk, cls, rid, txt, desc))
                n += 1
    return n

if __name__ == "__main__":
    print("focus:", sh("shell", "dumpsys", "window")[1].split("mCurrentFocus")[1].split("\n")[0][:80] if "mCurrentFocus" in sh("shell", "dumpsys", "window")[1] else "?")
    # tap input box center
    print("tap input", sh("shell", "input", "tap", "639", "3053")[0])
    time.sleep(1.5)
    print("type", sh("shell", "input", "text", "hello_doubao_test")[0])
    time.sleep(1.5)
    p = dump_ui()
    n = parse(p, r"D:\Desktop\AI 辅助对话\_shots\ui_live.txt")
    print("nodes written:", n)
