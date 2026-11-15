"""NTP-style time probe server (run on Windows).

Client sends t1 (its send time), server replies with t2 (receive) and t3 (send).
offset = ((t2 - t1) + (t3 - t4)) / 2 ; rtt = (t4 - t1) - (t3 - t2)
"""
import socket
import struct
import time

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("0.0.0.0", 9977))
s.listen(8)
print("time probe server on 9977", flush=True)
while True:
    conn, _ = s.accept()
    try:
        data = conn.recv(8)
        if len(data) == 8:
            struct.unpack("!d", data)
            t2 = time.time()
            t3 = time.time()
            conn.sendall(struct.pack("!dd", t2, t3))
    finally:
        conn.close()
