# -*- coding: utf-8 -*-
import subprocess, time, sys
sys.path.insert(0, r"D:\Desktop\AI 辅助对话\_work_final\doubao_test")
from recon_send import sh, dump_ui, parse

OUT = r"D:\Desktop\AI 辅助对话\_shots\ui_input.txt"
print("set ADBKeyboard:", sh("shell", "ime", "set", "com.android.adbkeyboard/.AdbIME")[1].strip())
time.sleep(2)
print("tap input:", sh("shell", "input", "tap", "639", "3053")[0])
time.sleep(1.5)
print("broadcast:", sh("shell", "am", "broadcast", "-a", "ADB_INPUT_TEXT", "--es", "msg", "hello doubao test")[1].strip()[:120])
time.sleep(1.5)
p = dump_ui()
parse(p, OUT)
# print only the input area lines
with open(OUT, encoding="utf-8") as f:
    for line in f:
        if "input_text" in line or "action_" in line or "send" in line.lower():
            print(line.rstrip())
