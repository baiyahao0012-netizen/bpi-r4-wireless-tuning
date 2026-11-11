# -*- coding: utf-8 -*-
import paramiko, sys
from remote_config import HOST as host, USER as user, PWD as pwd
t = paramiko.Transport((host, 22))
t.connect(username=user, password=pwd)
sftp = paramiko.SFTPClient.from_transport(t)
for name in ["rcv03.mp4", "rcv03.pcm"]:
    sftp.get("C:/rtc/" + name, name)
    print("got", name)
sftp.close(); t.close()
