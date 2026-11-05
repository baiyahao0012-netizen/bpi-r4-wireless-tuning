# -*- coding: utf-8 -*-
import sys
from docx import Document

p = r"D:\Download\近期科研小结_白亚豪.docx"
doc = Document(p)
out = []
for para in doc.paragraphs:
    t = para.text.strip()
    if t:
        out.append(t)
for ti, tbl in enumerate(doc.tables):
    out.append("[TABLE %d]" % ti)
    for row in tbl.rows:
        out.append(" | ".join(c.text.strip() for c in row.cells))
text = "\n".join(out)
with open(r"D:\Desktop\AI 辅助对话\_work_final\rtc\doc_dump.txt", "w", encoding="utf-8") as f:
    f.write(text)
print("paragraphs:", len(doc.paragraphs), "tables:", len(doc.tables), "chars:", len(text))
