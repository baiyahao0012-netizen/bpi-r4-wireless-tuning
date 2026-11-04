# -*- coding: utf-8 -*-
import numpy as np, sounddevice as sd, time

print("=== hostapis ===")
for i, h in enumerate(sd.query_hostapis()):
    print("%d: %-14s devices=%s default_in=%s default_out=%s"
          % (i, h['name'], len(h['devices']), h.get('default_input_device'),
             h.get('default_output_device')))

print("\n=== devices ===")
for i, d in enumerate(sd.query_devices()):
    api = sd.query_hostapis(d['hostapi'])['name']
    print("%2d %-12s in=%d out=%d sr=%.0f  %s"
          % (i, api[:12], d['max_input_channels'], d['max_output_channels'],
             d['default_samplerate'], d['name']))

def find(api_name, want_in=None, keyword=None):
    hits = []
    for i, d in enumerate(sd.query_devices()):
        api = sd.query_hostapis(d['hostapi'])['name']
        if api_name not in api:
            continue
        if want_in is not None:
            if want_in and d['max_input_channels'] < 1: continue
            if (not want_in) and d['max_output_channels'] < 1: continue
        if keyword and keyword.lower() not in d['name'].lower():
            continue
        hits.append(i)
    return hits

def capture_test(idx, sr, ch, ms=20, blocks=25):
    blk = int(sr * ms / 1000)
    try:
        got = []
        with sd.InputStream(device=idx, samplerate=sr, channels=ch,
                            dtype='int16', blocksize=blk) as st:
            t0 = time.perf_counter()
            lat = st.latency
            for _ in range(blocks):
                d, ov = st.read(blk)
                got.append(d.copy())
            el = time.perf_counter() - t0
        a = np.concatenate(got).astype(np.int16)
        rms = float(np.sqrt((a.astype(np.float64) ** 2).mean()))
        pk = int(np.abs(a).max())
        print("  dev=%-3d %5d Hz ch=%d blk=%4d -> %.3fs for %.3fs audio (%.2fx) "
              "lat=%.3fs rms=%6.1f peak=%5d"
              % (idx, sr, ch, blk, el, blocks*ms/1000.0,
                 el/(blocks*ms/1000.0), lat, rms, pk))
        return rms
    except Exception as e:
        print("  dev=%-3d %5d Hz ch=%d FAILED: %r" % (idx, sr, ch, e))
        return None

print("\n=== capture trials (Realtek mic) ===")
for api in ("WASAPI", "MME", "DirectSound", "WDM-KS"):
    for idx in find(api, want_in=True, keyword="麦克风")[:2] or find(api, want_in=True)[:2]:
        for (sr, ch) in ((44100, 2), (48000, 1)):
            capture_test(idx, sr, ch)

print("\n=== output candidates (non-Bluetooth first) ===")
for i, d in enumerate(sd.query_devices()):
    if d['max_output_channels'] < 1:
        continue
    api = sd.query_hostapis(d['hostapi'])['name']
    print("%2d %-12s ch=%d sr=%.0f  %s" % (i, api[:12], d['max_output_channels'],
                                           d['default_samplerate'], d['name']))
