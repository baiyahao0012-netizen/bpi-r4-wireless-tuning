import time, cv2
cap = cv2.VideoCapture("clip.mp4")
print("opened:", cap.isOpened(), "fps:", cap.get(cv2.CAP_PROP_FPS),
      "frames:", cap.get(cv2.CAP_PROP_FRAME_COUNT))
n = 0
t0 = time.perf_counter()
while n < 200:
    ok, img = cap.read()
    if not ok:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        continue
    n += 1
el = time.perf_counter() - t0
print("read %d frames in %.3f s -> %.1f fps, %.2f ms/frame" % (n, el, n/el, el/n*1000))
