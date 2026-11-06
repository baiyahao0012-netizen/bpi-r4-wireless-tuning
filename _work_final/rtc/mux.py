# -*- coding: utf-8 -*-
"""Mux the received video and the received audio into one playable file."""
import av, numpy as np, fractions

inp = av.open("rcv03.mp4")
vs_in = inp.streams.video[0]
W = vs_in.codec_context.width
H = vs_in.codec_context.height
FPS = 25
out = av.open("rcv03_sync.mp4", "w")
vs = out.add_stream("libx264", rate=FPS)
vs.width, vs.height, vs.pix_fmt = W, H, "yuv420p"
vs.options = {"preset": "veryfast", "crf": "23"}
as_ = out.add_stream("aac", rate=48000)
as_.layout = "mono"

pcm = np.fromfile("rcv03.pcm", dtype=np.int16)
SPB = 1920          # 40 ms of audio, one video frame at 25 fps
ai = 0
i = 0

def flush_audio(upto):
    global ai
    while ai + SPB <= upto:
        chunk = pcm[ai:ai + SPB].reshape(1, -1).copy()
        af = av.AudioFrame.from_ndarray(chunk, format="s16", layout="mono")
        af.sample_rate = 48000
        af.pts = ai
        af.time_base = fractions.Fraction(1, 48000)
        for pkt in as_.encode(af):
            out.mux(pkt)
        ai += SPB

for frame in inp.decode(vs_in):
    frame.pts = i
    frame.time_base = fractions.Fraction(1, FPS)
    for pkt in vs.encode(frame):
        out.mux(pkt)
    i += 1
    flush_audio(i * SPB)

flush_audio(len(pcm))
for pkt in vs.encode(None):
    out.mux(pkt)
for pkt in as_.encode(None):
    out.mux(pkt)
out.close()
print("muxed %d video frames, %d audio samples" % (i, ai))
