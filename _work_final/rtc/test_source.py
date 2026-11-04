# -*- coding: utf-8 -*-
import importlib, time
print("=== modules ===")
for m in ('pyaudiowpatch', 'soundcard', 'mss', 'dxcam', 'PIL', 'PIL.ImageGrab', 'cv2', 'numpy', 'sounddevice'):
    try:
        mod = importlib.import_module(m)
        print("%-16s OK   %s" % (m, getattr(mod, '__version__', '')))
    except Exception as e:
        print("%-16s MISSING  %s" % (m, e))

print("\n=== WASAPI loopback endpoints (pyaudiowpatch) ===")
try:
    import pyaudiowpatch as pa
    p = pa.PyAudio()
    try:
        d = p.get_default_wasapi_loopback()
        print("default loopback: %s ch=%d sr=%d" %
              (d['name'], d['maxInputChannels'], int(d['defaultSampleRate'])))
    except Exception as e:
        print("no default loopback:", e)
    for i in range(p.get_device_count()):
        d = p.get_device_info_by_index(i)
        if d.get('isLoopbackDevice'):
            print("  LOOP %2d ch=%d sr=%5d  %s" %
                  (i, d['maxInputChannels'], int(d['defaultSampleRate']), d['name']))
    p.terminate()
except Exception as e:
    print("pyaudiowpatch unavailable:", e)

print("\n=== loopback mics (soundcard) ===")
try:
    import soundcard as sc
    for m in sc.all_microphones(include_loopback=True):
        print("  ", "LOOP" if m.isloopback else "MIC ", m.name)
    print("default speaker:", sc.default_speaker().name)
except Exception as e:
    print("soundcard unavailable:", e)

print("\n=== screen capture timing (PIL) ===")
try:
    import numpy as np
    from PIL import ImageGrab
    t = time.perf_counter()
    im = ImageGrab.grab()
    print("  full screen: %dx%d in %.1f ms" % (im.size[0], im.size[1],
                                               (time.perf_counter() - t) * 1000))
    for (w, h) in ((640, 480), (960, 540), (1280, 720)):
        t = time.perf_counter()
        n = 10
        for _ in range(n):
            im2 = ImageGrab.grab()
            im3 = im2.resize((w, h))
            arr = np.asarray(im3)[:, :, ::-1].copy()
        el = (time.perf_counter() - t) / n * 1000
        print("  grab+resize->%dx%d: %.1f ms/frame  shape=%s dtype=%s"
              % (w, h, el, arr.shape, arr.dtype))
except Exception as e:
    print("  PIL grab failed:", e)

print("\n=== screen capture timing (mss) ===")
try:
    import mss, numpy as np
    with mss.mss() as sct:
        mon = sct.monitors[1]
        t = time.perf_counter()
        n = 10
        for _ in range(n):
            img = sct.grab(mon)
        print("  %dx%d in %.1f ms/frame" % (img.width, img.height,
                                            (time.perf_counter() - t) / n * 1000))
except Exception as e:
    print("  mss unavailable:", e)
