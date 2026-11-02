# -*- coding: utf-8 -*-
"""Record one Doubao text Q&A round (no congestion) to develop the analyzer."""
import sys, time, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import doubao as D

REMOTE = "/sdcard/qa.mp4"
LOCAL = r"D:\Desktop\AI 辅助对话\_shots\qa.mp4"
QUESTION = ("Please explain TCP congestion control in detail, including slow start, "
            "congestion avoidance, fast retransmit and fast recovery. At least 600 words.")

print("devices:", D.devices().replace("\n", " | "))
print("focus:", D.foreground()[:90])
D.focus_input()
time.sleep(1.0)
D.screencap("qa_inputstate")
print("typing...")
D.type_text(QUESTION)
time.sleep(1.0)
D.screencap("qa_typed")
print("start recording")
proc = D.record_start(REMOTE, 120)
time.sleep(2.5)
print("send at", time.strftime("%H:%M:%S"))
D.send()
# wait for the recording to finish
for i in range(130):
    if proc.poll() is not None:
        break
    time.sleep(1)
print("record done, rc=", proc.returncode)
time.sleep(1)
D.sh("pull", REMOTE, LOCAL)
print("pulled:", LOCAL, os.path.getsize(LOCAL) if os.path.exists(LOCAL) else "MISSING")
