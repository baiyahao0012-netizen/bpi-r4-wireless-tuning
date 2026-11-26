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
from reliable import ReliableBuffer
from pcap_rx import PcapRx
from video_proto import FRAME_MAX, ack, answer, mac, parse, question

HTML = """<!doctype html><html><head><meta charset="utf-8"><title>RTC-VLM</title>
<style>
:root{--bg:#0e1013;--panel:#15181d;--panel2:#1b1f26;--line:#262b33;--txt:#e6e9ef;
      --muted:#8b93a1;--accent:#38a169;--accent2:#4c9be8;--warn:#e8a04c;--bad:#e05c5c}
*{box-sizing:border-box}
html,body{height:100%}
body{margin:0;background:var(--bg);color:var(--txt);font-family:"Segoe UI",system-ui,-apple-system,"Microsoft YaHei",sans-serif;display:flex;flex-direction:column;overflow:hidden}
#top{display:flex;align-items:center;gap:14px;padding:10px 18px;background:linear-gradient(180deg,#191d23,#14171c);border-bottom:1px solid var(--line);white-space:nowrap;overflow-x:auto}
.brand{font-weight:700;font-size:16px;letter-spacing:.3px;display:flex;align-items:baseline;gap:8px}
.brand span{font-weight:400;font-size:11px;color:var(--muted)}
.controls{display:flex;align-items:center;gap:12px;margin-left:auto}
button{font-family:inherit;cursor:pointer;border:0;border-radius:8px;transition:.15s}
#btn{min-width:118px;padding:9px 20px;font-size:14px;font-weight:600;color:#fff;background:var(--accent);white-space:nowrap;box-shadow:0 2px 8px rgba(56,161,105,.25)}
#btn:hover{filter:brightness(1.08)}
#btn.stop{background:var(--bad);box-shadow:0 2px 8px rgba(224,92,92,.25)}
#btn:disabled{opacity:.55;cursor:default}
.ghost{background:var(--panel2);color:var(--txt);border:1px solid var(--line);padding:7px 14px;font-size:12px}
.ghost:hover{border-color:#3a4150}
.chip{font-size:12px;color:var(--muted);background:var(--panel2);border:1px solid var(--line);padding:6px 10px;border-radius:999px;white-space:nowrap}
.chip.on{color:var(--accent)}
label.chk{display:flex;align-items:center;gap:6px;font-size:12px;color:var(--muted);white-space:nowrap}
input[type=checkbox]{accent-color:var(--accent)}
.group{display:flex;align-items:center;gap:6px;font-size:12px;color:var(--muted);white-space:nowrap}
select,input[type=number]{background:var(--panel2);color:var(--txt);border:1px solid var(--line);border-radius:6px;padding:6px 8px;font-size:12px;font-family:inherit}
input[type=number]{width:58px}
#main{flex:1;display:grid;grid-template-columns:minmax(0,58%) minmax(0,42%);grid-template-rows:minmax(0,1fr);min-height:0;overflow:hidden}
#left{display:flex;flex-direction:column;min-width:0;min-height:0;overflow:hidden;border-right:1px solid var(--line)}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:10px;margin:10px 10px 0;overflow:hidden}
.panel.video{flex:0 0 auto;position:relative;background:#000;display:flex;align-items:center;justify-content:center;padding:0}
.panel.video img{display:block;max-width:none;max-height:none}
.badge{position:absolute;left:10px;top:10px;font-size:11px;color:#cfd6e2;background:rgba(0,0,0,.55);border:1px solid rgba(255,255,255,.08);padding:4px 8px;border-radius:6px;backdrop-filter:blur(4px)}
.panel.charts{flex:1 1 auto;margin-bottom:10px;padding:10px 12px;display:flex;flex-direction:column;gap:6px;min-height:0;overflow:hidden}
.chart-head{display:flex;align-items:baseline;justify-content:space-between}
.chart-head h3{margin:0;font-size:12px;font-weight:600;color:var(--muted);letter-spacing:.4px;text-transform:uppercase}
.chart-head span{font-size:12px;color:var(--accent2);font-variant-numeric:tabular-nums}
canvas{width:100%;max-width:100%;display:block;background:#0b0d10;border-radius:6px}
#fps{height:64px}#ttft{height:54px}
.metrics{display:flex;flex-wrap:wrap;gap:6px;margin-top:2px}
.m{font-size:11px;color:var(--muted);background:var(--panel2);border:1px solid var(--line);border-radius:6px;padding:4px 8px;white-space:nowrap;font-variant-numeric:tabular-nums}
.m b{color:var(--txt);font-weight:600}
#right{display:flex;flex-direction:column;min-width:0;min-height:0;overflow:hidden}
.right-head{display:flex;align-items:center;justify-content:space-between;padding:12px 14px 6px}
.right-head h3{margin:0;font-size:14px}
#met{font-size:11px;color:var(--muted);white-space:nowrap}
#log{flex:1;min-height:0;overflow-y:auto;padding:4px 14px 16px;scroll-behavior:smooth}
#log::-webkit-scrollbar,body::-webkit-scrollbar{width:8px;height:8px}
#log::-webkit-scrollbar-thumb,body::-webkit-scrollbar-thumb{background:#2c333d;border-radius:4px}
.q{background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--accent);border-radius:8px;margin:0 0 10px;padding:10px 12px}
.q .meta{font-size:11px;color:var(--muted);display:flex;flex-wrap:wrap;gap:8px;margin-bottom:6px;font-variant-numeric:tabular-nums}
.q .meta .tag{background:var(--panel2);border:1px solid var(--line);border-radius:5px;padding:1px 6px}
.qq{font-size:13px;color:#dfe6f0;margin:2px 0 6px}
.a{font-size:13px;line-height:1.55;color:#9fe0b0;white-space:pre-wrap;min-height:18px}
.a.streaming::after{content:"▋";color:var(--accent);margin-left:2px;animation:blink 1s steps(1) infinite}
@keyframes blink{50%{opacity:0}}
.sparkwrap{margin-top:8px}
.sparklab{font-size:10px;color:var(--muted);margin-bottom:2px;font-variant-numeric:tabular-nums}
.spark{height:34px}
</style></head><body>
<div id="top">
  <div class="brand">RTC·VLM <span>L2 实时视觉问答</span></div>
  <div class="controls">
    <button id="btn">开始测试</button>
    <span id="st" class="chip">空闲</span>
    <label class="chk"><input type="checkbox" id="loss"> 模拟丢包 30%</label>
    <span class="group">调度<select id="smode"><option value="off">关</option><option value="fifo">fifo</option><option value="ai-first">ai-first</option><option value="quota">quota</option></select></span>
    <span class="group">背景流<input id="sbulk" type="number" value="20"><span>Mbps</span></span>
    <button id="sapply" class="ghost">应用</button>
  </div>
</div>
<div id="main">
  <section id="left">
    <div class="panel video"><img id="v" src="/frame.jpg"><div class="badge" id="vbadge">等待视频</div></div>
    <div class="panel charts">
      <div class="chart-head"><h3>帧率 FPS</h3><span id="fpsnow">–</span></div>
      <canvas id="fps" width="900" height="64"></canvas>
      <div class="chart-head"><h3>首块时延 TTFT</h3><span id="ttftnow">–</span></div>
      <canvas id="ttft" width="900" height="54"></canvas>
      <div class="metrics" id="met2"></div>
    </div>
  </section>
  <section id="right">
    <div class="right-head"><h3>问答流</h3><span id="met">—</span></div>
    <div id="log"></div>
  </section>
</div>
<script>
const $=id=>document.getElementById(id);
const btn=$('btn'),st=$('st'),met=$('met'),met2=$('met2'),loss=$('loss'),smode=$('smode'),sbulk=$('sbulk'),sapply=$('sapply'),
      vbadge=$('vbadge'),fpsnow=$('fpsnow'),ttftnow=$('ttftnow'),
      cvF=$('fps'),cxF=cvF.getContext('2d'),cvT=$('ttft'),cxT=cvT.getContext('2d');
function fit(cv){const r=cv.getBoundingClientRect(),d=window.devicePixelRatio||1;
  if(cv.width!==Math.round(r.width*d)||cv.height!==Math.round(r.height*d)){cv.width=Math.round(r.width*d);cv.height=Math.round(r.height*d);}return d;}
function drawLine(cv,cx,arr,color,fill){const d=fit(cv),W=cv.width,H=cv.height;cx.clearRect(0,0,W,H);
  cx.strokeStyle='#1f242c';cx.lineWidth=1;for(let i=1;i<4;i++){const y=H*i/4;cx.beginPath();cx.moveTo(0,y);cx.lineTo(W,y);cx.stroke();}
  if(!arr||!arr.length)return;const mx=Math.max(1,...arr);
  const X=i=>i*(W-4)/Math.max(1,arr.length-1)+2, Y=v=>H-3-(v/mx)*(H-8);
  cx.beginPath();arr.forEach((v,i)=>{i?cx.lineTo(X(i),Y(v)):cx.moveTo(X(i),Y(v));});
  if(fill){cx.lineTo(X(arr.length-1),H);cx.lineTo(X(0),H);cx.closePath();cx.fillStyle=fill;cx.fill();cx.beginPath();
    arr.forEach((v,i)=>{i?cx.lineTo(X(i),Y(v)):cx.moveTo(X(i),Y(v));});}
  cx.strokeStyle=color;cx.lineWidth=2*d;cx.stroke();}
function drawSpark(cv,arr){const d=fit(cv),cx=cv.getContext('2d'),W=cv.width,H=cv.height;cx.clearRect(0,0,W,H);
  if(!arr||!arr.length)return;const mx=Math.max(1,...arr),bw=Math.max(1,(W-4)/arr.length);
  for(let i=0;i<arr.length;i++){const h=(arr[i]/mx)*(H-4);cx.fillStyle=arr[i]>mx*0.66?'#e8a04c':(arr[i]>mx*0.33?'#4c9be8':'#38a169');
    cx.fillRect(2+i*bw,H-2-h,Math.max(1,bw-1),h);}
  const lab=cv.parentElement.querySelector('.sparklab');
  if(lab)lab.textContent=`块间隔 n=${arr.length} · 中位 ${median(arr).toFixed(1)}ms · 最大 ${mx.toFixed(1)}ms`;}
function median(a){const s=[...a].sort((x,y)=>x-y),m=s.length>>1;return s.length%2?s[m]:(s[m-1]+s[m])/2;}
function fmt(v){return v===undefined||v===null?'-':v;}
const gaps={};
const vid=$('v');
if(vid){setInterval(()=>{const im=new Image();im.onload=()=>{vid.src=im.src;};im.src='/frame.jpg?t='+Date.now();},50);}

function layout(){
  const left=document.getElementById('left');
  const vp=document.querySelector('.panel.video');
  const ch=document.querySelector('.panel.charts');
  const im=document.getElementById('v');
  if(!left||!vp||!ch||!im)return;
  const m=10, chartsMin=268;
  const availW=Math.max(160,left.clientWidth-2*m);
  const availH=Math.max(90,left.clientHeight-2*m-chartsMin);
  let w=availW, h=Math.round(w*9/16);
  if(h>availH){ h=availH; w=Math.round(h*16/9); }
  vp.style.height=h+'px';
  im.style.width=w+'px'; im.style.height=h+'px';
  ch.style.height=Math.max(chartsMin,left.clientHeight-h-2*m)+'px';
}
window.addEventListener('resize',layout);
setTimeout(layout,60);
setInterval(layout,1000);
btn.onclick=()=>{const running=btn.textContent.indexOf('停止')>=0;btn.disabled=true;st.textContent=running?'停止中…':'启动中…';
  fetch(running?'/stop':'/start',{method:'POST'}).then(r=>r.json()).then(d=>{st.textContent=d.msg||'';btn.disabled=false;})
   .catch(e=>{st.textContent='失败 '+e;btn.disabled=false;});};
loss.onchange=()=>{fetch('/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({loss:loss.checked?0.3:0})});};
sapply.onclick=()=>{fetch('/sched',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mode:smode.value,rate:50,bulk:parseFloat(sbulk.value||'0')})});};
const es=new EventSource('/events');
es.onmessage=e=>{const d=JSON.parse(e.data);
  if(d.phase==='reset'){ $('log').innerHTML=''; st.textContent='新一轮（模型已重置）'; }
  else if(d.phase==='start'){
    const card=document.createElement('div');card.className='q';card.dataset.t=d.t;card.dataset.idx=d.idx;
    card.innerHTML=`<div class="meta"><span class="tag">#${d.qid}</span><span class="tag">t=${d.t}s</span>
      <span class="tag">frame ${d.idx}</span>${d.miss?'<span class="tag" style="color:#e05c5c">frame miss</span>':''}</div>
      <div class="qq">${d.question}</div><div class="a streaming" id="a${d.qid}"></div>
      <div class="sparkwrap"><div class="sparklab">等待首块…</div><canvas class="spark" id="s${d.qid}" width="720" height="34"></canvas></div>`;
    $('log').appendChild(card);gaps[d.qid]=[];$('log').scrollTop=$('log').scrollHeight;
  }
  else if(d.phase==='first'){const el=$('a'+d.qid);if(el)el.textContent=d.text;
    const c=$('a'+d.qid);if(c){const l=c.parentElement.querySelector('.sparklab');if(l)l.textContent='生成中…';}}
  else if(d.phase==='delta'){const el=$('a'+d.qid);if(el)el.textContent=(el.textContent||'')+d.text;}
  else if(d.phase==='final'){const el=$('a'+d.qid);
    if(el){el.textContent=d.empty?'[EMPTY/截断] '+(d.answer||''):d.answer;el.classList.remove('streaming');}
    const card=$('a'+d.qid)&&$('a'+d.qid).parentElement;
    if(card){const m=card.querySelector('.meta');const ds=card.dataset;
      m.innerHTML=`<span class="tag">#${d.qid}</span><span class="tag">t=${ds.t}s</span><span class="tag">frame ${ds.idx}</span>`+
        `<span class="tag">TTFT <b>${fmt(d.ttft_ms)}</b>ms</span><span class="tag">model ${fmt(d.model_ms)}ms</span>`+
        `<span class="tag">prompt ${fmt(d.prompt_eval_ms)}ms/${fmt(d.prompt_eval_count)}tok</span>`+
        `<span class="tag">gen ${fmt(d.eval_ms)}ms/${fmt(d.eval_count)}tok</span>`+
        (d.hit_cap?'<span class="tag" style="color:#e8a04c">截断</span>':'');}
    const cv=$('s'+d.qid);if(cv)drawSpark(cv,d.gaps_ms||[]);}
  else if(d.phase==='stats'){
    fpsnow.textContent=(d.fps||0)+' fps';
    ttftnow.textContent=(d.ttft_p50!==null&&d.ttft_p50!==undefined)?d.ttft_p50+' ms':'–';
    vbadge.textContent=`帧 ${d.frames} · 丢 ${d.lost} · fps ${d.fps||0}`;
    met.textContent=`发 ${d.ans_sent||0} · 丢 ${d.ans_dropped||0} · 重传 ${d.ans_retx||0} · 确认 ${d.ans_acked||0} · 过期 ${d.ans_failed||0} · 补救 ${d.recovery||0}%`;
    met2.innerHTML=[['发送',d.ans_sent],['丢失',d.ans_dropped],['重传',d.ans_retx],['确认',d.ans_acked],
      ['过期',d.ans_failed],['补救',(d.recovery||0)+'%'],['调度',d.sched_mode||'off'],['深度',d.sched_depth||0],
      ['越队',d.ai_jump||0],['驱逐',d.evicted||0],['ai/bulk',(d.sent_ai||0)+'/'+(d.sent_bulk||0)]]
      .map(([k,v])=>`<span class="m">${k} <b>${v}</b></span>`).join('');
    drawLine(cvF,cxF,d.fps_hist||[],'#38a169','rgba(56,161,105,.12)');
    drawLine(cvT,cxT,d.ttft_hist||[],'#e8a04c','rgba(232,160,76,.12)');
    if(d.running){st.textContent=`运行中 ${d.elapsed_s||0}s`;btn.textContent='停止测试';btn.classList.add('stop');btn.disabled=false;}
    else{st.textContent=d.last_msg||'空闲';btn.textContent='开始测试';btn.classList.remove('stop');btn.disabled=false;}
  }
};
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
        self.fps_hist = collections.deque(maxlen=120)
        self.sched_mode = "off"
        self.sched_rate = a.sched_rate_mbps
        self.bulk_mbps = a.bulk_mbps
        self.sched_cap = a.sched_capacity
        self.ai_q = collections.deque()
        self.bulk_q = collections.deque()
        self.q_keys = set()
        self.qseq = 0
        self.q_lock = threading.Lock()
        self.bulk_on = False
        self.drain_on = False
        self.sched_stats = {"depth": 0, "ai_jump": 0, "evicted": 0,
                            "sent_ai": 0, "sent_bulk": 0}
        self.frames_1s = 0
        self.ttfts = []
        self.outstanding = {}
        self.rbuf = ReliableBuffer(
            depth=a.buffer_depth, rto_ms=a.answer_timeout_ms,
            max_sends=a.max_resend + 1, on_send=self._tx_frame,
            ledger_path=(a.ledger + '.chunks.jsonl') if a.ledger else None)
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
            self.rbuf.on_ack(p["qid"], p["cum"], p["bitmap"])
            self._sync_rbuf()
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
                    self.frames_1s += 1
        elif p["type"] == "question":
            self.stats["questions"] += 1
            p["t_recv"] = time.monotonic_ns()
            self.q.put(p)


    def _tx_frame(self, key, frame):
        if self.sched_mode == "off":
            self._wire_send(frame)
            return
        with self.q_lock:
            if key is not None and key in self.q_keys:
                return
            self.qseq += 1
            if key is not None:
                self.q_keys.add(key)
            self.ai_q.append((self.qseq, key, frame))
            if self.sched_mode == "quota" and len(self.ai_q) + len(self.bulk_q) > self.sched_cap:
                if self.bulk_q:
                    self.bulk_q.popleft()
                    self.sched_stats["evicted"] += 1
            self._sync_sched()

    def _wire_send(self, frame):
        if random.random() < self.loss:
            with self.lock:
                self.stats["ans_dropped"] += 1
            return True
        try:
            self.tx.send(frame)
            return True
        except Exception:
            with self.lock:
                self.stats["send_fail"] += 1
            return False

    def _sync_sched(self):
        self.sched_stats["depth"] = len(self.ai_q) + len(self.bulk_q)
        with self.lock:
            self.stats["ai_jump"] = self.sched_stats["ai_jump"]
            self.stats["evicted"] = self.sched_stats["evicted"]

    def _pick_next(self):
        with self.q_lock:
            kind = None
            item = None
            if self.sched_mode in ("ai-first", "quota"):
                if self.ai_q:
                    kind, item = "ai", self.ai_q.popleft()
                    if self.bulk_q:
                        self.sched_stats["ai_jump"] += 1
                elif self.bulk_q:
                    kind, item = "bulk", self.bulk_q.popleft()
            else:  # fifo
                if self.ai_q and self.bulk_q:
                    if self.ai_q[0][0] < self.bulk_q[0][0]:
                        kind, item = "ai", self.ai_q.popleft()
                    else:
                        kind, item = "bulk", self.bulk_q.popleft()
                elif self.ai_q:
                    kind, item = "ai", self.ai_q.popleft()
                elif self.bulk_q:
                    kind, item = "bulk", self.bulk_q.popleft()
            if kind == "ai" and item is not None:
                self.q_keys.discard(item[1])
            self._sync_sched()
            return kind, item

    def drain_loop(self):
        rate = max(1.0, self.sched_rate) * 1e6 / 8.0
        tokens = 0.0
        last = time.monotonic()
        while self.running:
            now = time.monotonic()
            tokens = min(rate * 0.05, tokens + rate * (now - last))
            last = now
            kind, item = self._pick_next()
            if item is None:
                time.sleep(0.003)
                continue
            frame = item[2]
            if tokens < len(frame):
                with self.q_lock:
                    (self.ai_q if kind == "ai" else self.bulk_q).appendleft(item)
                time.sleep(0.002)
                continue
            tokens -= len(frame)
            ok = self._wire_send(frame)
            self.sched_stats["sent_" + kind] += 1
            if kind == "ai" and not ok and item[1] is not None:
                self.rbuf.retry_now(item[1])

    def bulk_loop(self):
        size = 1400
        while self.running:
            if not self.bulk_on:
                time.sleep(0.05)
                continue
            per_tick = max(1, int((self.bulk_mbps * 1e6 / 8.0) / size / 100))
            for _ in range(per_tick):
                frame = self.dst + self.src + (0x88B7).to_bytes(2, "big") + b"\x00" * (size - 14)
                with self.q_lock:
                    if len(self.bulk_q) >= self.sched_cap:
                        self.bulk_q.popleft()
                        self.sched_stats["evicted"] += 1
                    self.qseq += 1
                    self.bulk_q.append((self.qseq, None, frame))
                self._sync_sched()
            time.sleep(0.01)

    def set_sched(self, mode, rate=None, bulk=None):
        with self.q_lock:
            self.sched_mode = mode
            if rate is not None:
                self.sched_rate = rate
            if bulk is not None:
                self.bulk_mbps = bulk
            self.bulk_on = mode != "off" and (self.bulk_mbps or 0) > 0
            if not self.bulk_on:
                self.bulk_q.clear()
        if mode != "off" and not self.drain_on:
            self.drain_on = True
            threading.Thread(target=self.drain_loop, daemon=True).start()
        self._sync_sched()
        return {"mode": self.sched_mode, "rate": self.sched_rate,
                "bulk": self.bulk_mbps}

    def _sync_rbuf(self):
        s = self.rbuf.stats
        with self.lock:
            self.stats["ans_sent"] = s["sent"]
            self.stats["ans_acked"] = s["acked"]
            self.stats["ans_retx"] = s["retx"]
            self.stats["ans_failed"] = s["expired"]
            self.stats["ans_evicted"] = s["evicted"]

    def send_answer(self, qid, seq, flags, t2, text):
        self.rbuf.add(qid, seq, answer(self.dst, self.src, qid, seq, flags, t2, text))
        self._sync_rbuf()

    def retx_loop(self):
        while self.running:
            try:
                self.rbuf.tick()
                self._sync_rbuf()
            except Exception:
                pass
            time.sleep(0.02)

    def stop_run(self):
        with self.run_lock:
            if not self.run["running"]:
                return False, "未在运行"
            proc = self.run.get("proc")
            self.run["running"] = False
            self.run["last_msg"] = "已停止"
        if proc is not None:
            try:
                proc.terminate()
            except Exception:
                pass
        try:
            subprocess.Popen(["ssh", "-i", self.a.ssh_key, "-o", "BatchMode=yes",
                              "%s@%s" % (self.a.pi_user, self.a.pi_host),
                              "pkill -f video_tx.py"], stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
        self.push({"phase": "stats", "frames": self.stats["frames_total"],
                   "lost": self.stats["lost"], "queue": 0,
                   "answers": self.stats["answers"], "empty": self.stats["empty"],
                   "running": False, "last_msg": "已停止"})
        return True, "已停止"

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
                               "ans_acked": 0, "ans_failed": 0, "ans_evicted": 0,
                      "send_fail": 0})
            self.outstanding.clear()
            self.rbuf.clear()
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
                    self.run["proc"] = p
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


def fps_loop(st):
    while st.running:
        time.sleep(1.0)
        with st.lock:
            st.fps_hist.append(st.frames_1s)
            st.frames_1s = 0


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
    arrivals = []
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
                    arrivals.append(0.0)
                    full += delta
                    st.send_answer(qid, seq, 1, t2, delta)
                    seq += 1
                    st.push({"phase": "first", "qid": qid, "text": delta,
                             "ttft_ms": round((t2 - t1_ns) / 1e6, 1)})
                elif delta:
                    full += delta
                    arrivals.append(round((now - t2) / 1e6, 1))
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
    retried = False
    if not full.strip():
        retried = True
        p2 = dict(payload)
        p2["prompt"] = ("/no_think 只输出答案，不要思考过程，不超过30个字。问题：%s" % text)
        p2["options"] = {"num_predict": 200, "temperature": 0}
        print("ollama retry qid=%s (empty answer)" % qid, flush=True)
        try:
            with requests.post(a.ollama + "/api/generate", json=p2, stream=True,
                               timeout=180) as r2:
                for line in r2.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    d2 = json.loads(line)
                    delta2 = d2.get("response") or ""
                    now2 = time.monotonic_ns()
                    if delta2 and t2 is None:
                        t2 = now2
                        arrivals.append(0.0)
                        full += delta2
                        st.send_answer(qid, seq, 1, t2, delta2)
                        seq += 1
                        st.push({"phase": "first", "qid": qid, "text": delta2,
                                 "ttft_ms": round((t2 - t1_ns) / 1e6, 1)})
                    elif delta2:
                        full += delta2
                        arrivals.append(round((now2 - t2) / 1e6, 1))
                        buf += delta2
                        if time.monotonic() - last_flush > 0.03:
                            st.send_answer(qid, seq, 0, t2, buf)
                            seq += 1
                            st.push({"phase": "delta", "qid": qid, "text": buf})
                            buf = ""
                            last_flush = time.monotonic()
                    if d2.get("done"):
                        metrics = {k: d2.get(k) for k in (
                            "total_duration", "load_duration", "prompt_eval_count",
                            "prompt_eval_duration", "eval_count", "eval_duration")}
                        break
        except Exception as exc:
            print("ollama retry failed %s" % exc, flush=True)

    if buf:
        st.send_answer(qid, seq, 0, t2 or 0, buf)
        seq += 1
        st.push({"phase": "delta", "qid": qid, "text": buf})
    st.send_answer(qid, seq, 2, t2 or 0, "")
    mj = {k: (round(v / 1e6, 1) if isinstance(v, int) and k.endswith("duration") else v)
          for k, v in metrics.items()}
    hit_cap = bool(mj.get("eval_count") and
                   mj.get("eval_count") >= a.num_predict - 2)
    empty = not full.strip()
    model_ms = round((time.monotonic_ns() - t1_ns) / 1e6, 1)
    if empty:
        st.stats["empty"] += 1
    gaps = [round(arrivals[i] - arrivals[i - 1], 1) for i in range(1, len(arrivals))][:200]
    st.push({"phase": "final", "qid": qid, "answer": full, "empty": empty,
             "gaps_ms": gaps, "hit_cap": hit_cap, "retried": retried,
             "model_ms": model_ms,
             "thinking_chars": len(think_txt),
             "prompt_eval_ms": mj.get("prompt_eval_duration"),
             "prompt_eval_count": mj.get("prompt_eval_count"),
             "eval_ms": mj.get("eval_duration"),
             "eval_count": mj.get("eval_count"),
             "ttft_ms": round((t2 - t1_ns) / 1e6, 1) if t2 else None})
    if t2:
        st.ttfts.append(round((t2 - t1_ns) / 1e6, 1))
    st.stats["answers"] += 1
    if st.ledger:
        st.ledger.write(json.dumps({
            "run_tag": st.run.get("tag"), "qid": qid,
            "frame_idx_req": p["frame_idx"], "idx_used": idx_used,
            "frame_miss": miss, "frame_age_ms": frame_age_ms,
            "t0_ns": t0_ns, "t1_ns": t1_ns, "t2_ns": t2,
            "ttft_ms": round((t2 - t1_ns) / 1e6, 1) if t2 else None,
            "model_ms": model_ms, "empty": empty, "hit_cap": hit_cap, "retried": retried,
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
            if self.path == "/sched":
                try:
                    n2 = int(self.headers.get("Content-Length", "0"))
                    cfg = json.loads(self.rfile.read(n2) if n2 else b"{}")
                    out = st.set_sched(str(cfg.get("mode", "off")),
                                        float(cfg.get("rate", st.sched_rate)),
                                        float(cfg.get("bulk", st.bulk_mbps)))
                except Exception as exc:
                    out = {"error": str(exc)}
                body = json.dumps(out).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if self.path == "/stop":
                ok, msg = st.stop_run()
                body = json.dumps({"ok": ok, "msg": msg}, ensure_ascii=False).encode()
                self.send_response(200 if ok else 409)
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
            if self.path.startswith("/frame.jpg"):
                with st.lock:
                    fr = st.latest
                img = fr["jpeg"] if fr else st.placeholder
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(img)))
                self.end_headers()
                self.wfile.write(img)
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
                                 "send_fail": st.stats["send_fail"],
                                 "evicted": st.stats["ans_evicted"],
                                 "fps": st.fps_hist[-1] if st.fps_hist else 0,
                                 "fps_hist": list(st.fps_hist),
                                 "sched_mode": st.sched_mode, "sched_rate": st.sched_rate,
                                 "sched_bulk": st.bulk_mbps,
                                 "sched_depth": st.sched_stats["depth"],
                                 "ai_jump": st.sched_stats["ai_jump"],
                                 "evicted": st.sched_stats["evicted"],
                                 "sent_ai": st.sched_stats["sent_ai"],
                                 "sent_bulk": st.sched_stats["sent_bulk"],
                                 "ttft_hist": st.ttfts[-20:],
                                 "ttft_p50": (sorted(st.ttfts)[len(st.ttfts)//2] if st.ttfts else None),
                                 "recovery": (round(100.0 * st.rbuf.stats["acked"] /
                                               max(1, st.rbuf.stats["acked"] + st.rbuf.stats["expired"]), 1)),
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
    ap.add_argument("--num-predict", type=int, default=640)
    ap.add_argument("--loss", type=float, default=0.0)
    ap.add_argument("--answer-timeout-ms", type=float, default=400.0)
    ap.add_argument("--max-resend", type=int, default=8)
    ap.add_argument("--buffer-depth", type=int, default=64)
    ap.add_argument("--sched-rate-mbps", type=float, default=50.0)
    ap.add_argument("--sched-capacity", type=int, default=500)
    ap.add_argument("--bulk-mbps", type=float, default=0.0)
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
          threading.Thread(target=st.retx_loop, daemon=True),
          threading.Thread(target=fps_loop, args=(st,), daemon=True),
          threading.Thread(target=st.bulk_loop, daemon=True)]
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





