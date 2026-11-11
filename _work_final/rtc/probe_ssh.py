# -*- coding: utf-8 -*-
import paramiko

from remote_config import HOST, PWD as PW, USER
for u in [USER]:
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        cli.connect(HOST, port=22, username=u, password=PW, timeout=8,
                    banner_timeout=12, auth_timeout=12,
                    look_for_keys=False, allow_agent=False)
        print("OK  user=%r" % u)
        for cmd in ["whoami", "hostname", "python --version 2>&1"]:
            si, so, se = cli.exec_command(cmd, timeout=30)
            print("  >", cmd, "->", so.read().decode("utf-8", "replace").strip(),
                  se.read().decode("utf-8", "replace").strip())
        cli.close()
        break
    except paramiko.AuthenticationException:
        print("FAIL user=%r" % u)
    except Exception as e:
        print("ERR  user=%r %r" % (u, e))
    finally:
        try:
            cli.close()
        except Exception:
            pass
