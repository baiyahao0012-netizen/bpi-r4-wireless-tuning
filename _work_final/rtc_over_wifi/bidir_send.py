from scapy.all import Ether, Raw, sendp
iface=r"\Device\NPF_{C33D086D-AA6B-4D75-8D9F-03881CC0B98D}"
for i in range(5):
    p=Ether(src="90:de:80:1c:6a:7a",dst="36:19:86:e0:2e:0f",type=0x88b5)/Raw(b"PC_TO_AP_%d"%i)
    sendp(p,iface=iface,verbose=False); print("sent",i)
