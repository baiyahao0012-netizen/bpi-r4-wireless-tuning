# BPI-R4 AI 业务加速与 RTC over WiFi 项目交付文档

版本：v1.0  
日期：2026-10-29  
项目仓库：https://github.com/baiyahao0012-netizen/bpi-r4-wireless-tuning

---

## 1. 项目概述

本项目基于 Banana Pi BPI-R4 2.5GE PoE 开发板，围绕两个方向开展工作：

### 方向 A：AI 业务加速

利用 OpenAppFilter（OAF）识别豆包业务，将 AppID 写入 conntrack mark，再通过 nft 设置 DSCP EF，使豆包流量进入 WiFi AC_VO，从而在拥塞时获得更高调度优先级。

### 方向 B：RTC over WiFi

去掉 IP/UDP，使用自定义 EtherType 0x88B5 在 802.11 L2 上传输 H.264 视频，验证边缘场景下自定义 RTC 协议栈的可行性。

---

## 2. 开发板与官方资料

### 2.1 开发板

- 型号：Banana Pi BPI-R4 2.5GE PoE
- 主控：MediaTek MT7988A
- 内存：4 GB
- 无线网卡：MediaTek MT7996（WiFi 7，BE14）
- 存储：SD 卡 / eMMC
- 本项目当前从 SD 卡启动 OpenWrt

官方产品页：

- https://banana-pi.org/web/index.php?topclassid=19&classid=83&id=539&lanstr=en&wap=1

官方 Wiki：

- https://wiki.banana-pi.org/Getting_Started_with_BPI-R4

OpenWrt 设备页：

- https://openwrt.org/inbox/toh/sinovoip/bananapi_bpi-r4

### 2.2 软件版本

- OpenWrt 24.10.0
- Revision：r28427-6df0e3d02a
- Linux：6.6.73
- 架构：aarch64_cortex-a53
- 目标：mediatek/filogic

### 2.3 参考项目

- OAF：OpenAppFilter
- SparkRTC：https://github.com/hkust-spark/sparkrtc
- ADBKeyboard：https://github.com/senzhk/ADBKeyBoard

---

## 3. 当前网络拓扑

    手机 Redmi K60（豆包 com.larus.nova）
      → BPI-R4-5G AP
      → 192.168.240.219

    PC WLAN3
      → BPI-R4-5G
      → 192.168.240.126

    PC 自带 WLAN
      → BPI-R4-5G
      → 192.168.240.147

    BPI-R4 管理
      → 以太网
      → PC 192.168.240.2 / 板子 192.168.240.1

    BPI-R4 WAN
      → phy0.0-sta0
      → DianGroup103

### 3.1 关键说明

- 手机必须连接 BPI-R4-5G，豆包流量才会经过板子；
- 手机开热点 Bai 时，板子作为 Bai 的客户端，手机自身豆包流量不会经过 BPI-R4；
- 测试手机 AI 业务时，板子 WAN 必须走其他上游（当前为 DianGroup103）；
- wifi-failover 测试期间已停止，避免 WAN 切回 Bai；
- 当前 5G AP：HE80 / ch149；
- 当前默认输入法：百度。

### 3.2 网络配置

    BPI-R4-5G：WPA2，密码 12345678
    BPI-R4（2.4G）：WPA2，密码 12345678
    DianGroup103：密码 DianGroup2002
    Bai：手机热点，密码 12345678

注意：以上包含现场密码，交付文档不要公开上传到公共仓库。

---

## 4. 已完成模块与准备情况

| 模块 | 状态 | 说明 |
|---|---|---|
| BPI-R4 OpenWrt | 完成 | 24.10.0 / 6.6.73 |
| 5G/2.4G AP | 完成 | phy0.1-ap0 / phy0.0-ap0 |
| 板子 STA 上网 | 完成 | Bai / DianGroup103 |
| 主备 WiFi 切换 | 完成 | Bai 优先，DianGroup103 兜底 |
| OAF 内核模块 | 完成 | oaf.ko + 最小 netlink loader |
| 豆包 AppID 1900 | 完成 | doubao.com |
| 手机豆包识别 | 完成 | conntrack mark=1900 |
| nft EF / AC_VO | 完成 | 规则已可自动/手动安装 |
| oaf-auto 自动开关 | 完成 | AI 字节增量检测，ON/OFF |
| ADB 控制手机 | 完成 | 点击/输入/发送/截图 |
| 中文注入 | 完成 | ADBKeyboard，测试后恢复百度 |
| 英文/中文复杂题 | 完成 | 已发送并收到回答 |
| TTFT 自动采集 | 未完成 | uiautomator 流式 idle 失败 |
| VLM/OCR 准确率 | 未测试 | 需要 VLM pipeline |
| RTC over WiFi 视频 | 完成 | 0x88B5 / H.264 / FEC / NACK |
| 手机/浏览器 raw L2 | 不支持 | 无 raw socket 权限 |
| 备份与回退 | 完成 | 固件/模块/config/U-Boot |

---

## 5. OAF 加速实现

### 5.1 原理

    豆包 DNS/SNI
      → OAF 识别
      → conntrack mark 低 16 位 = 1900
      → nft postrouting 匹配 mark=1900
      → ip dscp set ef
      → mac80211 AC_VO
      → WMM 优先调度

### 5.2 板端文件

    /root/oaf.ko
    /root/oaf_load
    /root/oaf_feature_plain.txt
    /root/oaf_start.sh
    /root/oaf_accel.sh
    /root/oaf_demo.sh
    /root/oaf_auto.sh

### 5.3 常用命令

    # 加载 OAF + 加速
    /root/oaf_demo.sh start

    # 查看状态
    /root/oaf_demo.sh status

    # 手动开/关加速
    /root/oaf_accel.sh install 1900 ef
    /root/oaf_accel.sh remove

    # 停止自动 watcher
    pkill -f oaf_auto

    # 查看手机豆包识别
    grep '192.168.240.219' /proc/net/nf_conntrack | grep mark=1900

    # 查看 nft 计数
    nft -a list table ip oaf_accel

### 5.4 oaf-auto

功能：

- 检测手机 mark=1900 的 conntrack 字节增量；
- 有增长：自动安装 EF 规则；
- 20 秒无增长：自动移除规则；
- 避免空闲 TCP 连接导致永久 ON。

日志示例：

    oaf-auto: AI bytes=919904 flows=7 -> accel ON
    oaf-auto: AI idle 20 s (bytes=7689 flows=1) -> accel OFF
    oaf-auto: AI bytes=292207 flows=4 -> accel ON

注意：

- 手机 IP 硬编码为 192.168.240.219；
- 切换 2.4G 后 IP 变为 192.168.240.236，需要修改脚本；
- 多次 start-stop-daemon 会产生多个 watcher，测试前执行 pkill -f oaf_auto。

---

## 6. 手机 ADB 控制

### 6.1 PC 端 ADB

    _work_recover/platform-tools/platform-tools/adb.exe

检查：

    adb devices

应显示：

    109be14a    device

### 6.2 输入法

- 默认输入法：百度
- 中文注入：ADBKeyboard
- 测试结束后已恢复百度：

    adb shell ime set com.baidu.input_mi/.ImeService

### 6.3 已实现

- 打开豆包；
- 点击输入框；
- 英文通过 input text；
- 中文通过 ADBKeyboard 广播；
- 点击发送；
- 截图/UI dump；
- 复杂题已收到回答。

### 6.4 已知问题

- uiautomator dump 在流式输出时报：

    ERROR: could not get idle state

- 因此不能可靠轮询首字；
- 固定坐标会误触打电话/展开编辑器；
- 建议改用 screencap + 像素差/OCR 测 TTFT。

---

## 7. 测试结果

### 7.1 手机豆包识别

    src=192.168.240.219 ... mark=1900
    mark=1900 连接数：6–14

nft：

    ct mark & 0xffff == 0x76c counter ... ip dscp set ef

### 7.2 1.1× 极限打流 A/B

| 指标 | 基线 | 加速 |
|---|---|---|
| WLAN3 | 255 Mbit/s | 258 Mbit/s |
| 自带 WLAN | 24.5 Mbit/s | 24.6 Mbit/s |
| 合计 | 279.5 Mbit/s | 282.6 Mbit/s |
| TTFB p50 | 0.687 s | 0.732 s |
| TTFB p95 | 0.929 s | 0.881 s |
| nft 规则 | 无 | 有 |
| EF 包 | 5 | 132 |

结论：机制生效；该轮体验无明显收益。

### 7.3 另一次强拥塞 A/B

    基线：622 Mbit/s，TTFB p50 0.744 s，p95 1.845 s
    加速：577 Mbit/s，TTFB p50 0.543 s，p95 1.547 s
    手机 TCP RTT p50：58.17 → 40.98 ms
    EF 包：0 → 86

结论：

- 出现 TTFB p50 −27%、手机 RTT p50 −30% 的正向信号；
- 但样本少、App 操作不一致；
- 不能作为最终 30% 验收证据。

### 7.4 严重拥塞验证

2.4G + 双网卡 UDP：

    手机 ping AP：20 个包丢 4 个，20% 丢包
    RTT avg 108.6 ms，max 444.9 ms

说明可以制造严重拥塞。

### 7.5 RTC over WiFi

已验证：

- 自定义 EtherType 0x88B5；
- H.264 视频；
- 实时 90 帧 / 3.005 s；
- 双向 ACK；
- 两 STA AP bridge；
- FEC 丢 1 块恢复；
- NACK 丢块重传；
- SHA256 一致。

限制：

- 只能 Linux/OpenWrt 专用端点；
- 手机/浏览器不能直接参与；
- 标准 WebRTC/ICE 不兼容。

详细报告：

    _work_final/rtc_over_wifi/implementation_report.md

---

## 8. WiFi 主备切换

功能：

- 有 Bai：连接 Bai；
- 无 Bai：连接 DianGroup103；
- 在 DianGroup103 时检测到 Bai：自动切回。

板端文件：

    /root/wifi_failover.sh
    /etc/init.d/wifi-failover
    /etc/rc.d/S99wifi-failover

状态：

    /etc/init.d/wifi-failover start
    /etc/init.d/wifi-failover stop
    /etc/init.d/wifi-failover disable

注意：

- 切换使用 wifi reload，会短暂重启 WiFi；
- 测试手机 AI 时建议 stop，避免 WAN 切回 Bai；
- 现场实测 DianGroup103 可上网；
- 自动切回 Bai 已验证。

---

## 9. 备份与回退

备份文件：

    _work_recover/backups/backup_sem_20261029.tar.gz
    SHA256: 8C6992D2A1C1E05E9FFE80629AEA182867B630A66932A6E60BD73E0FEBF31484

内容：

- /etc/config
- /lib/firmware/mediatek/mt7996
- /lib/modules/6.6.73/mt76*.ko
- /root 脚本
- U-Boot 环境
- sysupgrade 配置备份

回退：

    tar xzf backup_sem.tar.gz -C /tmp
    cp -a /tmp/backup_sem/mt7996/* /lib/firmware/mediatek/mt7996/
    cp -a /tmp/backup_sem/modules/mt76*.ko* /lib/modules/6.6.73/
    cp -a /tmp/backup_sem/config/* /etc/config/
    reboot

极端情况用 SD 卡/串口恢复。

---

## 10. 关键文件清单

### OAF

    _work_final/oaf_accel/
      oaf_accel.sh
      oaf_auto.sh
      oaf_demo.sh
      oaf_start.sh
      oaf.ko
      oaf_load
      feature_plain.txt
      phone_ab_metrics.md
      pc_he40_ab.md
      real_doubao_ab.md
      doubao_base.pcap
      doubao_accel.pcap

### RTC

    _work_final/rtc_over_wifi/
      implementation_report.md
      full_test_results.md
      real_world_test.md
      comparison_results.md
      matrix_raw.csv
      videos/
      src/

### 切换

    _work_final/bai_failover/
      wifi_failover.sh
      wifi-failover.init
      README.md

### 备份/工具

    _work_recover/backups/backup_sem_20261029.tar.gz
    _work_recover/platform-tools/
    _work_recover/ADBKeyboard.apk

---

## 11. 当前阻塞与下一步

### 11.1 TTFT

阻塞：

    uiautomator dump: could not get idle state

下一步：

    adb screencap 每 300–500 ms
    → 回答区域像素差 / OCR
    → 第一帧出现文字 = TTFT

或 UiAutomator instrumentation。

### 11.2 5 题 A/B

计划：

1. 5 个固定复杂题；
2. 每题等回答结束；
3. 基线组完成；
4. 用户新开对话；
5. 加速组同样 5 题；
6. 统计 TTFT p50/p95、卡顿、RTT、EF。

### 11.3 VLM/OCR

需要：

- 固定书页/文本；
- OCR/VLM pipeline；
- 准确率 ground truth；
- 基线/加速对比。

### 11.4 恢复现场

测试结束后：

- 恢复 5G HE80；
- 手机/PC 回 5G；
- 输入法回百度；
- 停 oaf-auto 或只保留一个；
- 视需求恢复 wifi-failover。

---

## 12. PC 端 EDCA/AC_VO 验证补充

在 PC 同一 STA、同一 AP、同一背景流下，把 5G AP 临时改为 HE40：

| 指标 | 基线 | 加速 | 变化 |
|---|---|---|---|
| 背景总吞吐 | 274 Mbit/s | 265 Mbit/s | 基本不变 |
| TTFB p50 | 0.649 s | 0.257 s | −60.3% |
| TTFB p95 | 1.032 s | 0.426 s | −58.7% |

结论：

- 强拥塞下，豆包 DSCP EF → AC_VO 的优先级调度有效；
- 总吞吐基本不变，符合“优先级不增加总带宽”的预期；
- 这是“AC_VO 优先级调度”效果，不是“每帧 CW/AIFS 参数调优”；
- HE80 高容量、400 Mbit/s 背景流下无明显收益。

对应文档：

    _work_final/oaf_accel/pc_he40_ab.md

---

## 13. 结论

当前项目已完成：

- 开发板 OpenWrt 环境；
- OAF 豆包识别；
- nft EF / AC_VO；
- 自动 ON/OFF；
- ADB 控制手机；
- 中英文复杂题发送；
- WiFi 主备切换；
- RTC over WiFi 视频；
- 备份与回退。

尚未完成：

- 可靠的 TTFT 自动采集；
- 5 题严格 A/B；
- VLM/OCR 准确率验证；
- 30% 卡顿/80% 准确率的最终验收。

结论：机制已经跑通，强拥塞下出现正向信号，但最终验收数据还需要补齐。
