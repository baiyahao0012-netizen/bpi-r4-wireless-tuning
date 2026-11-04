# -*- coding: utf-8 -*-
import numpy as np, sounddevice as sd, time, threading

def cb_test(idx, sr, ch, secs=2.0, label=""):
    got = {'n': 0, 'pk': 0, 'sum': 0.0, 'blocks': 0, 't0': None}
    def cb(indata, frames, ti, status):
        a = indata[:, 0].astype(np.int32)
        got['n'] += frames
        got['sum'] += float((a.astype(np.float64) ** 2).sum())
        got['pk'] = max(got['pk'], int(np.abs(a).max()))
        got['blocks'] += 1
        if got['t0'] is None:
            got['t0'] = time.perf_counter()
    try:
        st = sd.InputStream(device=idx, samplerate=sr, channels=ch, dtype='int16',
                            blocksize=0, callback=cb)
        st.start()
        t0 = time.perf_counter()
        time.sleep(secs)
        el = time.perf_counter() - t0
        st.stop(); st.close()
        rate = got['n'] / el
        rms = (got['sum'] / max(got['n'], 1)) ** 0.5
        print("  %-10s dev=%-3d %5d Hz ch=%d -> %6d samples in %.2fs = %7.0f Hz "
              "(%.2fx)  blocks=%3d rms=%6.1f peak=%5d"
              % (label, idx, sr, ch, got['n'], el, rate, rate / sr, got['blocks'], rms, got['pk']))
        return rate
    except Exception as e:
        print("  %-10s dev=%-3d %5d Hz ch=%d FAILED %r" % (label, idx, sr, ch, e))
        return None

print("=== callback capture: is the mic alive and at what rate? ===")
cb_test(23, 48000, 2, 2.0, "WASAPI arr")
cb_test(23, 48000, 1, 2.0, "WASAPI arr")
cb_test(1, 44100, 2, 2.0, "MME arr")
cb_test(24, 48000, 2, 2.0, "WASAPI mix")   # 立体声混音 = loopback of system sound

print("\n=== WASAPI loopback (system sound) as a synthetic source ===")
try:
    import sounddevice as _sd
    print("  default out:", _sd.query_devices(kind='output')['name'])
except Exception as e:
    print("  ", e)

print("\n=== output device open test (Realtek speakers, WASAPI) ===")
for idx in (21, 25, 8):
    try:
        sr = int(sd.query_devices(idx)['default_samplerate'])
        t = np.arange(int(sr * 0.25)) / sr
        tone = (0.15 * 32767 * np.sin(2 * np.pi * 660 * t)).astype(np.int16)
        with sd.OutputStream(device=idx, samplerate=sr, channels=2, dtype='int16') as o:
            o.write(np.repeat(tone.reshape(-1, 1), 2, axis=1))
            lat = o.latency
        print("  dev=%-3d %5d Hz OK latency=%.3fs  %s"
              % (idx, sr, lat, sd.query_devices(idx)['name']))
    except Exception as e:
        print("  dev=%-3d FAILED %r" % (idx, e))
