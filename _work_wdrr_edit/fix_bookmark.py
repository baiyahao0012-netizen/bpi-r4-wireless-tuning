# -*- coding: utf-8 -*-
"""移除新增标题段落中因 deepcopy 带入的重复书签（bookmark id 21）。"""
from docx import Document
from docx.oxml.ns import qn

TARGET = r'D:\Desktop\AI 辅助对话\mac80211 WDRR 调度器部署验证报告.docx'
doc = Document(TARGET)

targets = ['6.4 WDRR 加权专项验证', '6.5 原版基线对照（.orig）']
removed = 0
for p in doc.paragraphs:
    if any(t in p.text for t in targets):
        for el in p._p.findall(qn('w:bookmarkStart')) + p._p.findall(qn('w:bookmarkEnd')):
            p._p.remove(el)
            removed += 1
print('REMOVED_BOOKMARKS', removed)
doc.save(TARGET)
print('DONE')
