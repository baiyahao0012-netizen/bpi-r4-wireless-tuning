# -*- coding: utf-8 -*-
import os, sys, codecs, paramiko
from remote_config import HOST, USER, PW
here = os.path.dirname(os.path.abspath(__file__))
cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect(HOST, port=22, username=USER, password=PW, timeout=10,
            look_for_keys=False, allow_agent=False)
sftp = cli.open_sftp()
for fn in sys.argv[1:]:
    p = os.path.join(here, fn)
    with open(p, 'rb') as f:
        data = f.read()
    if fn.lower().endswith('.ps1') and not data.startswith(codecs.BOM_UTF8):
        data = codecs.BOM_UTF8 + data      # PowerShell 5.1 needs the BOM
    with sftp.open("C:\\rtc\\" + fn, 'wb') as rf:
        rf.write(data)
    print("uploaded", fn, len(data), "B")
sftp.close()
cli.close()
