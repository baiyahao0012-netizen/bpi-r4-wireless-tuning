# -*- coding: utf-8 -*-
import subprocess, time, sys
sys.path.insert(0, r"D:\Desktop\AI 辅助对话\_work_final\doubao_test")
from recon_send import sh, dump_ui, parse

OUT = r"D:\Desktop\AI 辅助对话\_shots\ui_input2.txt"
# ensure ADBKeyboard is current
print(sh("shell", "ime", "set", "com.android.adbkeyboard/.AdbIME")[1].strip())
time.sleep(1.5)
print("tap:", sh("shell", "input", "tap", "639", "3053")[0])
time.sleep(1.5)
# single remote command string with quotes so spaces survive
msg = "hello doubao test"
print(sh("shell", "am broadcast -a ADB_INPUT_TEXT --es msg '%s'" % msg)[1].strip()[:160])
time.sleep(1.5)
p = dump_ui(); parse(p, OUT)
with open(OUT, encoding="utf-8") as f:
    for line in f:
        if "input_text" in line or "action_" in line or "send" in line.lower() or "EditText" in line:
            print(line.rstrip())
