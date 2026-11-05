# -*- coding: utf-8 -*-
p = r"D:\Desktop\AI 辅助对话\_work_final\rtc\receiver.py"
d = open(p, "rb").read()
before = d.count(b"\x00")
d = d.replace(b"b'\x00'", b"b'\\x00'")
after = d.count(b"\x00")
open(p, "wb").write(d)
print("nul before=%d after=%d" % (before, after))
