# -*- coding: utf-8 -*-
"""Run a command on a remote Windows host over SSH.

    python ctl.py <host> <user> <password> "<command>"
"""
import sys
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
import paramiko

from remote_config import HOST_USER, HOST_PW


def run(host, cmd, user=HOST_USER, pwd=HOST_PW, timeout=180):
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cli.connect(host, port=22, username=user, password=pwd, timeout=10,
                banner_timeout=15, auth_timeout=15,
                look_for_keys=False, allow_agent=False)
    si, so, se = cli.exec_command(cmd, timeout=timeout)
    out = so.read()
    err = se.read()
    rc = so.channel.recv_exit_status()
    cli.close()
    return out, err, rc


def dec(b):
    for enc in ('gbk', 'utf-8'):
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            continue
    return b.decode('utf-8', 'replace')


def main():
    if len(sys.argv) < 5:
        print(__doc__)
        return 2
    host, user, pwd, cmd = sys.argv[1:5]
    out, err, rc = run(host, cmd, user, pwd)
    sys.stdout.write(dec(out))
    if err.strip():
        sys.stdout.write('--- stderr ---\n' + dec(err))
    sys.stdout.write('\n--- exit %d ---\n' % rc)
    return 0


if __name__ == '__main__':
    sys.exit(main())
