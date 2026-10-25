# -*- coding: utf-8 -*-
"""提取 BPI-R4 实测报告 docx 的段落与表格文本，供核对原始数据"""
import docx

SRC = r"D:\Desktop\AI 辅助对话\_work_final\BPI-R4_EDCA_AMPDU_MCS_WDRR_实测报告.docx"
OUT = r"D:\Desktop\AI 辅助对话\_work_final\docx_extract.txt"

d = docx.Document(SRC)
lines = []
for p in d.paragraphs:
    t = p.text.strip()
    if t:
        lines.append(t)
for i, tbl in enumerate(d.tables):
    lines.append(f"=== TABLE {i} ===")
    for row in tbl.rows:
        cells = []
        seen = set()
        for c in row.cells:
            txt = c.text.strip().replace("\n", " / ")
            if txt not in seen:
                seen.add(txt)
                cells.append(txt)
        lines.append(" | ".join(cells))

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("paragraphs:", len(d.paragraphs), "tables:", len(d.tables), "->", OUT)
