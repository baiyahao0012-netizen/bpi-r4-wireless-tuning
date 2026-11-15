"""Local UDP relay for the T8 real-link receiver.

Windows Firewall allows python.exe but not gst-launch.exe; this relay receives
RTP on the public ports (python) and forwards it to gst-launch on loopback.
Only inbound RTP needs relaying; RTCP outbound goes straight to the Pi.
"""
import socket
import threading
import time


def relay(listen_port, target_port):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 8 * 1024 * 1024)
    s.bind(("0.0.0.0", listen_port))
    out = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    n = 0
    while True:
        try:
            data, _ = s.recvfrom(65535)
        except OSError:
            break
        out.sendto(data, ("127.0.0.1", target_port))
        n += 1
        if n % 1000 == 0:
            print("relay %d->%d: %d packets" % (listen_port, target_port, n), flush=True)


threading.Thread(target=relay, args=(5004, 6004), daemon=True).start()
threading.Thread(target=relay, args=(5008, 6008), daemon=True).start()
print("relay up: 5004->6004, 5008->6008", flush=True)
while True:
    time.sleep(3600)
