# -*- coding: utf-8 -*-
"""Fetch the received A/V, verify lengths, and mux into one playable file."""
import paramiko, av, numpy as np, fractions

from remote_config import HOST, USER, PWD

t = paramiko.Transport((HOST, 22))
t.connect(username=USER, password=PWD)
sftp = paramiko.SFTPClient.from_transport(t)
for n in ["rcv05.mp4", "rcv05.pcm"]:
    sftp.get("C:/rtc/" + n, n)
    print("got", n)
sftp.close(); t.close()

pcm = np.fromfile("rcv05.pcm", dtype=np.int16)
print("pcm samples=%d  seconds=%.2f" % (len(pcm), len(pcm)/48000.0))

inp = av.open("rcv05.mp4")
vs_in = inp.streams.video[0]
W, H, FPS = vs_in.codec_context.width, vs_in.codec_context.height, 25
out = av.open("rcv05_sync.mp4", "w")
vs = out.add_stream("libx264", rate=FPS)
vs.width, vs.height, vs.pix_fmt = W, H, "yuv420p"
vs.options = {"preset": "veryfast", "crf": "23"}
as_ = out.add_stream("aac", rate=48000)
as_.layout = "mono"
SPB = 1920
ai = 0
i = 0

def flush(upto):
    global ai
    while ai + SPB <= upto:
        chunk = pcm[ai:ai+SPB].reshape(1, -1).copy()
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
    flush(i * SPB)
flush(len(pcm))
for pkt in vs.encode(None):
    out.mux(pkt)
for pkt in as_.encode(None):
    out.mux(pkt)
out.close()
print("muxed video=%d frames  audio=%d samples (%.2f s)"
      % (i, ai, ai/48000.0))
