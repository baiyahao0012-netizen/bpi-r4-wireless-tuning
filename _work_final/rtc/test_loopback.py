# -*- coding: utf-8 -*-
import time, numpy as np
import pyaudiowpatch as pa

p = pa.PyAudio()
print("=== all WASAPI endpoints ===")
loops = []
for i in range(p.get_device_count()):
    d = p.get_device_info_by_index(i)
    tag = "LOOP" if d.get('isLoopbackDevice') else "    "
    print("%s %2d ch=%d sr=%5d  %s" % (tag, i, d['maxInputChannels'],
                                       int(d['defaultSampleRate']), d['name']))
    if d.get('isLoopbackDevice'):
        loops.append(d)

print("\n=== pick loopback for current default output ===")
try:
    lb = p.get_default_wasapi_loopback()
    print("default loopback -> %s ch=%d sr=%d"
          % (lb['name'], lb['maxInputChannels'], int(lb['defaultSampleRate'])))
except Exception as e:
    print("default loopback failed:", e)
    lb = loops[0] if loops else None

if lb:
    idx = lb['index']
    ch = min(2, lb['maxInputChannels'])
    sr = int(lb['defaultSampleRate'])
    print("\n=== capture 3.0 s from %r ===" % lb['name'])
    st = p.open(format=pa.paInt16, channels=ch, rate=sr,
                input=True, input_device_index=idx, frames_per_buffer=1024)
    t0 = time.perf_counter()
    tot = 0
    pk = 0
    acc = 0.0
    while time.perf_counter() - t0 < 3.0:
        buf = st.read(1024, exception_on_overflow=False)
        a = np.frombuffer(buf, dtype=np.int16)
        tot += len(a) // ch
        acc += float((a.astype(np.float64) ** 2).sum())
        pk = max(pk, int(np.abs(a).max()))
    el = time.perf_counter() - t0
    st.stop_stream(); st.close()
    print("  got %d frames in %.2fs -> %d Hz (%.2fx of %d)  rms=%.1f peak=%d"
          % (tot, el, tot / el, (tot / el) / sr, sr,
             (acc / max(tot * ch, 1)) ** 0.5, pk))
p.terminate()
