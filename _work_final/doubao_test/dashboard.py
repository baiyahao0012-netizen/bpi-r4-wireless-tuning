# -*- coding: utf-8 -*-
"""AI-business dashboard: TTFB trend chart + AI flow metrics + accel toggle."""
import json, subprocess, sys, time, threading, struct, urllib.parse, collections, csv, os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ADB = r"D:\Desktop\AI 辅助对话\_work_recover\platform-tools\platform-tools\adb.exe"
BOARD = "root@192.168.240.1"
PHONE_MAC = "06:65:45:fc:44:3d"
PHONE_IP = "192.168.240.219"
IFACE = "phy0.1-ap0"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8099

AI_PORTS = {443, 9924, 8080}
AI_FILTER = "(port 443 or port 9924 or port 8080)"

_lock = threading.Lock()
flow_up = {}
ttfb_hist = []
ai = {"dl_bytes": 0, "ul_bytes": 0, "last": time.time(), "dl_rate": 0, "ul_rate": 0,
      "flows": 0, "ttfb_last": None, "ttfb_n": 0}

HIST = {"t": [], "ttfb": [], "aidl": [], "ef": [], "rtt": []}
HMAX = 60
HIST_LOCK = threading.Lock()
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dash_log.csv")
LOG_ON = [True]
LOG_LOCK = threading.Lock()

def log_row(d):
    if not LOG_ON[0]:
        return
    with LOG_LOCK:
        new = not os.path.exists(LOG_PATH)
        try:
            with open(LOG_PATH, "a", encoding="utf-8", newline="") as f:
                w = csv.writer(f)
                if new:
                    w.writerow(["time","accel","bg","bg_n","phone_kbs","ai_dl_kbs","ef_kbs","ttfb_last_ms","ttfb_p50_ms","ttfb_max_ms","ttfb_n","rtt_avg_ms","signal","tx_rate"])
                w.writerow([d.get("ts"), d.get("accel"), d.get("bg"), d.get("bg_n"),
                            round(d.get("phone_kbs") or 0, 2), round((d.get("ai") or {}).get("dl_kbs") or 0, 2),
                            round(d.get("ef_kbs") or 0, 2), round((d.get("ai") or {}).get("ttfb_last_ms") or 0, 1),
                            round((d.get("ai") or {}).get("ttfb_p50_ms") or 0, 1), round((d.get("ai") or {}).get("ttfb_max_ms") or 0, 1),
                            (d.get("ai") or {}).get("ttfb_n") or 0,
                            round((d.get("rtt") or {}).get("avg") or 0, 1) if d.get("rtt") else 0,
                            d.get("signal"), d.get("tx_rate")])
        except Exception:
            pass

def _canon(a, b):
    return tuple(sorted([a, b]))

def handle_packet(data, ts):
    try:
        if len(data) < 34: return
        if struct.unpack("!H", data[12:14])[0] != 0x0800: return
        ip = data[14:]
        ihl = (ip[0] & 0x0f) * 4
        proto = ip[9]
        src = ".".join(str(b) for b in ip[12:16])
        dst = ".".join(str(b) for b in ip[16:20])
        if src != PHONE_IP and dst != PHONE_IP: return
        l4 = ip[ihl:]
        if proto == 6:
            if len(l4) < 20: return
            sport, dport = struct.unpack("!HH", l4[0:4])
            plen = len(l4) - (l4[12] >> 4) * 4
        elif proto == 17:
            if len(l4) < 8: return
            sport, dport = struct.unpack("!HH", l4[0:4])
            plen = len(l4) - 8
        else:
            return
        if dport not in AI_PORTS and sport not in AI_PORTS: return
        key = _canon((src, sport), (dst, dport))
        down = (dst == PHONE_IP)
        with _lock:
            if down:
                ai["dl_bytes"] += plen
                if plen > 0:
                    t0 = flow_up.pop(key, None)
                    if t0 is not None:
                        dt = ts - t0
                        if 0.001 < dt < 5.0:
                            ttfb_hist.append(dt)
                            if len(ttfb_hist) > 300: del ttfb_hist[:150]
                            ai["ttfb_last"] = dt
                            ai["ttfb_n"] += 1
            else:
                ai["ul_bytes"] += plen
                if plen > 0:
                    flow_up[key] = ts
    except Exception:
        pass

def pcap_thread():
    while True:
        p = None
        try:
            cmd = "tcpdump -i br-lan -s 96 -w - 'host %s and %s' 2>/dev/null" % (PHONE_IP, AI_FILTER)
            p = subprocess.Popen(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=4", BOARD, cmd],
                                 stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            f = p.stdout
            if len(f.read(24)) < 24:
                time.sleep(2); continue
            while True:
                rh = f.read(16)
                if len(rh) < 16: break
                sec, usec, incl, orig = struct.unpack("<IIII", rh)
                data = f.read(incl)
                if len(data) < incl: break
                handle_packet(data, sec + usec / 1e6)
        except Exception:
            time.sleep(2)
        finally:
            try:
                if p: p.kill()
            except Exception: pass
            time.sleep(1)

def window_reset():
    now = time.time()
    with _lock:
        dt = max(0.2, now - ai["last"])
        ai["dl_rate"] = ai["dl_bytes"] / dt
        ai["ul_rate"] = ai["ul_bytes"] / dt
        ai["flows"] = len(flow_up)
        ai["dl_bytes"] = 0; ai["ul_bytes"] = 0; ai["last"] = now
        snap = dict(ai)
        snap["ttfb_p50"] = sorted(ttfb_hist)[len(ttfb_hist)//2] if ttfb_hist else None
        snap["ttfb_max"] = max(ttfb_hist) if ttfb_hist else None
        return snap

def run(args, timeout=12):
    try:
        r = subprocess.run(args, capture_output=True, timeout=timeout)
        return r.stdout.decode("utf-8", "replace")
    except Exception:
        return ""

def board(cmd, timeout=12):
    return run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=4", BOARD, cmd], timeout)

def phone(cmd, timeout=12):
    return run([ADB, "shell", cmd], timeout)

def parse_station(dump):
    out = {"tx_bytes": None, "signal": None, "tx_bitrate": None}
    cur = False
    for line in dump.splitlines():
        if line.startswith("Station "):
            cur = PHONE_MAC in line
        elif cur:
            if "tx bytes:" in line:
                try: out["tx_bytes"] = int(line.split(":")[1].strip())
                except: pass
            elif "signal:" in line and "avg" not in line and "last ack" not in line:
                try: out["signal"] = int(line.split(":")[1].split()[0])
                except: pass
            elif "tx bitrate:" in line:
                out["tx_bitrate"] = line.split(":", 1)[1].strip()
    return out

def nft_ef():
    txt = board("nft list table ip oaf_accel 2>/dev/null")
    b = 0
    for line in txt.splitlines():
        if "counter packets" in line and "dscp set ef" in line:
            try: b += int(line.split("counter packets")[1].split("bytes")[1].split()[0])
            except: pass
    return b

def accel_state():
    return "table ip oaf_accel" in board("nft list tables 2>/dev/null", timeout=20)

def rtt():
    out = board("ping -c 3 -W 1 %s 2>/dev/null" % PHONE_IP, timeout=8)
    for line in out.splitlines():
        if "min/avg/max" in line:
            try:
                n = line.split("=")[1].strip().split("/")
                return {"min": float(n[0]), "avg": float(n[1]), "max": float(n[2]), "mdev": float(n[3])}
            except: pass
    return None

BG_SCRIPT = r"D:\Desktop\AI 辅助对话\_work_final\doubao_test\udpflood.py"
BGLOAD = r"D:\Desktop\AI 辅助对话\_work_final\doubao_test\bgload.py"
BGSTA_PROCS = []
BG_PROCS = []
BG_N = [0]
BG_LOCK = threading.Lock()

def start_bg(n):
    with BG_LOCK:
        stop_bg_locked()
        try:
            p = subprocess.Popen([sys.executable, BG_SCRIPT, PHONE_IP, "9999", "3600", "192.168.240.2", str(int(n))],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            BG_PROCS.append(p)
        except Exception:
            pass
        BG_N[0] = int(n)
        return int(n)

def stop_bg_locked():
    global BG_PROCS
    for p in BG_PROCS:
        try: p.kill()
        except Exception: pass
    BG_PROCS = []
    BG_N[0] = 0

def stop_bg():
    with BG_LOCK:
        stop_bg_locked()

def start_bgsta(n):
    with BG_LOCK:
        stop_bgsta_locked()
        ips = ["192.168.240.126", "192.168.240.147"][:max(1, min(2, int(n)))]
        for ip in ips:
            try:
                p = subprocess.Popen([sys.executable, BGLOAD, ip, "10", "3600"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                BGSTA_PROCS.append(p)
            except Exception:
                pass
        return len(BGSTA_PROCS)

def stop_bgsta_locked():
    global BGSTA_PROCS
    for p in BGSTA_PROCS:
        try: p.kill()
        except Exception: pass
    BGSTA_PROCS = []

def bgsta_state():
    with BG_LOCK:
        return len(BGSTA_PROCS) > 0, len(BGSTA_PROCS)

def bg_apply(on, n):
    if on: start_bg(n)
    else: stop_bg()

def bg_state():
    with BG_LOCK:
        return len(BG_PROCS) > 0, BG_N[0]

def cap_on(on):
    if on:
        board("echo 0 > /sys/kernel/debug/ieee80211/phy0/mt76/force_rate")
    else:
        return {"cap6m": True, "note": "force_rate 无法软复位，需重启板子才能恢复自动速率"}
    return {"cap6m": True}

def set_accel(on):
    if on:
        out = board("sh /root/oaf_accel.sh install >/dev/null 2>&1; nft add rule ip oaf_accel post ct mark and 0xffff == 0x000a counter ip dscp set ef 2>/dev/null; nft list table ip oaf_accel 2>/dev/null", timeout=25)
        return "table ip oaf_accel" in out
    else:
        out = board("nft delete table ip oaf_accel 2>/dev/null; nft delete table ip6 oaf_accel 2>/dev/null; nft list tables 2>/dev/null", timeout=25)
        return "table ip oaf_accel" in out

_stats_lock = threading.Lock()
CACHE = {"station": {}, "phone_kbs": None, "ap_mbps": None, "ef_kbs": 0.0,
         "signal": None, "tx_rate": None, "rtt": None, "ts": ""}
CACHE_LOCK = threading.Lock()

def _one_board():
    return board("iw dev %s station dump 2>/dev/null; echo @@TX@@; cat /sys/class/net/%s/statistics/tx_bytes 2>/dev/null; echo @@EF@@; nft list table ip oaf_accel 2>/dev/null" % (IFACE, IFACE))

def sampler_thread():
    prev = None
    while True:
        t0 = time.time()
        try:
            out = _one_board()
            parts = out.split("@@TX@@")
            st = parse_station(parts[0]) if parts else {}
            rest = parts[1] if len(parts) > 1 else ""
            p2 = rest.split("@@EF@@")
            tx = p2[0].strip()
            nft = p2[1] if len(p2) > 1 else ""
            ef = 0
            for line in nft.splitlines():
                if "counter packets" in line and "dscp set ef" in line:
                    try: ef += int(line.split("counter packets")[1].split("bytes")[1].split()[0])
                    except: pass
            txv = int(tx) if tx.isdigit() else None
            now = time.time()
            cur = {"t": now, "tx": txv, "ef": ef, "st": st}
            if prev is not None:
                dt = max(0.2, now - prev["t"])
                phone_kbs = ((txv - prev["tx"]) / dt / 1024) if (txv is not None and prev["tx"] is not None) else None
                ef_kbs = (ef - prev["ef"]) / dt / 1024
                ap_mbps = ((txv - prev["tx"]) * 8 / dt / 1e6) if (txv is not None and prev["tx"] is not None) else None
                with CACHE_LOCK:
                    CACHE.update({"phone_kbs": phone_kbs, "ap_mbps": ap_mbps, "ef_kbs": ef_kbs,
                                  "signal": st.get("signal"), "tx_rate": st.get("tx_bitrate"),
                                  "accel": "table ip oaf_accel" in nft, "ts": time.strftime("%H:%M:%S")})
            prev = cur
        except Exception:
            pass
        time.sleep(max(0.05, 1.0 - (time.time() - t0)))

def rtt_thread():
    while True:
        r = rtt()
        if r:
            with CACHE_LOCK: CACHE["rtt"] = r
        time.sleep(2.0)

def stats():
    a = window_reset()
    with CACHE_LOCK:
        c = dict(CACHE)
    rec = {
        "t": time.strftime("%H:%M:%S"),
        "ttfb": (a["ttfb_last"] * 1000) if a["ttfb_last"] else None,
        "aidl": a["dl_rate"] / 1024,
        "ef": c.get("ef_kbs", 0.0),
        "rtt": (c["rtt"]["avg"] if c.get("rtt") else None),
    }
    with HIST_LOCK:
        for k in HIST: HIST[k].append(rec[k])
        for k in HIST:
            if len(HIST[k]) > HMAX: del HIST[k][:len(HIST[k]) - HMAX]
        hist = {k: list(HIST[k]) for k in HIST}
    d = {
        "ts": rec["t"],
        "accel": c.get("accel", False),
        "ai": {
            "dl_kbs": a["dl_rate"] / 1024, "ul_kbs": a["ul_rate"] / 1024,
            "flows": a["flows"],
            "ttfb_last_ms": (a["ttfb_last"] * 1000) if a["ttfb_last"] else None,
            "ttfb_p50_ms": (a["ttfb_p50"] * 1000) if a["ttfb_p50"] else None,
            "ttfb_max_ms": (a["ttfb_max"] * 1000) if a["ttfb_max"] else None,
            "ttfb_n": a["ttfb_n"],
        },
        "ef_kbs": c.get("ef_kbs", 0.0),
        "ef_pct": (c.get("ef_kbs", 0.0) / (a["dl_rate"] / 1024) * 100) if a["dl_rate"] else 0,
        "signal": c.get("signal"), "tx_rate": c.get("tx_rate"),
        "rtt": c.get("rtt"), "hist": hist,
        "bg": bg_state()[0], "bg_n": bg_state()[1],
        "bgsta": bgsta_state()[0], "bgsta_n": bgsta_state()[1],
        "cap6m": True,
    }
    log_row(d)
    return d

HTML = """<!doctype html><html><head><meta charset="utf-8"><title>AI 业务加速看板</title>
<style>
html,body{background:#0b0f17;color:#e6edf3;font-family:system-ui,Segoe UI,Arial;margin:0;padding:14px;text-align:left}
h1{font-size:20px;margin:0 0 12px;text-align:left;font-weight:700}
.row2{display:flex;gap:26px;align-items:center;flex-wrap:wrap;background:#151b26;border:1px solid #232c3b;border-radius:12px;padding:12px 16px;margin-bottom:12px}
.grp{display:flex;align-items:center;gap:12px}
.lab{font-size:14px;color:#c9d3df}
.sw{width:66px;height:34px;border-radius:17px;background:#2a3444;position:relative;cursor:pointer;transition:.2s;flex:0 0 auto}
.sw.on{background:#1f9d55}
.sw i{position:absolute;top:4px;left:4px;width:26px;height:26px;border-radius:50%;background:#fff;transition:.2s}
.sw.on i{left:36px}
.st{font-size:14px;font-weight:600}
.big{font-size:30px;font-weight:800;color:#3ddc84;line-height:1}
.on-t{color:#3ddc84}.off-t{color:#ff6b6b}
select{background:#0f141c;color:#e6edf3;border:1px solid #2a3444;border-radius:6px;padding:6px 10px;font-size:15px}
.charts{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.cb{background:#151b26;border:1px solid #232c3b;border-radius:12px;padding:10px 12px}
.ct{font-size:13px;color:#9aa7b8;display:flex;justify-content:space-between;margin-bottom:4px}
.cv{font-size:14px;font-weight:600;color:#e6edf3}
canvas{width:100%;height:150px;display:block}
.bar{display:flex;align-items:center;gap:12px;margin:12px 0 4px}
.bar input[type=range]{flex:1;accent-color:#3ddc84}
.meta{font-size:12px;color:#8b98a9;margin-top:6px}
</style></head><body>
<h1>AI 业务加速看板 · 豆包</h1>
<div class="row2">
  <div class="grp"><span class="lab">加速</span><div class="sw" id="sw" onclick="toggle()"><i></i></div><span class="st" id="state">-</span></div>
  <div class="grp"><span class="lab">同STA背景流</span><div class="sw" id="sw_bg" onclick="toggleBg()"><i></i></div><span class="st" id="bgst">-</span></div>
  <div class="grp"><span class="lab">同STA条数</span><select id="bgn" onchange="onBgnChange()"><option>10</option><option>50</option><option selected>100</option><option>150</option><option>200</option></select></div>
  <div class="grp"><span class="lab">跨STA背景流</span><div class="sw" id="sw_sta" onclick="toggleSta()"><i></i></div><span class="st" id="stast">-</span></div>
  <div class="grp"><span class="lab">记录</span><a href="/dash_log.csv" target="_blank" class="lab" style="color:#3ddc84">下载CSV</a><span class="lab" style="cursor:pointer;color:#ff6b6b" onclick="clearLog()">清空</span></div>
</div>
<div class="charts">
  <div class="cb"><div class="ct"><span>TTFB</span><span class="cv" id="v_ttfb">-</span></div><canvas id="c_ttfb" width="700" height="150"></canvas></div>
  <div class="cb"><div class="ct"><span>AI 下行速率</span><span class="cv" id="v_aidl">-</span></div><canvas id="c_aidl" width="700" height="150"></canvas></div>
  <div class="cb"><div class="ct"><span>EF 加速流量</span><span class="cv" id="v_ef">-</span></div><canvas id="c_ef" width="700" height="150"></canvas></div>
  <div class="cb"><div class="ct"><span>手机 RTT</span><span class="cv" id="v_rtt">-</span></div><canvas id="c_rtt" width="700" height="150"></canvas></div>
</div>
<div class="bar"><span class="lab">窗口</span><input type="range" id="slider" min="0" max="55" value="55"><span class="lab" id="winlabel">最近 5 秒</span></div>
<div class="meta" id="meta">-</div>
<script>
const WIN=5;
let accel=false,bgOn=false,capOn=false,LAST={},pos=55,userMoved=false;
function drawOne(id,vals,color){
  const c=document.getElementById(id),ctx=c.getContext('2d'),W=c.width,H=c.height;
  ctx.clearRect(0,0,W,H);const L=46,R=8,T=10,B=18;
  const v=(vals||[]).filter(x=>x!=null&&isFinite(x));
  if(v.length<2){ctx.fillStyle='#8b98a9';ctx.font='13px sans-serif';ctx.fillText('等待数据…',L+6,H/2);return;}
  let mn=Math.min.apply(null,v),mx=Math.max.apply(null,v);
  if(mx-mn<1e-9)mx=mn+1;
  const pad=(mx-mn)*0.2;mn-=pad;mx+=pad;if(mn<0&&Math.min.apply(null,v)>=0)mn=0;
  const n=v.length,X=i=>L+(W-L-R)*i/(n-1),Y=x=>T+(H-T-B)*(1-(x-mn)/(mx-mn));
  ctx.strokeStyle='#232c3b';ctx.lineWidth=1;
  for(let g=0;g<=4;g++){const y=T+(H-T-B)*g/4;ctx.beginPath();ctx.moveTo(L,y);ctx.lineTo(W-R,y);ctx.stroke();}
  ctx.strokeStyle=color;ctx.lineWidth=2.5;ctx.beginPath();
  for(let i=0;i<n;i++){const px=X(i),py=Y(v[i]);if(i===0)ctx.moveTo(px,py);else ctx.lineTo(px,py);}
  ctx.stroke();
  const last=v[v.length-1];
  ctx.fillStyle=color;ctx.beginPath();ctx.arc(X(n-1),Y(last),3.5,0,7);ctx.fill();
  ctx.fillStyle='#8b98a9';ctx.font='11px sans-serif';
  const fm=x=>{const a=Math.abs(x);return a>=100?x.toFixed(0):a>=10?x.toFixed(1):a>=1?x.toFixed(2):x.toFixed(3);};
  ctx.fillText(fm(mx),4,T+10);ctx.fillText(fm(mn),4,H-B);
}
function render(){
  const h=LAST.hist||{};
  const slice=k=>{const arr=h[k]||[];return arr.slice(pos,pos+WIN);};
  drawOne('c_ttfb',slice('ttfb'),'#3ddc84');
  drawOne('c_aidl',slice('aidl'),'#4da3ff');
  drawOne('c_ef',slice('ef'),'#ffb84d');
  drawOne('c_rtt',slice('rtt'),'#c77dff');
  document.getElementById('winlabel').textContent=(pos>=55?'最近 5 秒':('第 '+pos+'–'+(pos+WIN)+' 秒'));
}
async function refresh(){
  try{
    const ctrl=new AbortController(); const to=setTimeout(()=>ctrl.abort(),4000);
    let r; try { r=await fetch('/api/stats',{signal:ctrl.signal}); } finally { clearTimeout(to); }
    const d=await r.json();const a=d.ai||{};LAST=d;
    accel=d.accel;bgOn=!!d.bg;staOn=!!d.bgsta;
    document.getElementById('sw_bg').className='sw'+(bgOn?' on':'');
    document.getElementById('bgst').textContent=bgOn?'运行中':'已停止';
    document.getElementById('bgst').className='st '+(bgOn?'on-t':'off-t');
    if (bgOn && d.bg_n) { const sel=document.getElementById('bgn'); const sv=String(d.bg_n); if ([].some.call(sel.options,function(o){return o.value===sv||o.text===sv;})) sel.value=sv; }
    document.getElementById('sw').className='sw'+(accel?' on':'');
    document.getElementById('state').textContent=accel?'已开启':'已关闭';
    document.getElementById('state').className='st '+(accel?'on-t':'off-t');
    document.getElementById('sw_sta').className='sw'+(staOn?' on':'');
    document.getElementById('stast').textContent=staOn?'运行中':'已停止';
    const f=(x,n)=>(x==null?'-':Number(x).toFixed(n==null?1:n));
    document.getElementById('v_ttfb').textContent=f(a.ttfb_last_ms,1)+' ms';
    document.getElementById('v_aidl').textContent=f(a.dl_kbs,2)+' KB/s';
    document.getElementById('v_ef').textContent=f(d.ef_kbs,2)+' KB/s';
    document.getElementById('v_rtt').textContent=(d.rtt?f(d.rtt.avg,1)+' ms':'-');
    const n=(d.hist&&d.hist.t)?d.hist.t.length:0;
    const maxPos=Math.max(0,n-WIN);
    if(!userMoved||pos>maxPos){pos=maxPos;}
    document.getElementById('slider').max=maxPos;
    document.getElementById('slider').value=pos;
    render();
    document.getElementById('meta').textContent='TTFB样本 '+a.ttfb_n+' · AI流 '+a.flows+' · EF占比 '+f(d.ef_pct,0)+'% · 信号 '+(d.signal==null?'-':d.signal)+'dBm · '+d.ts;
  }catch(e){}
}
document.getElementById('slider').addEventListener('input',function(){userMoved=true;pos=parseInt(this.value);render();});
async function toggle(){const t=!accel;document.getElementById('state').textContent='切换中…';await fetch('/api/toggle?on='+(t?1:0));refresh();}
async function toggleSta(){const t=!staOn;await fetch('/api/bgsta?on='+(t?1:0));refresh();}
async function clearLog(){ if(confirm('清空已记录的数据？')){ await fetch('/api/clear_log'); } }
async function onBgnChange(){if(bgOn){const n=document.getElementById('bgn').value;await fetch('/api/bg?on=1&n='+n);refresh();}}
async function toggleBg(){const t=!bgOn;const n=document.getElementById('bgn').value;await fetch('/api/bg?on='+(t?1:0)+'&n='+n);refresh();}
refresh();setInterval(refresh,2000);
</script></body></html>"""

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, code, body, ctype="text/html; charset=utf-8"):
        b = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code); self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        u = urllib.parse.urlparse(self.path); q = urllib.parse.parse_qs(u.query)
        if u.path == "/": self._send(200, HTML)
        elif u.path == "/api/stats":
            try: self._send(200, json.dumps(stats()), "application/json")
            except Exception as e: self._send(500, json.dumps({"error": str(e)}), "application/json")
        elif u.path == "/api/bg":
            on = q.get("on", ["0"])[0] == "1"
            n = int(q.get("n", ["4"])[0])
            threading.Thread(target=bg_apply, args=(on, n), daemon=True).start()
            self._send(200, json.dumps({"bg": on, "n": n if on else 0}), "application/json")
        elif u.path == "/api/bgsta":
            on = q.get("on", ["0"])[0] == "1"
            n = int(q.get("n", ["2"])[0])
            def run():
                with BG_LOCK:
                    if on: start_bgsta(n)
                    else: stop_bgsta_locked()
            threading.Thread(target=run, daemon=True).start()
            self._send(200, json.dumps({"bgsta": on, "n": n if on else 0}), "application/json")
        elif u.path == "/api/clear_log":
            try:
                if os.path.exists(LOG_PATH): os.remove(LOG_PATH)
            except Exception: pass
            self._send(200, json.dumps({"ok": True}), "application/json")
        elif u.path == "/dash_log.csv":
            try:
                with open(LOG_PATH, "rb") as f: data = f.read()
            except Exception:
                data = b""
            self._send(200, data, "text/csv")
        elif u.path == "/api/cap":
            on = q.get("on", ["0"])[0] == "1"
            self._send(200, json.dumps(cap_on(on)), "application/json")
        elif u.path == "/api/toggle":
            on = q.get("on", ["0"])[0] == "1"
            st = set_accel(on)
            with CACHE_LOCK: CACHE["accel"] = st
            self._send(200, json.dumps({"accel": st}), "application/json")
        else: self._send(404, "not found")

if __name__ == "__main__":
    threading.Thread(target=pcap_thread, daemon=True).start()
    threading.Thread(target=sampler_thread, daemon=True).start()
    threading.Thread(target=rtt_thread, daemon=True).start()
    print("dashboard on http://127.0.0.1:%d" % PORT, flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()