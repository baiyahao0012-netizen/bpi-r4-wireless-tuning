import asyncio, time
from webrtc_peer import CameraTrack

async def main():
    tr = CameraTrack(video="clip.mp4", fps=30)
    n = 0
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < 5.0:
        await tr.recv()
        n += 1
    el = time.perf_counter() - t0
    print("track produced %d frames in %.2f s -> %.1f fps" % (n, el, n/el))

asyncio.run(main())
