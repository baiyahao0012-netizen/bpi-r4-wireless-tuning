# -*- coding: utf-8 -*-
import numpy as np
p = np.fromfile("rcv03.pcm", dtype=np.int16).astype(np.float32)
n = len(p)
print("samples:", n, "seconds:", n/48000)
half = n // 2
a, b = p[:half], p[half:]
print("half identical:", bool(np.allclose(a, b, atol=1e-3)))
# block-level duplication check: compare x[i] with x[i+lag]
for lag in (960, 1920, 3840):
    x = p[:-lag]; y = p[lag:]
    c = float(np.dot(x, y) / (np.linalg.norm(x)*np.linalg.norm(y) + 1e-9))
    print("corr lag %d samples (%.1f ms): %.4f" % (lag, lag/48.0, c))
# zero-crossing / energy as a sanity signal
print("rms:", float(np.sqrt((p.astype(np.float64)**2).mean())))
