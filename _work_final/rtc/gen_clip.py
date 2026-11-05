# -*- coding: utf-8 -*-
"""Generate a deterministic test clip with motion (shared by both arms)."""
import numpy as np
import av

import sys
W, H, FPS, SECS = 320, 240, 30, 10
OUT = "clip_small.mp4"
out = av.open(OUT, "w")
st = out.add_stream("libx264", rate=FPS)
st.width, st.height = W, H
st.pix_fmt = "yuv420p"
st.options = {"preset": "veryfast", "tune": "zerolatency",
              "bitrate": "2000000", "maxrate": "2400000", "bufsize": "1000000",
              "g": "30"}

base_y, base_x = np.mgrid[0:H, 0:W].astype(np.float32)
n = 0
for i in range(FPS * SECS):
    t = i / float(FPS)
    # moving diagonal gradient: strong, continuous motion everywhere
    phase = 40.0 * t
    grad = np.sin((base_x + base_y + phase * 12) / 28.0) * 60 + 128
    img = np.dstack([grad, grad * 0.85, grad * 0.7]).astype(np.uint8)
    # bouncing box
    bx = int((W - 120) * (0.5 + 0.5 * np.sin(t * 1.7)))
    by = int((H - 120) * (0.5 + 0.5 * np.cos(t * 1.3)))
    img[by:by + 120, bx:bx + 120] = (30, 220, 60)
    # sweeping bar
    sx = int((W - 20) * ((t * 0.37) % 1.0))
    img[:, sx:sx + 20] = (240, 60, 60)
    frame = av.VideoFrame.from_ndarray(img, format="bgr24")
    frame.pts = n
    for pkt in st.encode(frame):
        out.mux(pkt)
    n += 1
for pkt in st.encode(None):
    out.mux(pkt)
out.close()
print("wrote clip.mp4  %dx%d@%d  %ds  %d frames" % (W, H, FPS, SECS, n))
