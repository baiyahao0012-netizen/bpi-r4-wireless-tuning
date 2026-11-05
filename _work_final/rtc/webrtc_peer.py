# -*- coding: utf-8 -*-
"""Standard WebRTC peer (UNMODIFIED stack) used as the control group.

Sender: camera -> H.264 -> RTP/SRTP -> UDP/IP -> Wi-Fi
Receiver: Wi-Fi -> UDP/IP -> SRTP/RTP -> decode

Signalling is a single HTTP POST so no extra infrastructure is needed.

    python webrtc_peer.py receiver --port 8000 --seconds 25
    python webrtc_peer.py sender --signal http://192.168.240.162:8000 --seconds 20
"""
import argparse
import asyncio
import json
import sys
import time

import aiohttp
from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiortc.rtcrtpparameters import RTCRtpEncodingParameters
from aiortc.rtcrtpsender import RTCRtpSender
from aiortc.mediastreams import MediaStreamError


class CameraTrack(VideoStreamTrack):
    """cv2 camera -> aiortc video track (bgr24)."""

    kind = "video"

    def __init__(self, index=0, width=640, height=480, fps=15, video=""):
        super().__init__()
        import cv2
        self.cv2 = cv2
        self.is_file = bool(video)
        if self.is_file:
            self.cap = cv2.VideoCapture(video)
        else:
            self.cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            self.cap.set(cv2.CAP_PROP_FPS, fps)
        self.last = None
        self.n = 0

    async def recv(self):
        pts, time_base = await self.next_timestamp()
        ok, img = self.cap.read()
        if not ok and self.is_file:
            self.cap.set(self.cv2.CAP_PROP_POS_FRAMES, 0)   # loop the clip
            ok, img = self.cap.read()
        if not ok:
            if self.last is None:
                raise MediaStreamError
            img = self.last
        else:
            self.last = img
        self.n += 1
        from av import VideoFrame
        f = VideoFrame.from_ndarray(img, format="bgr24")
        f.pts = pts
        f.time_base = time_base
        return f


def filter_sdp(sdp, keep_ip):
    """Keep only ICE candidates on keep_ip.

    Both hosts sit on the same LAN over two paths (wire + Wi-Fi).  Without
    filtering, ICE may pick the wired pair and the media never crosses the
    radio, which would invalidate the whole comparison.
    """
    if not keep_ip:
        return sdp
    keep = [l for l in sdp.splitlines()
            if not (l.startswith("a=candidate:") and keep_ip not in l)]
    return "\r\n".join(keep) + "\r\n"


async def wait_ice(pc, timeout=8.0):
    t = time.time()
    while pc.iceGatheringState != "complete" and time.time() - t < timeout:
        await asyncio.sleep(0.05)


async def dump_stats(pc, label):
    stats = await pc.getStats()
    for rep in stats.values():
        t = getattr(rep, "type", "")
        if t in ("outbound-rtp", "inbound-rtp", "candidate-pair"):
            d = dict(vars(rep))
            keep = {k: v for k, v in d.items()
                    if k not in ("timestamp", "id", "type", "kind")}
            print("[%s] %s %s" % (label, t, keep), flush=True)


async def run_receiver(args):
    pc = RTCPeerConnection()
    got = {"frames": 0, "t0": None}

    @pc.on("track")
    def on_track(track):
        print("track received:", track.kind, flush=True)

        async def consume():
            while True:
                try:
                    f = await track.recv()
                except Exception:
                    break
                got["frames"] += 1
                if got["t0"] is None:
                    got["t0"] = time.time()
        asyncio.ensure_future(consume())

    async def offer_handler(request):
        data = await request.json()
        print("offer received", flush=True)
        await pc.setRemoteDescription(
            RTCSessionDescription(sdp=data["sdp"], type=data["type"]))
        ans = await pc.createAnswer()
        await pc.setLocalDescription(ans)
        await wait_ice(pc)
        print("answer ready, ice=%s" % pc.iceGatheringState, flush=True)
        return web.json_response(
            {"sdp": filter_sdp(pc.localDescription.sdp, args.ice_ip),
             "type": pc.localDescription.type})

    app = web.Application()
    app.router.add_post("/offer", offer_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", args.port)
    await site.start()
    print("signalling on :%d, waiting for offer" % args.port, flush=True)

    t_end = time.time() + args.seconds
    while time.time() < t_end:
        await asyncio.sleep(1.0)
    await dump_stats(pc, "rx")
    print("RESULT webrtc remote_frames=%d" % got["frames"], flush=True)
    await pc.close()
    await runner.cleanup()


async def run_sender(args):
    pc = RTCPeerConnection()
    track = CameraTrack(args.cam, args.width, args.height, args.fps,
                        args.video)
    sender = pc.addTrack(track)

    # Match the codec and bitrate used by the L2 arm, otherwise the two arms
    # carry wildly different loads and the comparison means nothing.
    if args.codec:
        try:
            caps = RTCRtpSender.getCapabilities("video")
            want = [c for c in caps.codecs
                    if c.mimeType.lower() == "video/" + args.codec.lower()]
            if want:
                for tr in pc.getTransceivers():
                    tr.setCodecPreferences(want + [c for c in caps.codecs
                                                   if c not in want])
                print("codec forced to", want[0].mimeType, flush=True)
        except Exception as e:
            print("codec preference failed: %r" % (e,), flush=True)
    # aiortc has no public bitrate API: the encoder starts at 1 Mbps and is
    # normally steered by receiver REMB.  We pin it so both arms carry the
    # same load.

    @pc.on("connectionstatechange")
    async def on_state():
        print("state:", pc.connectionState, flush=True)

    offer = await pc.createOffer()
    await pc.setLocalDescription(offer)
    await wait_ice(pc)
    print("offer ready, ice=%s" % pc.iceGatheringState, flush=True)

    async with aiohttp.ClientSession() as s:
        async with s.post(args.signal + "/offer",
                          json={"sdp": filter_sdp(pc.localDescription.sdp,
                                                  args.ice_ip),
                                "type": pc.localDescription.type}) as r:
            ans = await r.json()
    await pc.setRemoteDescription(
        RTCSessionDescription(sdp=ans["sdp"], type=ans["type"]))
    print("answer applied, state=%s" % pc.connectionState, flush=True)

    t_end = time.time() + args.seconds
    enc_set = False
    while time.time() < t_end:
        if not enc_set and args.bitrate:
            enc = getattr(sender, "_RTCRtpSender__encoder", None)
            if enc is not None and hasattr(enc, "target_bitrate"):
                try:
                    enc.target_bitrate = args.bitrate
                    enc_set = True
                    print("encoder target_bitrate =", args.bitrate, flush=True)
                except Exception as e:
                    print("bitrate set failed: %r" % (e,), flush=True)
        await asyncio.sleep(0.5)
    await dump_stats(pc, "tx")
    print("RESULT webrtc frames_captured=%d" % track.n, flush=True)
    await pc.close()
    try:
        track.cap.release()
    except Exception:
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("role", choices=["sender", "receiver"])
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--signal", default="http://127.0.0.1:8000")
    ap.add_argument("--seconds", type=float, default=20.0)
    ap.add_argument("--cam", type=int, default=0)
    ap.add_argument("--video", default="", help="use a file instead of the camera")
    ap.add_argument("--width", type=int, default=640)
    ap.add_argument("--height", type=int, default=480)
    ap.add_argument("--fps", type=int, default=15)
    ap.add_argument("--ice-ip", default="",
                    help="only advertise ICE candidates on this local IP")
    ap.add_argument("--codec", default="h264")
    ap.add_argument("--bitrate", type=int, default=2500000)
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if args.role == "receiver":
        asyncio.run(run_receiver(args))
    else:
        asyncio.run(run_sender(args))


if __name__ == "__main__":
    main()
