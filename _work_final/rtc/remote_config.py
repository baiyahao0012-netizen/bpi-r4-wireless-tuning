# -*- coding: utf-8 -*-
"""远程实验机连接配置（不含任何明文口令）。

取值优先级：
  1. 环境变量 RTC_REMOTE_HOST / RTC_REMOTE_USER / RTC_REMOTE_PWD
  2. 同目录下的 remote_secrets.json（已在 .gitignore 中忽略，仅本机保存）

需要在新机器上运行时，复制一份 remote_secrets.json 填好即可，源码仓库不入库。
"""
import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_SECRETS_FILE = os.path.join(_HERE, "remote_secrets.json")


def _load_secrets():
    if os.path.exists(_SECRETS_FILE):
        with open(_SECRETS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


_cfg = _load_secrets()

# 主机地址 / 用户名 / 口令（口令只存在于本机配置或环境变量中）
HOST = os.environ.get("RTC_REMOTE_HOST", _cfg.get("host", ""))
USER = os.environ.get("RTC_REMOTE_USER", _cfg.get("user", ""))
PWD = os.environ.get("RTC_REMOTE_PWD", _cfg.get("pwd", ""))

# 旧脚本里用过的别名，保持调用处不变
REMOTE, RUSER, RPW = HOST, USER, PWD
HOST_USER, HOST_PW = USER, PWD
