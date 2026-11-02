import json
import re
import subprocess
import time
import xml.etree.ElementTree as ET

ADB = r"D:\Desktop\AI 辅助对话\_work_recover\platform-tools\platform-tools\adb.exe"
PROMPT = "Explain why prioritizing short interactive messages can reduce response delay during Wi-Fi congestion."


def adb(*args, timeout=20):
    return subprocess.run([ADB, "shell", *args], capture_output=True, text=True, timeout=timeout)


def dump_nodes():
    adb("uiautomator", "dump", "/sdcard/ui.xml")
    subprocess.run([ADB, "pull", "/sdcard/ui.xml", r"D:\Desktop\AI 辅助对话\_work_recover\ui.xml"],
                   capture_output=True, timeout=20)
    root = ET.parse(r"D:\Desktop\AI 辅助对话\_work_recover\ui.xml").getroot()
    return [(n.get("class", ""), n.get("text", ""), n.get("resource-id", ""),
             n.get("content-desc", ""), n.get("bounds", "")) for n in root.iter("node")]


def center(bounds):
    x1, y1, x2, y2 = map(int, re.findall(r"\d+", bounds))
    return (x1 + x2) // 2, (y1 + y2) // 2


nodes = dump_nodes()
edit = next((b for c, _, rid, _, b in nodes if c == "android.widget.EditText" and rid.endswith("input_text")), None)
if not edit:
    raise SystemExit("Pilot stopped: chat input was not found; no phone UI action was taken.")

x, y = center(edit)
adb("input", "tap", str(x), str(y))
time.sleep(0.4)
adb("input", "text", PROMPT.replace(" ", "%s"))
time.sleep(0.5)
nodes = dump_nodes()
send = next((b for _, _, rid, _, b in nodes if rid.endswith("action_send")), None)
if send:
    x, y = center(send)
    adb("input", "tap", str(x), str(y))
else:
    raise SystemExit("Pilot stopped: send control was not found; prompt was not submitted.")

t0 = time.monotonic()
first_seen = None
last_change = t0
previous_texts = set()
response_text = ""
while time.monotonic() - t0 < 60:
    time.sleep(0.7)
    current = dump_nodes()
    texts = {t.strip() for _, t, _, _, _ in current if len(t.strip()) > 12}
    fresh = [t for t in texts if t != PROMPT and not PROMPT.startswith(t) and not t.startswith(PROMPT[:24])]
    if fresh and first_seen is None:
        first_seen = time.monotonic()
        response_text = fresh[0]
    if texts != previous_texts:
        last_change = time.monotonic()
        previous_texts = texts
        if fresh:
            response_text = max(fresh, key=len)
    if first_seen and time.monotonic() - last_change >= 4:
        break

result = {
    "prompt": PROMPT,
    "first_text_seconds": round(first_seen - t0, 2) if first_seen else None,
    "stable_seconds": round(time.monotonic() - t0, 2) if first_seen else None,
    "response_sample": response_text[:220] if first_seen else "no response text found",
    "ui_nodes": len(dump_nodes()),
}
print(json.dumps(result, ensure_ascii=False))
