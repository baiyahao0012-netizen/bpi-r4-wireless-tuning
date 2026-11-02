# -*- coding: utf-8 -*-
import subprocess, time, sys
sys.path.insert(0, r"D:\Desktop\AI 辅助对话\_work_final\doubao_test")
from recon_send import sh

def grep(cmd, pats):
    out = sh("shell", cmd)[1]
    for line in out.splitlines():
        if any(p in line for p in pats):
            print("   ", line.strip()[:180])

print("== before tap ==")
grep("dumpsys input_method", ["mInputShown", "mServedView", "mCurFocusedWindow", "mImeWindowVis", "mShowRequested", "mServedInputConnection"])
print("== tap input ==")
sh("shell", "input", "tap", "639", "3053"); time.sleep(2.0)
grep("dumpsys input_method", ["mInputShown", "mServedView", "mCurFocusedWindow", "mImeWindowVis", "mShowRequested", "mServedInputConnection"])
print("== current focus ==")
out = sh("shell", "dumpsys window")[1]
for line in out.splitlines():
    if "mCurrentFocus" in line or "mFocusedApp" in line:
        print("   ", line.strip()[:180])
print("== input text ==")
print(sh("shell", "input text 'hello'")[1][:200])
time.sleep(1.5)
grep("dumpsys input_method", ["mServedInputConnection", "mInputShown"])
