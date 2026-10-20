# -*- coding: utf-8 -*-
"""SSH 到 BPI-R4 板端执行命令（远程命令作为单参数传给 ssh，标准模式）。用法：
python ssh_run.py "命令1; 命令2"
输出：远程 stdout + rc
"""
import sys, subprocess, time

if len(sys.argv) < 2:
    print("usage: ssh_run.py '<shell command>'", file=sys.stderr)
    sys.exit(2)

cmd = sys.argv[1]
for attempt in range(3):
    argv = ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=15',
            '-o', 'ServerAliveInterval=5', '-o', 'ServerAliveCountMax=2',
            'root@192.168.1.1', cmd]
    try:
        r = subprocess.run(argv, capture_output=True, timeout=50)
        if r.returncode == 0 or b'Usage:' not in r.stdout:
            break
    except subprocess.TimeoutExpired:
        print('[TIMEOUT attempt %d]' % (attempt + 1))
    if attempt < 2:
        time.sleep(5)
print('rc=%d' % r.returncode)
if r.stdout:
    sys.stdout.buffer.write(r.stdout)
    sys.stdout.buffer.flush()
if r.stderr:
    print('[stderr]', r.stderr[:1500])
