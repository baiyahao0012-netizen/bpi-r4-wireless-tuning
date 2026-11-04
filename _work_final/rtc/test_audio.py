# -*- coding: utf-8 -*-
import numpy as np, sounddevice as sd, av, time
from fractions import Fraction

print("--- devices ---")
print("default in :", sd.query_devices(kind='input')['name'])
print("default out:", sd.query_devices(kind='output')['name'])

SR, BLK = 48000, 960          # 20 ms mono
try:
    dev = sd.query_devices(kind='input')
    print("in  ch=%d sr=%d" % (dev['max_input_channels'], dev['default_samplerate']))
except Exception as e:
    print("query in failed:", e)

print("--- capture 20 blocks ---")
try:
    frames = []
    with sd.InputStream(samplerate=SR, channels=1, dtype='int16', blocksize=BLK) as st:
        t0 = time.perf_counter()
        for i in range(20):
            d, over = st.read(BLK)
            frames.append(d.copy())
    el = time.perf_counter() - t0
    a = np.concatenate(frames)
    print("captured %d samples in %.3fs (expect %.3f)  rms=%.1f peak=%d overflow=%s"
          % (len(a), el, 20*BLK/SR, float(np.sqrt((a.astype(np.float64)**2).mean())),
             int(np.abs(a).max()), over))
except Exception as e:
    print("CAPTURE FAILED: %r" % (e,))

print("--- opus encode/decode ---")
try:
    enc = av.CodecContext.create('libopus', 'w')
    enc.sample_rate = SR; enc.layout = 'mono'; enc.format = 's16'
    enc.bit_rate = 64000
    enc.open()
    sizes = []
    out = []
    for f in frames[:10]:
        fr = av.AudioFrame.from_ndarray(f.reshape(1, -1), format='s16', layout='mono')
        fr.sample_rate = SR; fr.pts = 0; fr.time_base = Fraction(1, SR)
        for p in enc.encode(fr):
            b = bytes(p); sizes.append(len(b)); out.append(b)
    for p in enc.encode(None):
        sizes.append(len(bytes(p)))
    print("encoded %d packets, %d..%d B (avg %.0f)"
          % (len(sizes), min(sizes), max(sizes), sum(sizes)/len(sizes)))
    dec = av.CodecContext.create('libopus', 'r')
    n = 0
    for b in out:
        for fr in dec.decode(av.Packet(b)):
            n += fr.samples
    print("decoded %d samples (expect %d)" % (n, 10*BLK))
except Exception as e:
    print("OPUS FAILED: %r" % (e,))

print("--- playback 0.4s 440Hz ---")
try:
    t = np.arange(int(SR*0.4)) / SR
    tone = (0.2 * 32767 * np.sin(2*np.pi*440*t)).astype(np.int16)
    sd.play(tone, SR); sd.wait()
    print("playback OK")
except Exception as e:
    print("PLAYBACK FAILED: %r" % (e,))
