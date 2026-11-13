"""最小演示：A 通过 UDP 发送数字 '1' 给 B。

只做三件事：
  1) 手工拼一个 12 字节的 RTP 头（没有任何库）
  2) 用 UDP socket 发出去
  3) 接收端拆头，把载荷取回来

运行：python rtp_udp_demo.py
"""

import socket
import struct
import threading

HOST = "127.0.0.1"
PORT = 9999
SSRC = 0x11223344
PT = 96          # 动态载荷类型，SDP 里协商成 H.264 用的就是这个号


def build_rtp(payload, seq, ts, marker=1):
    """拼 RTP 包。12 字节固定头 + 载荷。

    struct 格式 "!BBHII" 逐段对应：
        !  网络字节序（大端）
        B  version(2) | padding(1) | extension(1) | CC(4)   -> 0x80 = V2, 其余全 0
        B  marker(1) | payload type(7)
        H  sequence number (16 位)
        I  timestamp (32 位，90 kHz)
        I  SSRC (32 位)
    合计 1+1+2+4+4 = 12 字节。
    """
    b0 = 0x80                          # V=2, P=0, X=0, CC=0
    b1 = (marker << 7) | PT            # M=1, PT=96
    header = struct.pack("!BBHII", b0, b1, seq, ts, SSRC)
    return header + payload


def parse_rtp(packet):
    """拆 RTP 包，返回 (字段字典, 载荷)。"""
    b0, b1, seq, ts, ssrc = struct.unpack("!BBHII", packet[:12])
    fields = {
        "V": (b0 >> 6) & 0x03,
        "P": (b0 >> 5) & 0x01,
        "X": (b0 >> 4) & 0x01,
        "CC": b0 & 0x0F,
        "M": (b1 >> 7) & 0x01,
        "PT": b1 & 0x7F,
        "seq": seq,
        "ts": ts,
        "ssrc": ssrc,
    }
    return fields, packet[12:]


def hexdump(data):
    return " ".join(f"{b:02x}" for b in data)


def receiver(ready, results):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, PORT))
    sock.settimeout(5)
    ready.set()
    for _ in range(3):
        packet, addr = sock.recvfrom(2048)
        fields, payload = parse_rtp(packet)
        results.append((packet, fields, payload, addr))
    sock.close()


def main():
    ready = threading.Event()
    results = []
    th = threading.Thread(target=receiver, args=(ready, results), daemon=True)
    th.start()
    ready.wait()

    sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # 30 fps -> 90 kHz 时钟每帧步长 90000/30 = 3000
    for i, digit in enumerate([b"1", b"2", b"3"]):
        seq = i + 1
        ts = i * 3000
        packet = build_rtp(digit, seq, ts)
        sender.sendto(packet, (HOST, PORT))
        print(f"[A] payload={digit!r}  seq={seq}  ts={ts}")
        print(f"[A] 打包后 {len(packet)} 字节: {hexdump(packet)}")
        print(f"[A] sendto -> {HOST}:{PORT} (SOCK_DGRAM / UDP)")
        print()

    sender.close()
    th.join(timeout=5)

    for packet, fields, payload, addr in results:
        print(f"[B] 收到 {len(packet)} 字节 from {addr[0]}:{addr[1]}")
        print(f"[B] 拆头: {fields}")
        print(f"[B] 取出载荷: {payload!r}  -> 还原成数字 {payload.decode()}")
        print()

    print("=" * 60)
    print("内核全程只做了一件事：把这段字节塞进 UDP 包，加 8 字节 UDP 头")
    print("和 20 字节 IP 头，交给网卡。它不认识 RTP，也没碰过 RTP。")


if __name__ == "__main__":
    main()
