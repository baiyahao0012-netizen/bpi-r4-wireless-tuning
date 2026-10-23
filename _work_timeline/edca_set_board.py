#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# edca_set.py - 通过 nl80211 实时设置 AP 下行 EDCA（无需重启 WiFi）
# 用法: python3 edca_set.py <接口> <AC> <aifs> <cwmin> <cwmax> <txop>
# 示例: python3 edca_set.py phy0.0-ap0 2 1 3 7 94   (改 VI 为激进值)
# AC 参数约定（用户友好顺序，与 hostapd 文档一致）:
#   0=BE 1=BK 2=VI 3=VO
# 内核 nl80211/IEEE80211 AC 枚举相反: VO=0 VI=1 BE=2 BK=3
# 脚本内部自动转换后再下发；驱动 mt7996_conf_tx 的 mq_to_aci 表
# (VO->3 VI->2 BE->0 BK->1) 会把参数落到正确的固件 ACI。

import socket, struct, sys, os, random

NETLINK_GENERIC = 16
NLMSG_ERROR = 2
NLM_F_REQUEST = 0x01
NLM_F_ACK = 0x04
NLM_F_ACK_TLVS = 0x200
NLMSG_HDRLEN = 16
GENL_HDRLEN = 4
NLA_HDRLEN = 4
NLA_F_NEST = 0x8000
NLA_TYPE_MASK = 0x3fff

GENL_ID_CTRL = 16
CTRL_CMD_GETFAMILY = 3
CTRL_ATTR_FAMILY_ID = 1
CTRL_ATTR_FAMILY_NAME = 2

NL80211_GENL_NAME = "nl80211"
NL80211_GENL_VERSION = 1
NL80211_CMD_SET_WIPHY = 2
NL80211_ATTR_WIPHY = 1
NL80211_ATTR_IFINDEX = 3
# 6.6 内核已移除 NL80211_ATTR_TXQ_INFO(旧=13)；TXQ 下发改走 SET_WIPHY + WIPHY_TXQ_PARAMS
NL80211_ATTR_WIPHY_TXQ_PARAMS = 37
TXQ_SUBBLOCK_TYPE = 13
NL80211_TXQ_ATTR_AC = 1
NL80211_TXQ_ATTR_TXOP = 2
NL80211_TXQ_ATTR_CWMIN = 3
NL80211_TXQ_ATTR_CWMAX = 4
NL80211_TXQ_ATTR_AIFS = 5

# 用户 AC（BE=0 BK=1 VI=2 VO=3）-> 内核 nl80211 AC（VO=0 VI=1 BE=2 BK=3）
USER_AC_TO_NL80211 = [2, 3, 1, 0]

def align(n):
    return (n + 3) & ~3

def nla(t, payload):
    length = NLA_HDRLEN + len(payload)
    return struct.pack('HH', length, t) + payload + b'\x00' * (align(length) - length)

def nla_nested(t, children):
    body = b''.join(children)
    length = align(NLA_HDRLEN + len(body))
    return struct.pack('HH', length, t | NLA_F_NEST) + body + b'\x00' * (length - NLA_HDRLEN - len(body))

def genl_msg(family, cmd, attrs):
    body = b''.join(attrs)
    length = align(NLMSG_HDRLEN + GENL_HDRLEN + len(body))
    seq = random.randint(1, 0x7fffffff)
    nlh = struct.pack('IHHII', length, family, NLM_F_REQUEST | NLM_F_ACK | NLM_F_ACK_TLVS, seq, 0)
    gh = struct.pack('BBH', cmd, NL80211_GENL_VERSION, 0)
    return nlh + gh + body + b'\x00' * (length - NLMSG_HDRLEN - GENL_HDRLEN - len(body)), seq

def wait_ack(sock, seq):
    sock.settimeout(3)
    while True:
        try:
            data = sock.recv(65535)
        except socket.timeout:
            return -999
        pos = 0
        while pos + NLMSG_HDRLEN <= len(data):
            nl_len = struct.unpack_from('I', data, pos)[0]
            s_seq = struct.unpack_from('I', data, pos + 8)[0]
            if s_seq == seq:
                typ = struct.unpack_from('H', data, pos + 4)[0]
                if typ == NLMSG_ERROR:
                    err = struct.unpack_from('i', data, pos + 16)[0]
                    if err != 0:
                        emsg = ''
                        off = pos + 20
                        end = min(pos + nl_len, len(data))
                        while off + 4 <= end:
                            alen, atype = struct.unpack_from('HH', data, off)
                            if alen < 4:
                                break
                            if (atype & NLA_TYPE_MASK) == 1 and alen >= 8:
                                emsg = data[off + 4:off + alen].decode('utf-8', 'replace')
                                break
                            off += align(alen)
                        print('内核错误详情: %s' % emsg)
                    return err
                if typ == 3:
                    return 0
            if nl_len < 16:
                break
            pos += align(nl_len)

def get_family_id(sock):
    name = nla(CTRL_ATTR_FAMILY_NAME, b'nl80211\x00')
    msg, seq = genl_msg(GENL_ID_CTRL, CTRL_CMD_GETFAMILY, [name])
    sock.send(msg)
    sock.settimeout(3)
    while True:
        try:
            data = sock.recv(65535)
        except socket.timeout:
            raise RuntimeError('等待 GETFAMILY 响应超时')
        pos = 0
        while pos + NLMSG_HDRLEN <= len(data):
            nl_len = struct.unpack_from('I', data, pos)[0]
            typ = struct.unpack_from('H', data, pos + 4)[0]
            s_seq = struct.unpack_from('I', data, pos + 8)[0]
            if s_seq == seq:
                if typ == NLMSG_ERROR:
                    raise RuntimeError('GETFAMILY 返回错误')
                off = pos + NLMSG_HDRLEN + GENL_HDRLEN
                end = min(pos + nl_len, len(data))
                while off + 4 <= end:
                    alen, atype = struct.unpack_from('HH', data, off)
                    if alen < 4:
                        break
                    if (atype & NLA_TYPE_MASK) == CTRL_ATTR_FAMILY_ID and alen >= 6:
                        if alen >= 8:
                            return struct.unpack_from('I', data, off + 4)[0]
                        return struct.unpack_from('H', data, off + 4)[0]
                    off += align(alen)
                raise RuntimeError('GETFAMILY 响应未找到 FAMILY_ID, hex=' + data.hex())
            if nl_len < 16:
                break
            pos += align(nl_len)

def ifindex_of(name):
    p = '/sys/class/net/%s/ifindex' % name
    if os.path.exists(p):
        return int(open(p).read().strip())
    raise RuntimeError('接口不存在: %s' % name)

def main():
    if len(sys.argv) != 7:
        print(__doc__)
        sys.exit(1)
    name, ac, aifs, cwmin, cwmax, txop = (sys.argv[1], int(sys.argv[2]), int(sys.argv[3]),
                                          int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6]))
    if not 0 <= ac <= 3:
        sys.exit('AC 必须 0~3 (0=BE 1=BK 2=VI 3=VO)')
    ac_nl = USER_AC_TO_NL80211[ac]
    if not (0 <= aifs <= 255 and 0 <= cwmin <= 65535 and 0 <= cwmax <= 65535 and 0 <= txop <= 65535):
        sys.exit('参数越界: aifs<=255, cwmin/cwmax/txop<=65535')
    wiphy = None
    if name.startswith('phy'):
        try:
            wiphy = int(name[3:].split('.')[0])
        except ValueError:
            pass
    ifindex = ifindex_of(name)
    sock = socket.socket(socket.AF_NETLINK, socket.SOCK_RAW, NETLINK_GENERIC)
    try:
        sock.bind((0, 0))
        fam = get_family_id(sock)
        print('nl80211 family id =', fam)
        attrs = [nla(NL80211_ATTR_IFINDEX, struct.pack('i', ifindex))]
        if wiphy is not None:
            attrs.append(nla(NL80211_ATTR_WIPHY, struct.pack('i', wiphy)))
        txq = [nla(NL80211_TXQ_ATTR_AC, struct.pack('B', ac_nl)),
               nla(NL80211_TXQ_ATTR_TXOP, struct.pack('H', txop)),
               nla(NL80211_TXQ_ATTR_CWMIN, struct.pack('H', cwmin)),
               nla(NL80211_TXQ_ATTR_CWMAX, struct.pack('H', cwmax)),
               nla(NL80211_TXQ_ATTR_AIFS, struct.pack('B', aifs))]
        # 6.6 结构: WIPHY_TXQ_PARAMS{ 每AC一个TXQ子块{ AC/TXOP/CWMIN/CWMAX/AIFS } }
        sub = nla_nested(TXQ_SUBBLOCK_TYPE, txq)
        attrs.append(nla_nested(NL80211_ATTR_WIPHY_TXQ_PARAMS, [sub]))
        msg, seq = genl_msg(fam, NL80211_CMD_SET_WIPHY, attrs)
        sock.send(msg)
        err = wait_ack(sock, seq)
        if err == 0:
            ac_name = {0: 'BE', 1: 'BK', 2: 'VI', 3: 'VO'}[ac]
            print('OK: %s AC%d(%s) aifs=%d cwmin=%d cwmax=%d txop=%d' % (name, ac, ac_name, aifs, cwmin, cwmax, txop))
            print('验证: cat /sys/kernel/debug/ieee80211/phy*/mt76/edca')
        else:
            print('内核返回错误 %d: %s' % (err, os.strerror(abs(err)) if err < 0 else ''))
            sys.exit(1)
    finally:
        sock.close()

if __name__ == '__main__':
    main()
