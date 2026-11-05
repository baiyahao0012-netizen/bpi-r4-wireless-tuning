# -*- coding: utf-8 -*-
import io

p = r"D:\Desktop\AI 辅助对话\_work_final\rtc\txport.py"
with open(p, 'rb') as f:
    d = f.read()
before = d.count(b'\x00')
d = d.replace(b"b'\x00' * 6", b"bytes(6)")
after = d.count(b'\x00')
with open(p, 'wb') as f:
    f.write(d)
print("nul before=%d after=%d" % (before, after))
