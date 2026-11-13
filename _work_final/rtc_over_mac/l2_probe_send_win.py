from scapy.all import Ether, sendp
import time

IFACE = r"\Device\NPF_{A2958734-FBD5-4E72-AD1C-362588589CD1}"
SRC = "40:c2:ba:52:70:95"
DST = "90:de:80:1c:6a:7a"
for i in range(20):
    pkt = Ether(src=SRC, dst=DST, type=0x88B5) / (b"RTC2PROBE" + i.to_bytes(4, "big") + b"\x00" * 16)
    sendp(pkt, iface=IFACE, verbose=False)
    print("sent", i, flush=True)
    time.sleep(0.2)
