# -*- coding: utf-8 -*-
import sys, time, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import doubao as D

def log(*a):
    print(*a, flush=True)

REMOTE = "/sdcard/qa.mp4"
LOCAL = r"D:\Desktop\AI 辅助对话\_shots\qa.mp4"
QUESTION = ("Explain TCP congestion control in detail: slow start, congestion avoidance, "
            "fast retransmit, fast recovery. Give at least 500 words.")

log("devices:", D.devices().replace("\n", " | "))
log("focus:", D.foreground()[:90])

# clear any leftover input
D.sh("shell", "input", "keyevent", "123")   # move to end
D.sh("shell", "input", "keyevent", *(["67"] * 250))
time.sleep(0.8)
log("cleared input")

# focus (keyboard may already be shown; tapping input box area is safe if keyboard shown at ~1800)
D.sh("shell", "input", "keyevent", "4")     # dismiss keyboard if shown
time.sleep(0.8)
D.tap(*D.INPUT_XY)
time.sleep(1.8)
D.screencap("qa2_input")
D.type_text(QUESTION)
time.sleep(1.2)
D.screencap("qa2_typed")
log("typed question")

log("start recording")
proc = D.record_start(REMOTE, 100)
time.sleep(3.0)
log("send at", time.strftime("%H:%M:%S"))
D.send()
log("waiting for recording to finish")
for i in range(115):
    if proc.poll() is not None:
        break
    time.sleep(1)
log("record rc=", proc.returncode)
time.sleep(1.0)
D.sh("pull", REMOTE, LOCAL)
log("pulled:", os.path.getsize(LOCAL) if os.path.exists(LOCAL) else "MISSING")
