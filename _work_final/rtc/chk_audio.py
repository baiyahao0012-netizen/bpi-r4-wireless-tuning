# -*- coding: utf-8 -*-
"""Compare received audio against the source: length, level, spectral centroid."""
import av, numpy as np

def load_file_audio(path, secs=32.0):
    c = av.open(path)
    st = c.streams.audio[0]
    out = []
    n = 0
    for fr in c.decode(st):
        a = fr.to_ndarray()
        ch = len(fr.layout.channels)
        a = a.reshape(-1)
        if ch > 1:
            a = a.reshape(-1, ch).mean(axis=1)
        if fr.format.name != 's16':
            a = (np.clip(a, -1.0, 1.0) * 32767).astype('int16')
        out.append(a.astype('int16'))
        n += len(a)
        if n >= secs * fr.sample_rate:
            break
    return np.concatenate(out)[:int(secs * 48000)]

def centroid(x, sr=48000):
    x = x.astype(np.float64)
    w = np.hanning(8192)
    tot = 0.0; cnt = 0
    for i in range(0, len(x) - 8192, 4096):
        seg = x[i:i+8192] * w
        sp = np.abs(np.fft.rfft(seg))
        f = np.fft.rfftfreq(8192, 1.0/sr)
        tot += float((sp * f).sum()); cnt += float(sp.sum())
    return tot / max(cnt, 1e-9)

src = load_file_audio(r"D:\Desktop\AI 辅助对话\test03_music.mp4")
rcv = np.fromfile("rcv05.pcm", dtype=np.int16)
print("source: %d samples (%.2f s)  rms=%.1f  centroid=%.0f Hz"
      % (len(src), len(src)/48000.0, float(np.sqrt((src.astype(np.float64)**2).mean())), centroid(src)))
print("recv  : %d samples (%.2f s)  rms=%.1f  centroid=%.0f Hz"
      % (len(rcv), len(rcv)/48000.0, float(np.sqrt((rcv.astype(np.float64)**2).mean())), centroid(rcv)))
