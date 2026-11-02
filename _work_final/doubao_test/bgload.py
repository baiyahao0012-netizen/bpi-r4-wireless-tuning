import socket, sys, time, threading
src, n, dur = sys.argv[1], int(sys.argv[2]), float(sys.argv[3])
host = sys.argv[4] if len(sys.argv) > 4 else "192.168.240.1"
path = sys.argv[5] if len(sys.argv) > 5 else "/big.bin"
tot = [0]*n
def worker(i):
    try:
        s = socket.socket(); s.bind((src,0)); s.settimeout(5); s.connect((host,80)); s.settimeout(5)
        s.sendall(("GET %s HTTP/1.0\r\nHost: h\r\n\r\n" % path).encode())
        t0=time.time()
        while time.time()-t0 < dur:
            d = s.recv(1<<20)
            if not d: break
            tot[i]+=len(d)
        s.close()
    except Exception: pass
ts=[threading.Thread(target=worker,args=(i,)) for i in range(n)]
t0=time.time()
for t in ts: t.start()
for t in ts: t.join()
el=time.time()-t0; total=sum(tot)
print("conns=%d el=%.1fs total=%.1fMB agg=%.0f Mbit/s" % (n, el, total/1e6, total*8/el/1e6))

