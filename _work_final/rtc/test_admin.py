# -*- coding: utf-8 -*-
import ctypes, os, sys, traceback
LOG = r"D:\Desktop\AI 辅助对话\_work_final\rtc\admin_test.log"
out = open(LOG, "w", encoding="utf-8")
def p(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    out.write(s + "\n"); out.flush()

try:
    p("IsAdmin:", bool(ctypes.windll.shell32.IsUserAnAdmin()))
except Exception as e:
    p("IsAdmin check failed:", repr(e))

sys.path.insert(0, r"D:\Desktop\AI 辅助对话\_work_final\rtc")
import l2sock

frame = b"\xff" * 6 + b"\x02\x00\x00\x00\x00\x01" + b"\x88\xb5" + b"RTC2" + b"\x00" * 40
for sub in ("GbE Family", "8852", "MediaTek"):
    try:
        s = l2sock.L2Socket(dev_substr=sub)
        s.send(frame)
        p("%-12s SEND OK   (%s)" % (sub, s.desc[:45]))
        s.close()
    except Exception as e:
        p("%-12s SEND FAIL %s" % (sub, str(e)[:110]))

p("done")
out.close()
