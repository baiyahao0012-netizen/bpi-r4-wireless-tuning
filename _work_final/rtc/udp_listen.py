import socket, time
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(('0.0.0.0', 9931))
s.settimeout(6)
n = 0
try:
    while n < 5:
        d, a = s.recvfrom(512)
        print("from", a, d.decode('ascii', 'replace').strip())
        n += 1
except socket.timeout:
    print("timeout, got", n)
