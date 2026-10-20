# -*- coding: utf-8 -*-
"""paramiko 执行 BPI-R4 板端命令。用法：
python ssh_py.py "命令1; 命令2"
输出：远程 stdout + rc
"""
import sys, paramiko

if len(sys.argv) < 2:
    print("usage: ssh_py.py '<shell command>'", file=sys.stderr)
    sys.exit(2)

cmd = sys.argv[1]
cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    cli.connect('192.168.1.1', username='root', password=None, timeout=15,
                allow_agent=False, look_for_keys=False, banner_timeout=20,
                auth_timeout=20)
except Exception as e:
    print('CONNECT_ERR: %r' % e)
    sys.exit(1)
try:
    stdin, stdout, stderr = cli.exec_command(cmd, timeout=60)
    out = stdout.read().decode('utf-8', 'replace')
    err = stderr.read().decode('utf-8', 'replace')
    rc = stdout.channel.recv_exit_status()
except Exception as e:
    print('EXEC_ERR: %r' % e)
    sys.exit(1)
cli.close()
print('rc=%d' % rc)
if out:
    print(out)
if err:
    print('[stderr]', err[:1500])
