# -*- coding: utf-8 -*-
"""Transcode the supplied test.mp4 to 640x480@30, first N seconds."""
import sys
import av

src = r"D:\Desktop\AI 辅助对话\test.mp4"
SECS = float(sys.argv[1]) if len(sys.argv) > 1 else 30.0
out = av.open(r"D:\Desktop\AI 辅助对话\_work_final\rtc\test640.mp4", "w")
st = out.add_stream("libx264", rate=30)
st.width, st.height, st.pix_fmt = 640, 480, "yuv420p"
st.options = {"preset": "veryfast", "tune": "zerolatency",
              "bitrate": "2000000", "maxrate": "2400000", "bufsize": "1000000",
              "g": "30"}

inp = av.open(src)
vs = inp.streams.video[0]
n = 0
for frame in inp.decode(vs):
    if n >= SECS * 30:
        break
    img = frame.reformat(width=640, height=480, format="yuv420p")
    img.pts = n
    try:
        for pkt in st.encode(img):
            out.mux(pkt)
    except Exception as e:
        print("enc err", e)
        break
    n += 1
for pkt in st.encode(None):
    out.mux(pkt)
out.close()
print("transcoded %d frames" % n)
