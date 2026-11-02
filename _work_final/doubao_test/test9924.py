import socket, time
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(("192.168.240.2", 9924))
for _ in range(10):
    s.sendto(b"x" * 100, ("192.168.240.219", 9999))
    time.sleep(0.05)
print("sent 10")
