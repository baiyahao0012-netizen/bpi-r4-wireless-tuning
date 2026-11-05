# -*- coding: utf-8 -*-
"""Transport abstraction: the ONLY thing that differs between the two arms.

  l2  : RTC2 frame 直接放进以太网帧载荷   (RTC -> Ethernet -> 802.11)
  udp : RTC2 frame 放进 UDP 载荷, 由内核加 IP/UDP 头
        (RTC -> UDP -> IP -> Ethernet -> 802.11)

Everything above this layer (framing, pacing, jitter buffer, feedback, audio)
is identical, so any measured difference is attributable to the stack only.
"""
import socket
import l2sock
import rtc2

# Wire cost charged to the pacer, per packet.
#   l2  : Ethernet header 14
#   udp : Ethernet 14 + IPv4 20 + UDP 8 = 42
OVERHEAD = {'l2': 14, 'udp': 42}


class DataTx(object):
    def __init__(self, transport, eth_dev='GbE Family',
                 dst_mac='C0-35-32-19-CC-FB', src_mac='40-C2-BA-52-70-95',
                 dst_ip='192.168.240.147', dst_port=9922,
                 src_ip='192.168.240.2'):
        self.transport = transport
        self.overhead = OVERHEAD[transport]
        if transport == 'l2':
            self.sock = l2sock.L2Socket(dev_substr=eth_dev,
                                        direction=l2sock.PCAP_D_OUT)
            self._dst = l2sock.mac_to_bytes(dst_mac)
            self._src = l2sock.mac_to_bytes(src_mac)
            self.desc = 'l2 raw -> %s via %s' % (dst_mac, self.sock.desc)
        else:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.bind((src_ip, 0))
            try:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1 << 20)
            except Exception:
                pass
            self.sock = s
            self._dst = (dst_ip, dst_port)
            self._src = (src_ip, s.getsockname()[1])
            self.desc = 'udp %s:%d -> %s:%d' % (src_ip, self._src[1],
                                                dst_ip, dst_port)

    def send(self, frame):
        if self.transport == 'l2':
            self.sock.send(self._dst + self._src
                           + rtc2.ETH_DATA.to_bytes(2, 'big') + frame)
        else:
            self.sock.sendto(frame, self._dst)

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass


class FbTx(object):
    """Receiver-side feedback sender."""

    def __init__(self, transport, eth_dev='GbE Family',
                 dst_mac='C0-35-32-19-CC-FB', src_mac='40-C2-BA-52-70-95',
                 dst_ip='192.168.240.2', dst_port=9923, ethertype=None):
        self.transport = transport
        self.etype = rtc2.ETH_FEEDBACK if ethertype is None else ethertype
        if transport == 'l2':
            # Wi-Fi cannot inject, so the frame is addressed to this station's
            # own MAC and pushed out the Ethernet port; the board's bridge
            # forwards it out the radio.
            self.sock = l2sock.L2Socket(dev_substr=eth_dev,
                                        direction=l2sock.PCAP_D_OUT)
            self._dst = l2sock.mac_to_bytes(dst_mac)
            self._src = l2sock.mac_to_bytes(src_mac)
        else:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1 << 20)
            self.sock = s
            self._dst = (dst_ip, dst_port)

    def send(self, payload):
        if self.transport == 'l2':
            self.sock.send(self._dst + self._src
                           + self.etype.to_bytes(2, 'big') + payload)
        else:
            self.sock.sendto(payload, self._dst)

    def send_to_mac(self, dst_bytes, payload):
        """Send to a MAC learned at runtime (e.g. a sync request's source)."""
        if self.transport == 'l2':
            self.sock.send(dst_bytes + self._src
                           + self.etype.to_bytes(2, 'big') + payload)
        else:
            self.sock.sendto(payload, self._dst)

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass


class FbRx(object):
    """Sender-side feedback receiver."""

    def __init__(self, transport, iface='8852', port=9923, bind_ip=''):
        self.transport = transport
        if transport == 'l2':
            self.sock = l2sock.L2Socket(dev_substr=iface,
                                        direction=l2sock.PCAP_D_IN)
            self.desc = 'l2 capture on ' + self.sock.desc
        else:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 2 << 20)
            except Exception:
                pass
            s.bind((bind_ip, port))
            s.settimeout(0.2)
            self.sock = s
            self.desc = 'udp :%d' % port

    def recv_any(self, timeout_s):
        """Return (ethertype, payload, src_mac) or None.

        Delivers both feedback frames and control frames so one capture handle
        can serve the feedback loop and the clock-sync responder.
        """
        if self.transport == 'l2':
            r = self.sock.recv(timeout_s)
            if not r:
                return None
            raw = r[1]
            if len(raw) < 14:
                return None
            et = rtc2.ethertype_of(raw)
            src = raw[6:12]
            if et == rtc2.ETH_FEEDBACK:
                return (et, raw[14:14 + rtc2.FB_LEN], src)
            if et == rtc2.ETH_CONTROL:
                return (et, raw[14:], src)
            return None
        try:
            data, addr = self.sock.recvfrom(2048)
            return (rtc2.ETH_FEEDBACK, data, bytes(6))
        except socket.timeout:
            return None

    def recv(self, timeout_s):
        """Return feedback payload bytes only (kept for the old call sites)."""
        item = self.recv_any(timeout_s)
        if item is None:
            return None
        et, payload, _src = item
        return payload if et == rtc2.ETH_FEEDBACK else None
        try:
            data, _ = self.sock.recvfrom(2048)
            return data
        except socket.timeout:
            return None

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass


class CtrlRx(object):
    """Capture control frames (EtherType 0x88B7) — used for clock sync."""

    def __init__(self, transport, iface='8852', port=9924, bind_ip=''):
        self.transport = transport
        if transport == 'l2':
            self.sock = l2sock.L2Socket(dev_substr=iface,
                                        direction=l2sock.PCAP_D_IN)
            self.desc = 'ctrl on ' + self.sock.desc
        else:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((bind_ip, port))
            s.settimeout(0.2)
            self.sock = s
            self.desc = 'udp ctrl :%d' % port

    def recv_any(self, timeout_s):
        """Return (payload, src_mac) or None."""
        if self.transport == 'l2':
            r = self.sock.recv(timeout_s)
            if not r:
                return None
            raw = r[1]
            if len(raw) < 14 or rtc2.ethertype_of(raw) != rtc2.ETH_CONTROL:
                return None
            return (raw[14:], raw[6:12])
        try:
            data, _addr = self.sock.recvfrom(2048)
            return (data, bytes(6))
        except socket.timeout:
            return None

    def recv(self, timeout_s):
        item = self.recv_any(timeout_s)
        return None if item is None else item[0]

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass


class DataRx(object):
    def __init__(self, transport, iface='8852', port=9922, bind_ip=''):
        self.transport = transport
        if transport == 'l2':
            self.sock = l2sock.L2Socket(dev_substr=iface,
                                        direction=l2sock.PCAP_D_IN)
            self.desc = 'l2 capture on ' + self.sock.desc
        else:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 8 << 20)
            except Exception:
                pass
            s.bind((bind_ip, port))
            s.settimeout(0.05)
            self.sock = s
            self.desc = 'udp :%d (rcvbuf 8 MB)' % port

    def recv(self, timeout_s):
        """Return (now_perf_counter, rtc2_frame_bytes) or None."""
        if self.transport == 'l2':
            r = self.sock.recv(timeout_s)
            if not r:
                return None
            raw = r[1]
            if len(raw) < 14 + rtc2.HDR_LEN:
                return ('skip', None)
            if rtc2.ethertype_of(raw) != rtc2.ETH_DATA:
                return ('other', None)
            return (time.perf_counter(), raw[14:])
        try:
            data, _ = self.sock.recvfrom(65535)
        except socket.timeout:
            return None
        return (time.perf_counter(), data)

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass


import time  # noqa: E402  (used by DataRx.recv)
