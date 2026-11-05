import time, cv2
from fractions import Fraction
from aiortc.codecs.h264 import H264Encoder
from av import VideoFrame

cap = cv2.VideoCapture("clip.mp4")
frames = []
i = 0
while len(frames) < 30:
    ok, img = cap.read()
    if not ok:
        break
    f = VideoFrame.from_ndarray(img, format="bgr24")
    f.pts = i
    f.time_base = Fraction(1, 30)
    frames.append(f)
    i += 1
cap.release()

enc = H264Encoder()
if hasattr(enc, "target_bitrate"):
    enc.target_bitrate = 2000000
enc.encode(frames[0])          # warm up / create codec
print("codec name:", getattr(enc.codec, "name", "?"))
print("codec options:", getattr(enc.codec, "options", None))
t0 = time.perf_counter()
for f in frames:
    enc.encode(f)
el = time.perf_counter() - t0
n = len(frames)
print("encoded %d frames in %.3f s -> %.1f fps, %.1f ms/frame"
      % (n, el, n/el, el/n*1000))
