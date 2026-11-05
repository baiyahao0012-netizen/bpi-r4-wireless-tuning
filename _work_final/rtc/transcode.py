# -*- coding: utf-8 -*-
import sys, av
src, dst = sys.argv[1], sys.argv[2]
W, H, FPS, SECS = 640, 480, 30, float(sys.argv[3]) if len(sys.argv) > 3 else 30.0
out = av.open(dst, "w")
st = out.add_stream("libx264", rate=FPS)
st.width, st.height, st.pix_fmt = W, H, "yuv420p"
st.options = {"preset": "veryfast", "tune": "zerolatency",
              "bitrate": "2000000", "maxrate": "2400000", "bufsize": "1000000",
              "g": "30"}
inp = av.open(src)
vs = inp.streams.video[0]
n = 0
for frame in inp.decode(vs):
    if n >= SECS * FPS:
        break
    img = frame.reformat(width=W, height=H, format="yuv420p")
    img.pts = n
    for pkt in st.encode(img):
        out.mux(pkt)
    n += 1
for pkt in st.encode(None):
    out.mux(pkt)
out.close()
print("transcoded %d frames" % n)
