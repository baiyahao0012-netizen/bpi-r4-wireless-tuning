# -*- coding: utf-8 -*-
"""Doubao phone control helpers (adb). Text Q&A test harness."""
import subprocess, time, os, shutil

ADB = r"D:\Desktop\AI 辅助对话\_work_recover\platform-tools\platform-tools\adb.exe"
PKG = "com.larus.nova"
WORK = r"D:\Desktop\AI 辅助对话\_shots"
INPUT_XY = (639, 3053)     # input box center (keyboard hidden)
SEND_XY  = (1260, 1800)    # app send button (keyboard shown, 百度 IME)


def sh(*args, timeout=60, binary=False):
    r = subprocess.run([ADB] + list(args), capture_output=True, timeout=timeout)
    if binary:
        return r.returncode, r.stdout, r.stderr
    return r.returncode, r.stdout.decode("utf-8", "replace"), r.stderr.decode("utf-8", "replace")


def devices():
    return sh("devices")[1].strip()


def tap(x, y):
    return sh("shell", "input", "tap", str(int(x)), str(int(y)))[0]


def focus_input(wait=2.0):
    tap(*INPUT_XY)
    time.sleep(wait)


def _escape(s):
    # adb shell input text: spaces -> %s ; escape shell-special chars
    out = s.replace(" ", "%s")
    for ch in "()<>|;&*\\~^\"'\`":
        out = out.replace(ch, "\\" + ch)
    return out


def type_text(s, wait=1.0):
    """ASCII via input text; non-ASCII via ADBKeyboard broadcast (sets IME temporarily)."""
    if all(ord(c) < 128 for c in s):
        sh("shell", "input", "text", _escape(s))
    else:
        sh("shell", "ime", "set", "com.android.adbkeyboard/.AdbIME")
        time.sleep(1.2)
        sh("shell", "am broadcast -a ADB_INPUT_TEXT --es msg '%s'" % s.replace("'", ""))
        time.sleep(1.0)
        # restore 百度 so the app's send button + keyboard layout are standard
        sh("shell", "ime", "set", "com.baidu.input_mi/.ImeService")
    time.sleep(wait)


def send(wait=0.5):
    tap(*SEND_XY)
    time.sleep(wait)


def screencap(name):
    os.makedirs(WORK, exist_ok=True)
    p = os.path.join(WORK, name + ".png")
    sh("shell", "screencap", "-p", "/sdcard/%s.png" % name)
    sh("pull", "/sdcard/%s.png" % name, p)
    return p


def record_start(remote, seconds, bitrate=8000000, size="720x1600"):
    sh("shell", "rm", "-f", remote)
    cmd = [ADB, "shell", "screenrecord", "--bit-rate", str(bitrate), "--size", size,
           "--time-limit", str(int(seconds)), remote]
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def record_stop(proc, remote, local):
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        pass
    time.sleep(1.0)
    sh("shell", "pkill", "-INT", "-f", "screenrecord")
    time.sleep(1.5)
    sh("pull", remote, local)
    return local


def foreground():
    out = sh("shell", "dumpsys", "window")[1]
    for line in out.splitlines():
        if "mCurrentFocus" in line:
            return line.strip()
    return "?"
