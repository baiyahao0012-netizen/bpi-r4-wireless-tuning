# -*- coding: utf-8 -*-
"""把本地文件通过 ssh stdin + 远程 cat 写入板端。用法：
python ssh_put.py <本地文件> <远端路径>
"""
import sys, subprocess

if len(sys.argv) != 3:
    print("usage: ssh_put.py <local_file> <remote_path>", file=sys.stderr)
    sys.exit(2)

local = sys.argv[1]
remote = sys.argv[2]
data = open(local, 'rb').read()

argv = ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=15',
        'root@192.168.1.1', 'cat > %s' % remote]
p = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE)
out, err = p.communicate(data, timeout=40)
print('rc=%d wrote=%d bytes' % (p.returncode, len(data)))
if err:
    print('[stderr]', err[:1000])
