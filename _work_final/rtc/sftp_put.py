# -*- coding: utf-8 -*-
"""Upload the receiver package to the remote host over SFTP."""
import os
import sys
import paramiko

HOST, USER, PW = "192.168.240.221", "labuser", "[REDACTED-PWD]"
REMOTE_DIR = r"C:\rtc"
FILES = ["receiver.py", "rtc2.py", "l2sock.py", "txport.py", "list_nics.py",
         "README.txt"]

here = os.path.dirname(os.path.abspath(__file__))
src = os.path.join(here, "dist_receiver")

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect(HOST, port=22, username=USER, password=PW, timeout=10,
            banner_timeout=15, auth_timeout=15,
            look_for_keys=False, allow_agent=False)

# make the directory (cmd syntax, no quoting surprises)
si, so, se = cli.exec_command('if not exist %s mkdir %s' % (REMOTE_DIR, REMOTE_DIR))
so.channel.recv_exit_status()

sftp = cli.open_sftp()
for fn in FILES:
    p = os.path.join(src, fn)
    if not os.path.exists(p):
        print("skip (missing):", fn)
        continue
    sftp.put(p, REMOTE_DIR + "\\" + fn)
    print("uploaded %-16s %7d B" % (fn, os.path.getsize(p)))
sftp.close()

si, so, se = cli.exec_command("dir %s" % REMOTE_DIR)
out = so.read().decode("gbk", "replace")
print(out)
cli.close()
