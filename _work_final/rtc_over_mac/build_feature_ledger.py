# -*- coding: utf-8 -*-
"""Build the RTC over MAC media-plane feature ledger workbook."""
from collections import Counter
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import FormulaRule

OUT = "_work_final/rtc_over_mac/FEATURE_LEDGER_20261109.xlsx"

HEADERS = [
    "ID", "功能域", "功能/子功能", "标准/开源参考", "场景需要",
    "去掉UDP/IP影响", "UDP基线实现", "L2目标实现/补丁", "验证方法",
    "验收标准", "优先级", "阶段", "状态", "备注/风险",
]

ROWS = [
    # ---- MEDIA ----
    ("MED-01", "媒体", "视频解码/透传（H.264）", "GStreamer qtdemux/h264parse/avdec_h264", "必需", "不受影响",
     "已规划", "同基线", "6 条素材解码；统计帧数/错误", "全部可解，解码错误≤基线", "P0", "P0-基线", "待验证", "先透传，不重编码"),
    ("MED-02", "媒体", "H.264 RTP 打包", "RFC 6184；rtph264pay", "必需", "不受影响",
     "已规划", "同基线", "Wireshark 看单 NAL/FU-A/STAP-A", "包格式与分片正确", "P0", "P0-基线", "待验证", "大帧必须走 FU-A"),
    ("MED-03", "媒体", "H.264 RTP 解包/重组", "RFC 6184；rtph264depay", "必需", "不受影响",
     "已规划", "同基线", "pcap + 解码", "重组后帧可解码", "P0", "P0-基线", "待验证", "FU-A 边界"),
    ("MED-04", "媒体", "Opus 编解码", "RFC 6716；opusenc/opusdec", "必需", "不受影响",
     "已规划", "同基线", "音频时长/RMS/波形", "无半速、无爆音", "P0", "P0-基线", "待验证", "48 kHz，20 ms"),
    ("MED-05", "媒体", "Opus RTP 打包/解包", "RFC 7587；rtpopuspay/depay", "必需", "不受影响",
     "已规划", "同基线", "pcap + 解码", "包格式正确，时间戳连续", "P0", "P0-基线", "待验证", "与视频共用 RTCP SR 时基"),
    ("MED-06", "媒体", "AAC→Opus 预处理/5.1 下混", "FFmpeg libopus", "必需", "不适用",
     "未开始", "同基线", "时长/PTS/声道/响度", "时长一致，PTS 连续，立体声", "P0", "P0-基线", "待验证", "六条素材都需预处理"),
    ("MED-07", "媒体", "MP4/MKV demux 与 PTS", "qtdemux/matroskademux", "必需", "不受影响",
     "已规划", "同基线", "PTS 单调性/帧间隔", "24/25/30 fps 步长正确", "P0", "P0-基线", "待验证", "建议预处理成 MKV"),
    ("MED-08", "媒体", "视频帧完整性/解码错误", "h264parse + decoder", "必需", "不受影响",
     "已规划", "同基线", "解码错误数/帧数", "错误≤基线", "P0", "P0-基线", "待验证", "按帧记录"),
    ("MED-09", "媒体", "音频 PLC/丢包隐藏", "Opus PLC", "可选", "不受影响",
     "未开始", "同基线", "丢包音频主观/波形", "无明显爆音", "P2", "P2-后续", "待验证", "第一阶段可后置"),
    ("MED-10", "媒体", "关键帧/IDR/PLI", "GOP + RTCP PLI", "必需", "部分影响",
     "未开始", "同基线 + L2 RTCP", "丢包后请求 IDR", "解码恢复≤1 个 GOP", "P1", "P1-L2", "待补丁", "低帧率下 IDR 很贵，先限速"),
    ("MED-11", "媒体", "视频渲染/录制", "autovideosink/filesink", "必需", "不受影响",
     "已规划", "同基线", "录片/帧数/时间戳", "可回放，帧数一致", "P0", "P0-基线", "待验证", "参考接收端"),
    ("MED-12", "媒体", "音频播放/录制", "autoaudiosink/filesink", "必需", "不受影响",
     "已规划", "同基线", "录音频/时长", "可回放，时长一致", "P0", "P0-基线", "待验证", "参考接收端"),

    # ---- RTP ----
    ("RTP-01", "RTP", "RTP 头：seq/timestamp/SSRC/PT/marker", "RFC 3550；rtpbin", "必需", "不受影响",
     "已规划", "同基线", "Wireshark RTP 解析", "字段正确，序号连续", "P0", "P0-基线", "待验证", "标准 RTP"),
    ("RTP-02", "RTP", "90 kHz 时间戳/24/25/30 步长", "RFC 3550", "必需", "不受影响",
     "已规划", "同基线", "pcap 计算帧间步长", "3750/3600/3000", "P0", "P0-基线", "待验证", "整数帧率"),
    ("RTP-03", "RTP", "RTP 头扩展 MID/RID/abs-send-time", "RFC 8285", "可选", "不受影响",
     "未开始", "同基线", "pcap 扩展解析", "按需启用", "P2", "P2-后续", "待验证", "单流可先不用"),
    ("RTP-04", "RTP", "RTP/RTCP mux 与分流", "RFC 5761；rtpbin", "必需", "部分影响",
     "未开始", "L2 shim type 分流", "pcap 检查 RTP/RTCP", "两种包都可收", "P0", "P0-基线", "待补丁", "L2 没有端口对"),
    ("RTP-05", "RTP", "BUNDLE/多流复用", "RFC 8843", "不需要", "不受影响",
     "不实现", "不实现", "无", "不验收", "P2", "裁剪", "待裁剪", "单流场景不需要"),
    ("RTP-06", "RTP", "RTP padding/通用扩展", "RFC 3550/8285", "可选", "不受影响",
     "未开始", "同基线", "pcap", "不破坏解析", "P2", "P2-后续", "待验证", "按需"),
    ("RTP-07", "RTP", "序号回绕/扩展序号", "RFC 3550；ROC", "必需", "不受影响",
     "未开始", "同基线", "10 min 长跑/序号检查", "无错误回绕", "P1", "P1-L2", "待验证", "20 Mbps 下回绕很快"),
    ("RTP-08", "RTP", "RTX/NACK 重传", "RFC 4588/4585；rtpbin", "必需", "部分影响",
     "未开始", "L2 反馈通路", "0.1%/突发丢包", "恢复率≥95%", "P1", "P1-L2", "待补丁", "反馈也要走 L2"),
    ("RTP-09", "RTP", "FEC ULPFEC/FlexFEC", "RFC 8627；rtpulpfec", "可选", "部分影响",
     "未开始", "L2 承载", "丢包注入", "FEC 可恢复", "P1", "P1-L2", "待补丁", "大帧场景重要"),
    ("RTP-10", "RTP", "抖动缓冲", "GStreamer rtpjitterbuffer", "必需", "不受影响",
     "已规划", "同基线", "到达抖动/出队间隔 p95", "不欠载/不爆缓冲", "P0", "P0-基线", "待验证", "初始 100–200 ms"),
    ("RTP-11", "RTP", "乱序/重复/迟到处理", "rtpjitterbuffer", "必需", "不受影响",
     "已规划", "同基线", "注入乱序/重复", "按 PTS 正确出队", "P0", "P0-基线", "待验证", "按帧丢弃"),
    ("RTP-12", "RTP", "发送 pacing", "queue/pacer", "必需", "部分影响",
     "未开始", "同基线 + L2 开销", "码率/突发", "无长突发，空口不爆", "P1", "P1-L2", "待补丁", "L2 头开销要计入"),
    ("RTP-13", "RTP", "Payload Type 映射", "RTP/SDP", "必需", "不受影响",
     "已规划", "同基线", "pcap/接收 caps", "PT 与配置一致", "P0", "P0-基线", "待验证", "H.264/Opus 两个 PT"),
    ("RTP-14", "RTP", "RTP/RTCP 带宽分配", "RFC 3550", "可选", "部分影响",
     "未开始", "同基线 + L2", "pcap 带宽", "RTCP 不挤占媒体", "P1", "P1-L2", "待补丁", "反馈频率 5–20 Hz"),

    # ---- RTCP ----
    ("RTCP-01", "RTCP", "Sender Report（SR）", "RFC 3550；rtpbin", "必需", "不受影响",
     "已规划", "同基线", "pcap SR NTP/RTP", "字段正确，映射可用", "P0", "P0-基线", "待验证", "A/V sync 依据"),
    ("RTCP-02", "RTCP", "Receiver Report（RR）", "RFC 3550；rtpbin", "必需", "部分影响",
     "未开始", "L2 反馈通路", "pcap RR", "丢包/抖动字段可读", "P0", "P0-基线", "待补丁", "反馈也要无 IP"),
    ("RTCP-03", "RTCP", "SDES/BYE", "RFC 3550", "可选", "不受影响",
     "未开始", "同基线", "pcap", "不影响会话", "P2", "P2-后续", "待验证", "可后置"),
    ("RTCP-04", "RTCP", "NACK", "RFC 4585；rtpbin", "必需", "部分影响",
     "未开始", "L2 反馈通路", "丢包注入", "缺口被重传", "P1", "P1-L2", "待补丁", "限速/去重"),
    ("RTCP-05", "RTCP", "PLI/FIR 关键帧请求", "RFC 4585/5104", "必需", "部分影响",
     "未开始", "L2 反馈通路", "整帧丢失", "下一帧 IDR", "P1", "P1-L2", "待补丁", "100 ms 限速"),
    ("RTCP-06", "RTCP", "REMB/transport-cc", "RFC 8888；GCC", "可选", "部分影响",
     "未开始", "L2 反馈通路", "带宽变化", "码率能跟随", "P2", "P2-后续", "待补丁", "第一阶段固定码率"),
    ("RTCP-07", "RTCP", "RTCP XR", "RFC 3611", "可选", "不受影响",
     "未开始", "同基线", "pcap", "按需", "P2", "P2-后续", "待验证", "可后置"),
    ("RTCP-08", "RTCP", "Compound/RTCP mux", "RFC 3550/5761", "必需", "部分影响",
     "未开始", "L2 shim type 分流", "pcap", "复合包完整", "P0", "P0-基线", "待补丁", "L2 没有端口"),
    ("RTCP-09", "RTCP", "A/V sync SR 映射", "RFC 3550", "必需", "不受影响",
     "未开始", "同基线", "A/V skew p50/p95", "p95≤40 ms", "P0", "P0-基线", "待验证", "音频主时钟"),
    ("RTCP-10", "RTCP", "RTCP 间隔/带宽", "RFC 3550", "必需", "部分影响",
     "未开始", "同基线 + L2", "pcap 周期", "5–20 Hz，不超带宽", "P1", "P1-L2", "待补丁", "与 L2 控制帧共享"),

    # ---- SECURITY ----
    ("SEC-01", "安全", "SRTP 加密/认证", "RFC 3711；srtpenc/dec", "必需", "不受影响",
     "未开始", "同基线", "错误 key/明文检查", "无明文，错误 key 失败", "P0", "P0-基线", "待验证", "PSK 实验室"),
    ("SEC-02", "安全", "SRTP 重放保护", "RFC 3711", "必需", "不受影响",
     "未开始", "同基线", "重放包注入", "重放被拒", "P0", "P0-基线", "待验证", "窗口/ROC"),
    ("SEC-03", "安全", "密钥管理（PSK）", "配置文件/环境变量", "必需", "部分影响",
     "未开始", "L2 侧密钥配置", "轮换/错误 key", "密钥可用可轮换", "P0", "P0-基线", "待补丁", "不进 git"),
    ("SEC-04", "安全", "DTLS-SRTP", "RFC 5764/9147", "可选", "结构性影响",
     "未实现", "DTLS-over-L2 或 PSK", "握手/指纹", "可建立密钥", "P1", "P1-L2", "待补丁", "先 PSK 后 DTLS"),
    ("SEC-05", "安全", "802.1X/MACsec", "IEEE 802.1X/802.1AE", "可选", "结构性影响",
     "未实现", "L2/AP 侧", "认证/加密", "端口认证", "P2", "P2-后续", "待补丁", "产品级后置"),
    ("SEC-06", "安全", "L2 shim 头 HMAC", "自定义", "必需", "结构性影响",
     "未实现", "L2 shim", "篡改头注入", "篡改被拒", "P0", "P1-L2", "待补丁", "SRTP 不保护 shim"),
    ("SEC-07", "安全", "设备身份/证书", "X.509/Device ID", "可选", "结构性影响",
     "未实现", "L2 发现/认证", "身份校验", "设备可认证", "P2", "P2-后续", "待补丁", "MAC 不作为身份"),

    # ---- TRANSPORT ----
    ("TRAN-01", "传输", "UDP/IP 承载", "UDP/IPv4", "必需", "直接移除",
     "已规划", "L2 替代", "pcap 有无 IP 头", "L2 臂无 IP/UDP", "P0", "P0-基线", "待验证", "仅 baseline 使用"),
    ("TRAN-02", "传输", "端口/五元组分流", "UDP 端口", "必需", "结构性影响",
     "未开始", "flow_id + shim type", "pcap/多流", "不依赖端口", "P0", "P0-基线", "待补丁", "L2 没有端口"),
    ("TRAN-03", "传输", "Ethernet/EtherType 封装", "Ethernet II；0x88B5", "必需", "结构性影响",
     "未实现", "L2 shim", "pcap EtherType", "帧格式正确", "P0", "P1-L2", "待补丁", "实验 EtherType"),
    ("TRAN-04", "传输", "MAC 寻址/单播", "Ethernet MAC", "必需", "结构性影响",
     "未实现", "L2 目的/源 MAC", "pcap", "单播可达", "P0", "P1-L2", "待补丁", "不要广播媒体"),
    ("TRAN-05", "传输", "flow_id/会话标识", "自定义", "必需", "结构性影响",
     "未实现", "L2 shim", "多会话测试", "不串流", "P0", "P1-L2", "待补丁", "映射 SSRC/MID"),
    ("TRAN-06", "传输", "MTU/PMTUD/IP 分片", "IP/ICMP", "必需", "结构性影响",
     "未开始", "RTP≤1200；应用层分片", "pcap 最大帧", "无 IP 分片，无超 MTU", "P0", "P1-L2", "待补丁", "控制/DTLS 也要分片"),
    ("TRAN-07", "传输", "UDP checksum/端到端完整性", "UDP checksum", "必需", "结构性影响",
     "未开始", "SRTP auth + shim HMAC", "损坏包注入", "损坏被拒", "P0", "P1-L2", "待补丁", "以太网 FCS 不够"),
    ("TRAN-08", "传输", "DSCP/ECN", "IP QoS", "可选", "结构性影响",
     "未实现", "PCP/WMM", "QoS 标记", "优先级可测", "P1", "P1-L2", "待补丁", "无 ECN"),
    ("TRAN-09", "传输", "802.1p/WMM", "IEEE 802.1p/802.11e", "可选", "结构性影响",
     "未实现", "L2/AP", "抓包/队列", "AC 映射正确", "P1", "P1-L2", "待补丁", "音频/视频分 AC"),
    ("TRAN-10", "传输", "NAT/ICE/STUN/TURN", "RFC 8445/5389/8656", "不需要", "直接移除",
     "不实现", "不实现", "无", "不验收", "P0", "裁剪", "待裁剪", "局域网不需要"),
    ("TRAN-11", "传输", "路由/TTL/环路保护", "IP TTL", "可选", "结构性影响",
     "未实现", "shim TTL", "环路/多跳", "TTL 递减/丢弃", "P1", "P1-L2", "待补丁", "LAN 单跳可后置"),
    ("TRAN-12", "传输", "发现/会话建立", "DHCP/DNS/mDNS/ICE", "必需", "结构性影响",
     "静态配置", "L2 发现/静态 peer", "配对/重启", "可发现/可恢复", "P1", "P1-L2", "待补丁", "先静态"),
    ("TRAN-13", "传输", "SDP c=/m=/candidate", "RFC 8866", "必需", "部分影响",
     "静态配置", "SDP L2 profile", "offer/answer", "L2 地址/flow 可协商", "P1", "P1-L2", "待补丁", "先最小 profile"),
    ("TRAN-14", "传输", "AP L2 bridge/VLAN", "OpenWrt bridge/VLAN", "必需", "结构性影响",
     "已有 br-lan", "L2 bridge/media VLAN", "pcap/隔离", "媒体可达且不绕环", "P0", "P1-L2", "待补丁", "自定义 EtherType 要放行"),
    ("TRAN-15", "传输", "组播/广播", "IGMP/MLD", "不需要", "不适用",
     "不实现", "不实现", "无", "不验收", "P2", "裁剪", "待裁剪", "媒体用单播"),
    ("TRAN-16", "传输", "TCP fallback", "TCP", "不需要", "不适用",
     "不实现", "不实现", "无", "不验收", "P2", "裁剪", "待裁剪", "实时媒体不用 TCP"),

    # ---- OAM ----
    ("OAM-01", "运维", "pcap/Wireshark", "tcpdump/Wireshark", "必需", "不受影响",
     "已规划", "同基线", "抓包/解析", "RTP/RTCP 可解析", "P0", "P0-基线", "待验证", "L2 抓 EtherType"),
    ("OAM-02", "运维", "指标/日志", "GStreamer logs/脚本", "必需", "不受影响",
     "已规划", "同基线", "帧/包/抖动/丢包", "可复现", "P0", "P0-基线", "待验证", "统一 JSON/CSV"),
    ("OAM-03", "运维", "长时/回绕/泄漏", "10 min 长跑", "必需", "不受影响",
     "未开始", "同基线", "长跑", "无崩溃/无回绕错误", "P1", "P1-L2", "待验证", "序号/时间戳"),
    ("OAM-04", "运维", "ICMP/traceroute", "ICMP", "不需要", "直接移除",
     "不实现", "不实现", "无", "不验收", "P2", "裁剪", "待裁剪", "用 LLDP/CFM 替代"),
    ("OAM-05", "运维", "LLDP/CFM 故障定位", "IEEE 802.1AB/802.1ag", "可选", "结构性影响",
     "未实现", "L2/AP", "拓扑/故障", "可定位", "P2", "P2-后续", "待补丁", "后置"),
    ("OAM-06", "运维", "AP 上行遥测", "mt76/mac80211", "可选", "结构性影响",
     "未实现", "AP agent", "airtime/channel busy", "可读", "P1", "P1-L2", "待补丁", "方向是 STA→AP 上行"),
    ("OAM-07", "运维", "画质指标", "PSNR/SSIM/VMAF", "必需", "不受影响",
     "未开始", "同基线", "离线分析", "不低于 baseline", "P0", "P0-基线", "待验证", "六条素材都要"),

    # ---- TRIM ----
    ("TRIM-01", "裁剪", "DataChannel/SCTP", "RFC 8831/4960", "不需要", "直接移除",
     "不实现", "不实现", "无", "不验收", "P1", "裁剪", "待裁剪", "当前只有音视频"),
    ("TRIM-02", "裁剪", "simulcast/SVC", "WebRTC 扩展", "不需要", "直接移除",
     "不实现", "不实现", "无", "不验收", "P1", "裁剪", "待裁剪", "单流"),
    ("TRIM-03", "裁剪", "多方/SFU", "SFU 架构", "不需要", "直接移除",
     "不实现", "不实现", "无", "不验收", "P1", "裁剪", "待裁剪", "单 STA→AP"),
    ("TRIM-04", "裁剪", "浏览器 API", "W3C WebRTC", "不需要", "直接移除",
     "不实现", "不实现", "无", "不验收", "P1", "裁剪", "待裁剪", "AP 自定义接收"),
    ("TRIM-05", "裁剪", "AEC/AGC", "WebRTC 音频处理", "不需要", "不受影响",
     "不实现", "不实现", "无", "不验收", "P2", "裁剪", "待裁剪", "文件源/单向"),
    ("TRIM-06", "裁剪", "RED/音频冗余", "RFC 2198", "不需要", "不受影响",
     "不实现", "不实现", "无", "不验收", "P2", "裁剪", "待裁剪", "先 Opus PLC/FEC"),
]

# --- Baseline P0 checklist -------------------------------------------------
BASELINE = [
    ("BL-01", "预处理 1080p30_1 到 10 Mbps + Opus", "FFmpeg CBR/GOP/Opus", "时长/PTS/码率正确，可解", ""),
    ("BL-02", "GStreamer UDP 视频-only 跑通", "qtdemux→h264parse→rtph264pay→udpsink", "60 s 可解，无异常", ""),
    ("BL-03", "RTP 头/时间戳检查", "Wireshark + pcap", "PT/seq/SSRC/90 kHz 正确", ""),
    ("BL-04", "RTCP SR/RR 检查", "Wireshark + pcap", "SR/RR 字段正常", ""),
    ("BL-05", "SRTP 加解密", "srtpenc/srtpdec + 错误 key", "无明文，错误 key 失败", ""),
    ("BL-06", "抖动缓冲/乱序", "rtpjitterbuffer + 注入", "按 PTS 出队，无欠载", ""),
    ("BL-07", "Opus 音频 + A/V sync", "Opus 48 kHz + RTCP SR", "p95 ≤ 40 ms", ""),
    ("BL-08", "15/20 Mbps 码率", "同素材重编码", "可解，空口不丢", ""),
    ("BL-09", "0.1% 丢包 + NACK/PLI", "GStreamer rtpbin", "帧完整率≥95%", ""),
    ("BL-10", "24/25/30 fps 矩阵", "三条素材", "时间戳步长 3750/3600/3000", ""),
    ("BL-11", "10 min 长跑", "同 pipeline", "无崩溃/回绕错误", ""),
    ("BL-12", "baseline 指标冻结", "汇总 JSON/CSV + pcap", "可复现，作为 L2 对照", ""),
]

# --- Media-layer replacement acceptance (pre-baseline A/B) ----------------
AB_ROWS = [
    ("AB-00", "替换前实现确认", "待定义（名称/版本/能否在 Pi Linux 运行）", "GStreamer + UDP/IP",
     "同一 Pi/同一 Wi-Fi/同一接收机", "有可运行旧层才做真 A/B；没有则改为新层基线 + 独立交叉验证", ""),
    ("AB-01", "1080p30/10 Mbps 视频-only", "替换前媒体层（待确认实现）+ UDP/IP", "GStreamer + UDP/IP",
     "同素材/同目标码率/同 AP/同接收机；60 s", "两端均可解码，帧完整率≥99.9%，无异常", ""),
    ("AB-02", "15/20 Mbps 高码率", "替换前 + UDP/IP", "GStreamer + UDP/IP",
     "同素材/同 GOP/同码率", "可解码，空口不丢；新层不低于旧层", ""),
    ("AB-03", "Opus + A/V sync", "替换前音频路径", "GStreamer Opus + RTCP SR",
     "同素材/同音频时长", "A/V skew p95 ≤ 40 ms", ""),
    ("AB-04", "0.1% 丢包/突发丢包", "替换前 FEC/NACK/PLI", "GStreamer NACK/PLI/RTX/FEC",
     "同丢包模型/同注入点", "帧完整率≥95%，新层不低于旧层", ""),
    ("AB-05", "乱序/重复/迟到", "替换前 jitter buffer", "GStreamer rtpjitterbuffer",
     "同乱序/重复模型", "按 PTS 正确出队，无爆缓冲", ""),
    ("AB-06", "端到端时延/CPU", "替换前 sender/receiver", "GStreamer sender/receiver",
     "同机器/同素材/同码率", "时延不劣化超过 20%；CPU 可承受", ""),
    ("AB-07", "RTP/RTCP 标准性", "替换前原有媒体层格式（待确认）", "标准 RTP/RTCP/SRTP",
     "Wireshark + pcap", "可按 RFC 解析；新层为标准格式", ""),
    ("AB-08", "功能对齐", "替换前功能台账", "替换后功能台账",
     "逐项对照", "必需功能不缺；差异有记录", ""),
    ("AB-09", "10 min 长跑", "替换前", "GStreamer",
     "同码率/同链路", "无崩溃/无序号回绕错误", ""),
    ("AB-10", "替换验收冻结", "旧层数据归档", "新层配置冻结",
     "汇总 pcap/JSON/CSV", "新层作为后续 UDP baseline；旧层仅作对照", ""),
]


def style_header(ws, ncols):
    fill = PatternFill("solid", fgColor="1F4E78")
    font = Font(color="FFFFFF", bold=True, size=10)
    thin = Side(style="thin", color="B7C9E2")
    for c in range(1, ncols + 1):
        cell = ws.cell(row=1, column=c)
        cell.fill = fill
        cell.font = font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = Border(bottom=thin)


def style_body(ws, nrows, ncols, heights=34):
    thin = Side(style="thin", color="D9E2F3")
    for r in range(2, nrows + 1):
        ws.row_dimensions[r].height = heights
        for c in range(1, ncols + 1):
            cell = ws.cell(row=r, column=c)
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.border = Border(bottom=thin)


def add_table(ws, name, nrows, ncols):
    ref = f"A1:{chr(64 + ncols)}{nrows}"
    table = Table(displayName=name, ref=ref)
    table.tableStyleInfo = TableStyleInfo(
        name="TableStyleMedium2", showFirstColumn=False, showLastColumn=False,
        showRowStripes=True, showColumnStripes=False)
    ws.add_table(table)


wb = Workbook()
wb.properties.title = "RTC over MAC 媒体面功能台账"
wb.properties.creator = "DSH"
wb.properties.description = "1080p24/25/30, RTP/RTCP/SRTP over UDP baseline -> L2"

# ---------- 说明 ----------
ws = wb.active
ws.title = "说明"
ws.column_dimensions["A"].width = 24
ws.column_dimensions["B"].width = 112
ws["A1"] = "RTC over MAC 媒体面功能台账"
ws["A1"].font = Font(bold=True, size=16, color="1F4E78")
ws.merge_cells("A1:B1")
ws["A3"] = "版本"
ws["B3"] = "2026-11-09 / v1.0（初始化，未填实测结果）"
ws["A4"] = "适用范围"
ws["B4"] = "Pi 5 STA（MT7921AU）→ BPI-R4 AP → 有线参考接收端；1080p24/25/30 + Opus；RTP/RTCP/SRTP 媒体面；不做完整 WebRTC。"
ws["A5"] = "核心原则"
ws["B5"] = "先 UDP/IP baseline；同一套 RTP/RTCP/SRTP 代码换 L2 transport；差分测试；只补真正受影响的功能，只裁确认不需要的。"
ws["A6"] = "第一阶段重点"
ws["B6"] = "Phase 0.5 先做“替换前媒体层 vs GStreamer”UDP/IP 对比；新层验收通过后，才把新层 UDP 作为 L2 baseline。L2 行先看、不急着补。"
ws["A7"] = "替换前定义"
ws["B7"] = "必须先明确“替换前”的可运行实现。若 Pi 上没有旧层、也没有可安装的旧层，则不能伪造 before/after；改为 GStreamer UDP 基线 + 独立实现交叉验证。"
ws["A8"] = "字段说明"
ws["A8"].font = Font(bold=True, size=12, color="1F4E78")
notes = [
    ("场景需要", "必需 / 可选 / 不需要。可选=后续增强；不需要=裁剪候选。"),
    ("去掉UDP/IP影响", "不受影响 / 部分影响 / 结构性影响 / 直接移除 / 不适用。"),
    ("UDP基线实现", "GStreamer baseline 的当前状态；未开始/已规划/未实现等。"),
    ("L2目标实现/补丁", "换成 L2 后要做什么；不受影响的写“同基线”。"),
    ("优先级", "P0 必须；P1 重要；P2 后置。"),
    ("阶段", "P0-基线 / P1-L2 / P2-后续 / 裁剪。"),
    ("状态", "待验证 / 待补丁 / 待裁剪 / 不做 / 通过。初始全部未完成。"),
]
r = 9
for k, v in notes:
    ws.cell(row=r, column=1, value=k).font = Font(bold=True)
    ws.cell(row=r, column=2, value=v).alignment = Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[r].height = 34
    r += 1

counts = Counter(row[5] for row in ROWS)
needs = Counter(row[4] for row in ROWS)
prio = Counter(row[10] for row in ROWS)
phase = Counter(row[11] for row in ROWS)
status = Counter(row[12] for row in ROWS)
ws.cell(row=17, column=1, value="统计").font = Font(bold=True, size=12, color="1F4E78")
stats = [
    ("总条目", len(ROWS)),
    ("场景需要：必需", needs.get("必需", 0)),
    ("场景需要：可选", needs.get("可选", 0)),
    ("场景需要：不需要", needs.get("不需要", 0)),
    ("影响：不受影响", counts.get("不受影响", 0)),
    ("影响：部分影响", counts.get("部分影响", 0)),
    ("影响：结构性影响", counts.get("结构性影响", 0)),
    ("影响：直接移除", counts.get("直接移除", 0)),
    ("P0", prio.get("P0", 0)),
    ("P1", prio.get("P1", 0)),
    ("P2", prio.get("P2", 0)),
    ("P0-基线", phase.get("P0-基线", 0)),
    ("P1-L2", phase.get("P1-L2", 0)),
    ("P2-后续", phase.get("P2-后续", 0)),
    ("裁剪", phase.get("裁剪", 0)),
    ("待验证", status.get("待验证", 0)),
    ("待补丁", status.get("待补丁", 0)),
    ("待裁剪", status.get("待裁剪", 0)),
]
r = 18
for k, v in stats:
    ws.cell(row=r, column=1, value=k)
    ws.cell(row=r, column=2, value=v)
    r += 1

ws.freeze_panes = "A3"

# ---------- 功能台账 ----------
ws = wb.create_sheet("功能台账")
ws.append(HEADERS)
for row in ROWS:
    ws.append(row)
style_header(ws, len(HEADERS))
style_body(ws, len(ROWS) + 1, len(HEADERS), heights=42)
widths = [10, 10, 30, 30, 10, 16, 26, 28, 34, 36, 8, 12, 10, 30]
for i, w in enumerate(widths, 1):
    ws.column_dimensions[chr(64 + i)].width = w
ws.freeze_panes = "A2"
add_table(ws, "FeatureLedger", len(ROWS) + 1, len(HEADERS))

# Data validation
dv_need = DataValidation(type="list", formula1='"必需,可选,不需要"', allow_blank=True)
dv_impact = DataValidation(type="list", formula1='"不受影响,部分影响,结构性影响,直接移除,不适用"', allow_blank=True)
dv_prio = DataValidation(type="list", formula1='"P0,P1,P2"', allow_blank=True)
dv_phase = DataValidation(type="list", formula1='"P0-基线,P1-L2,P2-后续,裁剪"', allow_blank=True)
dv_status = DataValidation(type="list", formula1='"待验证,待补丁,待裁剪,不做,通过"', allow_blank=True)
for dv, col in ((dv_need, "E"), (dv_impact, "F"), (dv_prio, "K"), (dv_phase, "L"), (dv_status, "M")):
    ws.add_data_validation(dv)
    dv.add(f"{col}2:{col}{len(ROWS)+1}")

# Conditional formatting
red = PatternFill("solid", fgColor="F8CBAD")
orange = PatternFill("solid", fgColor="FFE699")
green = PatternFill("solid", fgColor="C6EFCE")
gray = PatternFill("solid", fgColor="D9D9D9")
yellow = PatternFill("solid", fgColor="FFF2CC")
ws.conditional_formatting.add(f"F2:F{len(ROWS)+1}", FormulaRule(formula=['$F2="结构性影响"'], fill=red))
ws.conditional_formatting.add(f"F2:F{len(ROWS)+1}", FormulaRule(formula=['$F2="部分影响"'], fill=orange))
ws.conditional_formatting.add(f"F2:F{len(ROWS)+1}", FormulaRule(formula=['$F2="不受影响"'], fill=green))
ws.conditional_formatting.add(f"F2:F{len(ROWS)+1}", FormulaRule(formula=['$F2="直接移除"'], fill=gray))
ws.conditional_formatting.add(f"M2:M{len(ROWS)+1}", FormulaRule(formula=['$M2="待补丁"'], fill=orange))
ws.conditional_formatting.add(f"M2:M{len(ROWS)+1}", FormulaRule(formula=['$M2="待验证"'], fill=yellow))
ws.conditional_formatting.add(f"M2:M{len(ROWS)+1}", FormulaRule(formula=['$M2="待裁剪"'], fill=gray))
ws.conditional_formatting.add(f"M2:M{len(ROWS)+1}", FormulaRule(formula=['$M2="通过"'], fill=green))

# ---------- Baseline P0 ----------
ws = wb.create_sheet("Baseline_P0")
base_headers = ["ID", "检查项", "方法/命令", "通过标准", "记录"]
ws.append(base_headers)
for row in BASELINE:
    ws.append(row)
style_header(ws, len(base_headers))
style_body(ws, len(BASELINE) + 1, len(base_headers), heights=40)
for i, w in enumerate([8, 38, 40, 40, 22], 1):
    ws.column_dimensions[chr(64 + i)].width = w
ws.freeze_panes = "A2"
add_table(ws, "BaselineP0", len(BASELINE) + 1, len(base_headers))

# ---------- 媒体层 A/B 验收 ----------
ws = wb.create_sheet("媒体层A_B")
ab_headers = ["ID", "对比项", "替换前（原媒体层，待定义）", "替换后（GStreamer）", "测试条件", "通过标准", "记录"]
ws.append(ab_headers)
for row in AB_ROWS:
    ws.append(row)
style_header(ws, len(ab_headers))
style_body(ws, len(AB_ROWS) + 1, len(ab_headers), heights=44)
for i, w in enumerate([8, 28, 30, 30, 34, 40, 22], 1):
    ws.column_dimensions[chr(64 + i)].width = w
ws.freeze_panes = "A2"
add_table(ws, "MediaLayerAB", len(AB_ROWS) + 1, len(ab_headers))

# ---------- 补丁清单 ----------
ws = wb.create_sheet("补丁清单")
patch_headers = ["ID", "功能/子功能", "影响", "L2目标实现/补丁", "验证方法", "优先级", "阶段", "状态"]
patch_rows = [row for row in ROWS if row[5] in ("部分影响", "结构性影响") and row[4] != "不需要"]
ws.append(patch_headers)
for row in patch_rows:
    ws.append([row[0], row[2], row[5], row[7], row[8], row[10], row[11], row[12]])
style_header(ws, len(patch_headers))
style_body(ws, len(patch_rows) + 1, len(patch_headers), heights=40)
for i, w in enumerate([10, 32, 14, 38, 36, 8, 12, 10], 1):
    ws.column_dimensions[chr(64 + i)].width = w
ws.freeze_panes = "A2"
add_table(ws, "PatchList", len(patch_rows) + 1, len(patch_headers))

# ---------- 裁剪候选 ----------
ws = wb.create_sheet("裁剪候选")
trim_headers = ["ID", "功能/子功能", "原因", "当前状态"]
trim_rows = [row for row in ROWS if row[4] == "不需要"]
ws.append(trim_headers)
for row in trim_rows:
    ws.append([row[0], row[2], row[13], row[12]])
style_header(ws, len(trim_headers))
style_body(ws, len(trim_rows) + 1, len(trim_headers), heights=34)
for i, w in enumerate([10, 34, 50, 10], 1):
    ws.column_dimensions[chr(64 + i)].width = w
ws.freeze_panes = "A2"
add_table(ws, "TrimList", len(trim_rows) + 1, len(trim_headers))

# ---------- 统计 ----------
ws = wb.create_sheet("统计")
ws["A1"] = "按功能域统计"
ws["A1"].font = Font(bold=True, size=12, color="1F4E78")
ws.append(["功能域", "条目数"])
domain_counts = Counter(row[1] for row in ROWS)
for k, v in sorted(domain_counts.items()):
    ws.append([k, v])
ws.append([])
ws.append(["影响", "条目数"])
for k in ["不受影响", "部分影响", "结构性影响", "直接移除", "不适用"]:
    ws.append([k, counts.get(k, 0)])
ws.append([])
ws.append(["阶段", "条目数"])
for k in ["P0-基线", "P1-L2", "P2-后续", "裁剪"]:
    ws.append([k, phase.get(k, 0)])
ws.append([])
ws.append(["状态", "条目数"])
for k in ["待验证", "待补丁", "待裁剪", "不做", "通过"]:
    ws.append([k, status.get(k, 0)])
ws.column_dimensions["A"].width = 24
ws.column_dimensions["B"].width = 12
for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=2):
    for cell in row:
        cell.alignment = Alignment(vertical="top")
# bold section headers
for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=2):
    if row[0].value in ("功能域", "影响", "阶段", "状态"):
        for cell in row:
            cell.font = Font(bold=True)

wb.save(OUT)
print("saved", OUT, "rows", len(ROWS), "patches", len(patch_rows), "trim", len(trim_rows))
