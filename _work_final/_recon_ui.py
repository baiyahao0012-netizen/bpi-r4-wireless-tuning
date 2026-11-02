# -*- coding: utf-8 -*-
import xml.etree.ElementTree as ET, re, sys
t = ET.parse(sys.argv[1]); r = t.getroot()
rows = []
for n in r.iter('node'):
    a = n.attrib
    txt = a.get('text','') or ''
    desc = a.get('content-desc','') or ''
    rid = a.get('resource-id','') or ''
    cls = a.get('class','') or ''
    b = a.get('bounds','')
    if txt or desc or ('EditText' in cls) or ('Button' in cls and rid):
        rows.append((b, cls.split('.')[-1], rid.split('/')[-1], txt[:40], desc[:30]))
print('total nodes:', sum(1 for _ in r.iter('node')), ' | shown:', len(rows))
for b, cls, rid, txt, desc in rows:
    print('%-22s %-14s %-22s txt=%-40s desc=%s' % (b, cls, rid, txt, desc))
