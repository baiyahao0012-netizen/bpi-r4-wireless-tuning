# -*- coding: utf-8 -*-
p = r"D:\Desktop\AI 辅助对话\_work_final\rtc\receiver.py"
d = open(p, "rb").read()
idx = [i for i, b in enumerate(d) if b == 0]
print("nul count:", len(idx))
for i in idx[:5]:
    print("at", i, repr(d[max(0, i-60):i+20]))
