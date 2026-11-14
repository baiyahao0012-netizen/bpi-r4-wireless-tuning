import socket
import sys

port = int(sys.argv[1])
timeout = float(sys.argv[2]) if len(sys.argv) > 2 else 10.0
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 8 * 1024 * 1024)
s.bind(("0.0.0.0", port))
s.settimeout(timeout)
n = 0
first = None
last = None
try:
    while True:
        d, a = s.recvfrom(65535)
        n += 1
        if first is None:
            first = a
        last = a
except socket.timeout:
    pass
print("port=%d received=%d src_first=%s src_last=%s" % (port, n, first, last), flush=True)
