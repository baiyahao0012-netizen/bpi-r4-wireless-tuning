#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Laptop-side receiver: reassemble L2 video, serve MJPEG + Q/A SSE, call Ollama.

Left panel: MJPEG of received frames. Right panel: question / answer stream.
Answers are streamed back over L2: first token immediately, then deltas.
"""
import argparse
import base64
import subprocess
import collections
import json
import os
import queue
import random
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fast_tx import PcapTx
from pcap_rx import PcapRx
from video_proto import FRAME_MAX, ack, answer, mac, parse, question

HTML = """<!doctype html><html><head><meta charset="utf-8"><title>RTC VLM</title>
<style>
body{background:#111;color:#ddd;font-family:system-ui;margin:0;display:flex;flex-direction:column;height:100vh}
#top{display:flex;align-items:center;gap:14px;padding:10px 14px;border-bottom:1px solid #333;background:#181818}
#btn{font-size:16px;padding:8px 22px;border-radius:6px;border:0;background:#2d8f4e;color:#fff;cursor:pointer}
#btn:disabled{background:#444;cursor:default}
#st{font-size:14px;color:#9ad}
#met{font-size:12px;color:#888;margin-left:auto}
#main{flex:1;display:flex;min-height:0}
#left{flex:1;display:flex;align-items:center;justify-content:center;border-right:1px solid #333}
#left img{max-width:100%;max-height:100%}
#right{width:44%;overflow-y:auto;padding:10px;font-size:13px}
.q{border:1px solid #444;border-radius:6px;margin:8px 0;padding:8px;background:#1a1a1a}
.meta{color:#888;font-size:11px}
.a{color:#8fd694;white-space:pre-wrap}
</style></head><body>
<div id="top"><button id="btn">开始测试</button><span id="st">空闲</span>
 <label style="font-size:13px;color:#ccc"><input type="checkbox" id="loss"> 模拟丢包30%</label><span id="met">frames 0 | lost 0 | queue 0</span></div>
<div id="main">
 <div id="left"><img id="v" src="/stream.mjpg"></div>
 <div id="right"><h3>Q/A（按时间追加）</h3><div id="log"></div></div>
</div>
<script>
const vid=document.getElementById('v');if(vid){vid.onerror=()=>{setTimeout(()=>{vid.src='/stream.mjpg?r='+Date.now();},1000);};}
const log=document.getElementById('log'),btn=document.getElementById('btn'),st=document.getElementById('st'),met=document.getElementById('met'),loss=document.getElementById('loss');
loss.onchange=()=>{fetch('/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({loss:loss.checked?0.3:0})});};
const es=new EventSource('/events');
es.onmessage=e=>{const d=JSON.parse(e.data);
  if(d.phase==='reset'){log.innerHTML='';window._cur=null;
    const v=document.getElementById('v');if(v)v.src='/stream.mjpg?r='+Date.now();
    st.textContent='新一轮（模型已重置）';met.textContent='frames 0 | lost 0 | queue 0 | 已答 0';}
  else if(d.phase==='start'){window._cur=document.createElement('div');window._cur.className='q';
    window._cur.innerHTML=`<div class="meta">#${d.qid} t=${d.t}s frame=${d.idx} ${d.miss?'(frame miss)':''}</div>
    <div><b>问：</b>${d.question}</div><div class="a" id="a${d.qid}"></div>`;
    log.appendChild(window._cur);}
  else if(d.phase==='first'){const el=document.getElementById('a'+d.qid);if(el)el.textContent=d.text;
    const m=window._cur?window._cur.querySelector('.meta'):null;if(m)m.textContent+=` | TTFT ${d.ttft_ms}ms`;}
  else if(d.phase==='delta'){const el=document.getElementById('a'+d.qid);if(el)el.textContent=(el.textContent||'')+d.text;}
  else if(d.phase==='final'){const el=document.getElementById('a'+d.qid);if(el)el.textContent=d.answer;
    const m=window._cur?window._cur.querySelector('.meta'):null;
    if(m)m.textContent+=` | model ${d.model_ms}ms | prompt ${d.prompt_eval_ms}ms/${d.prompt_eval_count}tok | gen ${d.eval_ms}ms/${d.eval_count}tok`;}
    if(d.empty){const el=document.getElementById('a'+d.qid);if(el)el.textContent='[EMPTY/截断] '+(d.answer||'');}
  else if(d.phase==='stats'){met.textContent=`frames ${d.frames} | lost ${d.lost} | 已答 ${d.answers||0} | 丢/重传/确认 ${d.ans_dropped||0}/${d.ans_retx||0}/${d.ans_acked||0}`;
    if(d.running){st.textContent=`运行中 ${d.elapsed_s||0}s`;btn.disabled=true;}
    else{st.textContent=d.last_msg||'空闲';btn.disabled=false;}}
};
btn.onclick=()=>{btn.disabled=true;st.textContent='启动中…';
  fetch('/start',{method:'POST'}).then(r=>r.json()).then(d=>{st.textContent=d.msg||'已启动';})
   .catch(e=>{st.textContent='启动失败 '+e;btn.disabled=false;});};
</script></body></html>"""


class State:
    def __init__(self, a):
        self.a = a
        self.src = mac(a.src_mac)
        self.dst = mac(a.dst_mac)
        self.tx = PcapTx(a.ip)
        self.frames = collections.OrderedDict()
        self.reasm = {}
        self.latest = None
        self.latest_seq = 0
        self.placeholder = base64.b64decode(
            '/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAP//////////////////////////////////////////'
            '//////////////////////////////////////////////////////////2wBDAf//'
            '//////////////////////////////////////////////////////////////wAARCAABAAEDASIA'
            'AhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAX/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/9oA'
            'DAMBAAIQAxAAAAF//8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABBQJ//8QAFBEBAAAA'
            'AAAAAAAAAAAAAAAAAP/aAAgBAwEBPwF//8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAgBAgEB'
            'PwF//8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQAGPwJ//8QAFBABAAAAAAAAAAAAAAAA'
            'AAAAAP/aAAgBAQABPyF//9oADAMBAAIAAwAAABD/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oA'
            'CAMDAQE/EH//xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oACAECAQE/EH//xAAUEAEAAAAAAAAA'
            'AAAAAAAAAAAA/9oACAEBAAE/EH//2Q==')
        self.stats = {"frames": 0, "frames_total": 0, "lost": 0, "frags": 0,
                      "questions": 0, "answers": 0, "empty": 0,
                      "ans_sent": 0, "ans_dropped": 0, "ans_retx": 0,
                      "ans_acked": 0, "ans_failed": 0}
        self.lost_ids = set()
        self.loss = a.loss
        self.outstanding = {}
        self.q = queue.Queue()
        self.clients = []
        self.lock = threading.RLock()
        self.ledger = open(a.ledger, "a", buffering=1, encoding="utf-8") if a.ledger else None
        self.running = True
        self.run = {"running": False, "started": 0.0, "tag": "", "last_msg": "空闲",
                    "last_result": None}
        self.run_lock = threading.Lock()

    def push(self, obj):
        line = "data: " + json.dumps(obj, ensure_ascii=False) + "\n\n"
        with self.lock:
            for q in list(self.clients):
                try:
                    q.put_nowait(line)
                except Exception:
                    pass

    def handle(self, raw):
        p = parse(raw)
        if not p:
            return
        if p["type"] == "ack":
            qid, seq = p["qid"], p["seq"]
            with self.run_lock:
                for key in [k for k in self.outstanding
                            if k[0] == qid and k[1] <= seq]:
                    self.outstanding.pop(key, None)
                    with self.lock:
                        self.stats["ans_acked"] += 1
            return
        if p["type"] == "video":
            self.stats["frags"] += 1
            idx = p["frame_idx"]
            r = self.reasm.get(idx)
            if r is None:
                r = {"pts": p["pts_us"], "total": p["frag_total"], "parts": {},
                     "t0": time.monotonic()}
                self.reasm[idx] = r
            r["parts"][p["frag_idx"]] = p["payload"]
            if len(r["parts"]) == r["total"]:
                data = b"".join(r["parts"][i] for i in range(r["total"]))
                del self.reasm[idx]
                with self.lock:
                    self.frames[idx] = {"pts": p["pts_us"], "jpeg": data,
                                        "t_recv": time.monotonic()}
                    while len(self.frames) > 400:
                        self.frames.popitem(last=False)
                    self.latest = self.frames[idx]
                    self.latest_seq += 1
                    self.stats["frames"] = len(self.frames)
                    self.stats["frames_total"] += 1
        elif p["type"] == "question":
            self.stats["questions"] += 1
            p["t_recv"] = time.monotonic_ns()
            self.q.put(p)


    def send_answer(self, qid, seq, flags, t2, text):
        frame = answer(self.dst, self.src, qid, seq, flags, t2, text)
        key = (qid, seq)
        with self.run_lock:
            self.outstanding[key] = {"frame": frame, "attempts": 0,
                                     "last": time.monotonic()}
        self._emit_answer(key)

    def _emit_answer(self, key):
        rec = self.outstanding.get(key)
        if rec is None:
            return
        rec["attempts"] += 1
        rec["last"] = time.monotonic()
        if random.random() < self.loss:
            with self.lock:
                self.stats["ans_dropped"] += 1
            return
        try:
            self.tx.send(rec["frame"])
            with self.lock:
                self.stats["ans_sent"] += 1
        except Exception:
            pass

    def retx_loop(self):
        while self.running:
            now = time.monotonic()
            for key, rec in list(self.outstanding.items()):
                if now - rec["last"] < self.a.answer_timeout_ms / 1000.0:
                    continue
                if rec["attempts"] > self.a.max_resend:
                    self.outstanding.pop(key, None)
                    with self.lock:
                        self.stats["ans_failed"] += 1
                    continue
                with self.lock:
                    self.stats["ans_retx"] += 1
                self._emit_answer(key)
            time.sleep(0.02)

    def reset_for_run(self):
        """Clear the Q/A panel and all per-run counters; drop queued questions."""
        with self.lock:
            while True:
                try:
                    self.q.get_nowait()
                except queue.Empty:
                    break
            self.stats.update({"questions": 0, "answers": 0, "empty": 0,
                               "frames_total": 0, "lost": 0, "frags": 0,
                               "ans_sent": 0, "ans_dropped": 0, "ans_retx": 0,
                               "ans_acked": 0, "ans_failed": 0})
            self.outstanding.clear()
            self.lost_ids = set()
        self.push({"phase": "reset"})

    def unload_model(self):
        """Unload the model so the next run starts from a clean state."""
        import requests
        try:
            requests.post(self.a.ollama + "/api/generate",
                          json={"model": self.a.model, "keep_alive": 0,
                                "prompt": ""}, timeout=15)
            print("MODEL_UNLOADED %s" % self.a.model, flush=True)
        except Exception as exc:
            print("MODEL_UNLOAD_FAIL %s" % exc, flush=True)

    def start_run(self):
        with self.run_lock:
            if self.run["running"]:
                return False, "已在运行"
            a = self.a
            tag = time.strftime("%H%M%S")
            remote = ("cd /tmp && sudo -S python3 %s --loop %d --seconds %d "
                      "--preload --out /tmp/run_%s.json" %
                      (a.tx_script, a.tx_loop, a.tx_seconds, tag))
            cmd = ["ssh", "-i", a.ssh_key, "-o", "BatchMode=yes",
                   "-o", "StrictHostKeyChecking=accept-new",
                   "%s@%s" % (a.pi_user, a.pi_host), remote]
            self.run.update({"running": True, "started": time.monotonic(),
                             "tag": tag, "last_msg": "运行中"})
            self.reset_for_run()

            def worker():
                out = ""
                self.unload_model()
                try:
                    p = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.STDOUT, text=True,
                                         encoding="utf-8", errors="replace")
                    out = p.communicate(input=a.sudo_pass + "\n",
                                        timeout=a.tx_seconds + 60)[0] or ""
                    res = None
                    for line in out.splitlines():
                        if line.startswith("RESULT "):
                            try:
                                res = json.loads(line[7:])
                            except Exception:
                                pass
                    with self.run_lock:
                        self.run["last_result"] = res
                        self.run["last_msg"] = "完成 %s" % tag
                except Exception as exc:
                    with self.run_lock:
                        self.run["last_msg"] = "失败: %s" % exc
                finally:
                    with self.run_lock:
                        self.run["running"] = False
                    print("RUN_END %s %s" % (self.run["tag"], out[-300:]), flush=True)

            threading.Thread(target=worker, daemon=True).start()
            return True, "已启动 %s" % tag


def capture_loop(st, rx):
    while st.running:
        try:
            raw = rx.next_packet()
        except OSError:
            time.sleep(0.01)
            continue
        if raw:
            st.handle(raw)


def expire_loop(st):
    while st.running:
        now = time.monotonic()
        with st.lock:
            for idx, r in list(st.reasm.items()):
                if now - r["t0"] > 0.5:
                    del st.reasm[idx]
                    if idx not in st.lost_ids:
                        st.lost_ids.add(idx)
                        st.stats["lost"] += 1
        time.sleep(0.05)


def get_frame(st, idx, wait_ms=80):
    deadline = time.monotonic() + wait_ms / 1000.0
    while time.monotonic() < deadline:
        with st.lock:
            if idx in st.frames:
                return idx, st.frames[idx], False
        time.sleep(0.005)
    with st.lock:
        lower = [k for k in st.frames if k <= idx]
        if lower:
            k = max(lower)
            return k, st.frames[k], True
    return None, None, True


def ollama_stream(st, p, idx_used, fr, miss, b64):
    a = st.a
    import requests
    qid = p["qid"]
    text = p["text"]
    t1_ns = p["t_recv"]
    t0_ns = p.get("t0_ns")
    frame_age_ms = round(t1_ns / 1e9 - fr["t_recv"], 3) * 1000 if fr else None
    # no_think + short answer: keep the generation budget for visible tokens
    prompt = ("/no_think 请仔细观察图片，用2到3句话回答下面的问题，并说明判断依据，总字数40到80字。问题：%s" % text)
    payload = {"model": a.model, "prompt": prompt, "images": [b64], "stream": True,
               "think": False,
               "options": {"num_predict": a.num_predict, "temperature": 0},
               "keep_alive": "10m"}
    t2 = None
    seq = 0
    buf = ""
    last_flush = time.monotonic()
    full = ""
    think_txt = ""
    metrics = {}
    print("ollama start qid=%s run=%s" % (qid, st.run.get("tag")), flush=True)
    try:
        with requests.post(a.ollama + "/api/generate", json=payload, stream=True,
                           timeout=180) as r:
            for line in r.iter_lines(decode_unicode=True):
                if not line:
                    continue
                d = json.loads(line)
                delta = d.get("response") or ""
                think_txt += d.get("thinking") or ""
                now = time.monotonic_ns()
                if delta and t2 is None:
                    t2 = now
                    full += delta
                    st.send_answer(qid, seq, 1, t2, delta)
                    seq += 1
                    st.push({"phase": "first", "qid": qid, "text": delta,
                             "ttft_ms": round((t2 - t1_ns) / 1e6, 1)})
                elif delta:
                    full += delta
                    buf += delta
                    if time.monotonic() - last_flush > 0.03:
                        st.send_answer(qid, seq, 0, t2, buf)
                        seq += 1
                        st.push({"phase": "delta", "qid": qid, "text": buf})
                        buf = ""
                        last_flush = time.monotonic()
                if d.get("done"):
                    metrics = {k: d.get(k) for k in (
                        "total_duration", "load_duration", "prompt_eval_count",
                        "prompt_eval_duration", "eval_count", "eval_duration")}
                    break
    except Exception as exc:
        import traceback
        traceback.print_exc()
        metrics = {"error": str(exc)}
    if buf:
        st.tx.send(answer(st.dst, st.src, qid, seq, 0, t2 or 0, buf))
        seq += 1
        st.push({"phase": "delta", "qid": qid, "text": buf})
    st.send_answer(qid, seq, 2, t2 or 0, "")
    mj = {k: (round(v / 1e6, 1) if isinstance(v, int) and k.endswith("duration") else v)
          for k, v in metrics.items()}
    empty = not full.strip()
    model_ms = round((time.monotonic_ns() - t1_ns) / 1e6, 1)
    if empty:
        st.stats["empty"] += 1
    st.push({"phase": "final", "qid": qid, "answer": full, "empty": empty,
             "model_ms": model_ms,
             "thinking_chars": len(think_txt),
             "prompt_eval_ms": mj.get("prompt_eval_duration"),
             "prompt_eval_count": mj.get("prompt_eval_count"),
             "eval_ms": mj.get("eval_duration"),
             "eval_count": mj.get("eval_count"),
             "ttft_ms": round((t2 - t1_ns) / 1e6, 1) if t2 else None})
    st.stats["answers"] += 1
    if st.ledger:
        st.ledger.write(json.dumps({
            "run_tag": st.run.get("tag"), "qid": qid,
            "frame_idx_req": p["frame_idx"], "idx_used": idx_used,
            "frame_miss": miss, "frame_age_ms": frame_age_ms,
            "t0_ns": t0_ns, "t1_ns": t1_ns, "t2_ns": t2,
            "ttft_ms": round((t2 - t1_ns) / 1e6, 1) if t2 else None,
            "model_ms": model_ms, "empty": empty,
            "thinking_chars": len(think_txt), "answer": full,
            "metrics": mj}, ensure_ascii=False) + "\n")

def question_loop(st):
    while st.running:
        try:
            p = st.q.get(timeout=0.2)
        except queue.Empty:
            continue
        idx, fr, miss = get_frame(st, p["frame_idx"])
        if fr is None:
            st.push({"phase": "start", "qid": p["qid"], "t": p["pts_us"] / 1e6,
                     "idx": p["frame_idx"], "question": p["text"], "miss": True})
            st.stats["answers"] += 1
            if st.ledger:
                st.ledger.write(json.dumps({
                    "run_tag": st.run.get("tag"), "qid": p["qid"],
                    "frame_idx_req": p["frame_idx"], "idx_used": None,
                    "frame_miss": True, "empty": True,
                    "error": "frame_missing", "answer": ""},
                    ensure_ascii=False) + "\n")
            continue
        b64 = base64.b64encode(fr["jpeg"]).decode()
        st.push({"phase": "start", "qid": p["qid"], "t": p["pts_us"] / 1e6,
                 "idx": idx, "question": p["text"], "miss": miss,
                 "frame_age_ms": round(p["t_recv"] / 1e9 - fr["t_recv"], 3) * 1000})
        ollama_stream(st, p, idx, fr, miss, b64)

def make_handler(st):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            if self.path == "/config":
                try:
                    n = int(self.headers.get("Content-Length", "0"))
                    cfg = json.loads(self.rfile.read(n) or b"{}")
                    st.loss = float(cfg.get("loss", st.loss))
                except Exception as exc:
                    st.loss = 0.0
                body = json.dumps({"loss": st.loss}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if self.path == "/start":
                ok, msg = st.start_run()
                body = json.dumps({"ok": ok, "msg": msg}, ensure_ascii=False).encode()
                self.send_response(200 if ok else 409)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_response(404)
            self.end_headers()

        def do_GET(self):
            if self.path == "/":
                body = HTML.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if self.path == "/stream.mjpg":
                self.send_response(200)
                self.send_header("Content-Type",
                                 "multipart/x-mixed-replace; boundary=frame")
                self.end_headers()
                try:
                    with st.lock:
                        fr0 = st.latest
                    img0 = fr0["jpeg"] if fr0 else st.placeholder
                    self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n"
                                     b"Content-Length: %d\r\n\r\n" % len(img0))
                    self.wfile.write(img0)
                    self.wfile.write(b"\r\n")
                    self.wfile.flush()
                except Exception:
                    return
                last = -1
                while st.running:
                    with st.lock:
                        seq = st.latest_seq
                        fr = st.latest
                    if fr and seq != last:
                        last = seq
                        try:
                            self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n"
                                             b"Content-Length: %d\r\n\r\n" % len(fr["jpeg"]))
                            self.wfile.write(fr["jpeg"])
                            self.wfile.write(b"\r\n")
                            self.wfile.flush()
                        except Exception:
                            return
                    time.sleep(0.06)
                return
            if self.path == "/events":
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                q = queue.Queue()
                with st.lock:
                    st.clients.append(q)
                try:
                    while st.running:
                        try:
                            msg = q.get(timeout=0.5)
                        except queue.Empty:
                            msg = "data: " + json.dumps(
                                {"phase": "stats", "frames": st.stats["frames_total"],
                                 "lost": st.stats["lost"],
                                 "queue": st.q.qsize(),
                                 "answers": st.stats["answers"],
                                 "empty": st.stats["empty"], "loss": st.loss,
                                 "ans_sent": st.stats["ans_sent"],
                                 "ans_dropped": st.stats["ans_dropped"],
                                 "ans_retx": st.stats["ans_retx"],
                                 "ans_acked": st.stats["ans_acked"],
                                 "ans_failed": st.stats["ans_failed"],
                                 "running": st.run["running"],
                                 "elapsed_s": int(time.monotonic() - st.run["started"]) if st.run["running"] else 0,
                                 "last_msg": st.run["last_msg"]}) + "\n\n"
                        self.wfile.write(msg.encode())
                        self.wfile.flush()
                except Exception:
                    pass
                finally:
                    with st.lock:
                        if q in st.clients:
                            st.clients.remove(q)
                return
            self.send_response(404)
            self.end_headers()
    return H


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ip", default="192.168.240.2")
    ap.add_argument("--src-mac", default="40:c2:ba:52:70:95")
    ap.add_argument("--dst-mac", default="90:de:80:1c:6a:7a")
    ap.add_argument("--ollama", default="http://127.0.0.1:11434")
    ap.add_argument("--model", default="qwen3-vl:2b")
    ap.add_argument("--num-predict", type=int, default=400)
    ap.add_argument("--loss", type=float, default=0.0)
    ap.add_argument("--answer-timeout-ms", type=float, default=400.0)
    ap.add_argument("--max-resend", type=int, default=8)
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--bind", default="127.0.0.1")
    ap.add_argument("--ledger", default="")
    ap.add_argument("--seconds", type=float, default=0, help="0 = run until Ctrl-C")
    ap.add_argument("--pi-host", default="192.168.240.153")
    ap.add_argument("--pi-user", default="bai")
    ap.add_argument("--ssh-key", default="C:/Users/15732/.ssh/id_ed25519_pi_rtc")
    ap.add_argument("--sudo-pass", default="12345678")
    ap.add_argument("--tx-script", default="/tmp/video_tx.py")
    ap.add_argument("--tx-seconds", type=float, default=122)
    ap.add_argument("--tx-loop", type=int, default=1)
    a = ap.parse_args()
    st = State(a)
    import base64 as _b64, requests as _rq
    png = _b64.b64encode(bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360000002000154a24f6f0000000049454e44ae426082")).decode()
    t_w = time.monotonic()
    try:
        _rq.post(a.ollama + "/api/generate", json={"model": a.model, "prompt": "warmup",
                "images": [png], "stream": False, "options": {"num_predict": 1}},
                timeout=300)
        print("WARMUP %.1fs" % (time.monotonic() - t_w), flush=True)
    except Exception as exc:
        print("WARMUP_FAIL %s" % exc, flush=True)
    rx = PcapRx(a.ip, bpf="ether proto 0x88b5 or ether proto 0x88b6 or ether proto 0x88b8")
    ts = [threading.Thread(target=capture_loop, args=(st, rx), daemon=True),
          threading.Thread(target=expire_loop, args=(st,), daemon=True),
          threading.Thread(target=question_loop, args=(st,), daemon=True),
          threading.Thread(target=st.retx_loop, daemon=True)]
    for t in ts:
        t.start()
    srv = ThreadingHTTPServer((a.bind, a.port), make_handler(st))
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    print("READY http://127.0.0.1:%d/ frames=%d" % (a.port, 0), flush=True)
    try:
        if a.seconds > 0:
            time.sleep(a.seconds)
        else:
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        pass
    st.running = False
    res = {"role": "laptop-rx", "frames_seen": st.stats["frames"],
           "frags": st.stats["frags"], "lost": st.stats["lost"],
           "questions": st.stats["questions"]}
    print("RESULT " + json.dumps(res, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()





