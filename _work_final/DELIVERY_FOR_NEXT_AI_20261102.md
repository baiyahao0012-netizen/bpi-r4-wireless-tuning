# BPI-R4 项目交付与交接文档（给下一个 AI）

日期：2026-11-02  
仓库：https://github.com/baiyahao0012-netizen/bpi-r4-wireless-tuning  
适用：接手 OAF / EDCA / 网页 A-B / RTC over WiFi 的 AI 或工程师

---

## 0. 一句话交接

项目有两条线：

1. AI 业务识别与 EDCA 加速：OAF 识别豆包，写 conntrack mark=1900，再把 AI 流量映射到 BK；B 组把 BK 调成 CWmin=1、CWmax=1、AIFS=2。
2. RTC over WiFi：去掉 IP/UDP，用自定义 EtherType 0x88B5 在 802.11 L2 传 H.264。

当前未完成：

    A 组网页测试有 32 行，B 组只有 4 行，B 组被中断；
    TTFB 采集有时抓到非回答 API，出现 3–5 ms 假值；
    因此现有 CSV 不能直接作为最终验收结论。

---

## 1. 设备清单

| 设备 | 型号/标识 | 作用 |
|---|---|---|
| 开发板 | Banana Pi BPI-R4 2.5GE PoE，MT7988A，4 GB | AP/路由/OAF/EDCA/抓包 |
| 无线网卡 | MediaTek MT7996，BPI-R4-NIC-BE14 | 5G/2.4G AP |
| 手机 | Redmi K60，23013RK75C，Android 15 | 豆包 App 最终验证 |
| 手机 WiFi MAC | 06:65:45:fc:44:3d | 识别/关联 |
| PC | Windows，Python 3.10/3.12 | 浏览器/打流/ADB/录屏 |
| PC WLAN3 | MediaTek USB WiFi，90:de:80:1c:6a:7a | 连 BPI AP |
| PC 内置 WLAN | Realtek 8852CE，c0:35:32:19:cc:fb | 连 BPI AP/第二路打流 |
| PC 以太网 | 192.168.240.2 | 管理板子 |
| USB-TTL | 3.3V，115200 8N1 | 串口救援 |

官方资料：

- 产品页：https://banana-pi.org/web/index.php?topclassid=19&classid=83&id=539&lanstr=en&wap=1
- Wiki：https://wiki.banana-pi.org/Getting_Started_with_BPI-R4
- OpenWrt：https://openwrt.org/inbox/toh/sinovoip/bananapi_bpi-r4

软件：

    OpenWrt 24.10.0
    Revision r28427-6df0e3d02a
    Linux 6.6.73
    target mediatek/filogic
    aarch64_cortex-a53

---

## 2. 网络拓扑与地址

    手机 Redmi K60
      → BPI-R4-5G
      → 192.168.240.219

    PC WLAN3
      → BPI-R4-5G
      → 192.168.240.126

    PC 内置 WLAN
      → BPI-R4-5G
      → 192.168.240.147

    PC 以太网
      → 192.168.240.2 → 板子 192.168.240.1

    BPI-R4 WAN
      → phy0.0-sta0 → Bai 或 DianGroup103

AP：

    5G：phy0.1-ap0，SSID BPI-R4-5G，密码 12345678
    2.4G：phy0.0-ap0，SSID BPI-R4，密码 12345678
    最近测试：ch149，HE20

上游：

    Bai：密码 12345678
    DianGroup103：密码 DianGroup2002

注意：

- 手机开热点 Bai 时，板子是 Bai 的客户端，手机自己的豆包流量不经过 BPI-R4；
- 测手机 AI 时，板子 WAN 要走另一个上游；
- 测 PC 网页时，只要 PC 连 BPI-R4-5G 即可；
- 文档含现场密码，不要公开上传。

---

## 3. 如何连接和控制开发板

SSH：

    ssh root@192.168.240.1

root 空密码或 key。板子没有 sftp-server，传文件用：

    scp -O file root@192.168.240.1:/root/

串口：

    USB-TTL 3.3V
    GND-GND，TX/RX 交叉
    115200 8N1
    上电看 U-Boot/内核日志

常用：

    uname -a
    cat /etc/openwrt_release
    iw dev
    iw dev phy0.1-ap0 info
    iw dev phy0.1-ap0 station dump
    uci show wireless
    wifi reload

重启 WiFi 会短暂断连。

备份：

    /etc/config/wireless
    /root/wireless.web.bak
    /root/hostapd-phy0.1.conf.bak
    _work_recover/backups/backup_sem_20261029.tar.gz
    SHA256 8C6992D2A1C1E05E9FFE80629AEA182867B630A66932A6E60BD73E0FEBF31484

---

## 4. PC 和手机控制

ADB：

    _work_recover/platform-tools/platform-tools/adb.exe

检查：

    adb devices

应出现：

    109be14a    device

常用：

    adb shell cmd wifi status
    adb shell cmd wifi connect-network "BPI-R4-5G" wpa2 12345678
    adb shell input tap X Y
    adb shell input text "ASCII only"
    adb shell screencap -p /sdcard/x.png
    adb pull /sdcard/x.png .

中文：

    adb shell am broadcast -a ADB_INPUT_B64 --es msg <base64>

测完恢复百度：

    adb shell ime set com.baidu.input_mi/.ImeService

网页自动化：

    独立 profile：C:\Temp\chrome_test_profile
    端口：127.0.0.1:9222
    启动：chrome.exe --remote-debugging-port=9222 --user-data-dir=C:\Temp\chrome_test_profile --new-window https://www.doubao.com/

不要直接杀用户当前 Chrome 主窗口；用独立 profile。

打流：

    killall iperf3
    iperf3 -s -p 5201 -D
    iperf3 -s -p 5202 -D

PC：

    iperf3 -c 192.168.240.1 -B 192.168.240.126 -p 5201 -u -b 0 -P 8 -t 600 -i 30
    iperf3 -c 192.168.240.1 -B 192.168.240.147 -p 5202 -u -b 0 -P 8 -t 600 -i 30

注意：

- iperf3 -i 最大 60，写 300 会失败；
- server 会 busy/stale，测试前 killall 重启；
- ping 192.168.240.1 可能是 0 ms，要 ping 223.5.5.5 判断拥塞；
- -b 0 无限速率，-b 300M 定速。

录屏：

    python -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"

    ffmpeg -f gdigrab -framerate 10 -i desktop -t 1800 -c:v libx264 -preset ultrafast -pix_fmt yuv420p -y out.mp4

已有：

    _work_recover/recordings/web_ab_full.mp4  183 MB，A 组
    _work_recover/recordings/web_B_full.mp4    63 MB，B 组中断

## 5. 方向 A：OAF AI 业务识别与 EDCA 加速

### 5.1 定义

    豆包流量
      → OAF 识别 doubao.com
      → conntrack mark 低 16 位 = 1900（0x76c）
      → nft 设置 DSCP
      → WiFi AC

历史实现：

    mark=1900 → DSCP EF → AC_VO

当前项目要求：

    A 组：不做任何改动，默认 WMM
    B 组：AI → BK
          BK CWmin=1 / CWmax=1 / AIFS=2

不要再说 B 组是 AI→VO。

### 5.2 板端 OAF 文件

    /root/oaf.ko
    /root/oaf_load
    /root/oaf_feature_plain.txt
    /root/oaf_accel.sh
    /root/oaf_demo.sh
    /root/oaf_auto.sh

检查：

    lsmod | grep oaf
    grep '192.168.240.219' /proc/net/nf_conntrack | grep mark=1900
    grep '192.168.240.126' /proc/net/nf_conntrack | grep mark=1900

### 5.3 B 组 nft 规则（CS1→BK）

    nft add table ip oaf_bk
    nft add chain ip oaf_bk post '{ type filter hook postrouting priority mangle; }'
    nft add rule ip oaf_bk post ct mark and 0xffff == 1900 ip dscp set cs1

检查：

    nft list table ip oaf_bk

注意：

- CS1 映射 BK；
- EF 映射 VO；
- 不要同时保留旧 oaf_accel EF 规则；
- 规则重启不保存。

### 5.4 B 组 BK EDCA 参数

UCI 的 wmm_ac_bk_* 在本板 hostapd 生成配置里没有生效。  
当前是直接改运行配置：

    /var/run/hostapd-phy0.1.conf

追加：

    wmm_ac_bk_cwmin=1
    wmm_ac_bk_cwmax=1
    wmm_ac_bk_aifsn=2
    wmm_ac_bk_txoplimit=0

reload：

    ubus call hostapd.phy0.1-ap0 reload

会短暂断连，PC 自动重连。

检查：

    grep -n 'wmm_ac_bk' /var/run/hostapd-phy0.1.conf

恢复 A 组：

    sed -i '/^wmm_ac_bk_/d' /var/run/hostapd-phy0.1.conf
    ubus call hostapd.phy0.1-ap0 reload

重要：

- 运行时配置，wifi reload 可能重新生成并丢掉；
- 每次 A/B 切换后必须重新检查；
- 不要只说“配置了”，要看实际文件/reload。

### 5.5 已有测试数据

A 组：

    _work_recover/web_A.csv
    32 行，4 轮 × 8 题

B 组：

    _work_recover/web_B.csv
    4 行，第 4 题时被中断

B pilot：

    _work_recover/web_B_pilot.csv
    1 行

结论：

    A 组可作参考，但测试中 UDP 打流曾中断/重启，不能当严格受控数据；
    B 组不足 32 行，不能做 A/B 结论。

TTFB 质量问题：

    web_ab.py 取第一个匹配 /im/、/alice/、/samantha/ 的响应，
    有时抓到 conversation/info、office/skills 等非回答 API，
    出现 3–5 ms 假值。

下一个 AI 必须修正：

- 只取真正 AI 回答请求/流；
- 记录 URL、responseStart、requestStart；
- 排除 /conversation、/office、/commerce、/user；
- 或用 CDP 流式响应/SSE 事件。

TTFT：

    用 DOM MutationObserver 首次新增回答文本；
    比 uiautomator 稳，但需确认选择器和回答开始判定。

### 5.6 网页 A/B 脚本

    _work_recover/web_ab.py

用法：

    python _work_recover/web_ab.py A 32 _work_recover/web_A.csv
    python _work_recover/web_ab.py B 32 _work_recover/web_B.csv

脚本行为：

- 连接 127.0.0.1:9222；
- 每轮 goto 豆包 chat；
- 填 contenteditable；
- MutationObserver 测 TTFT；
- 监听 response 测 TTFB；
- 每题后 sleep 6 s；
- 立即写 CSV。

当前 B 组被 kill，需要重跑。

---

## 6. 方向 B：RTC over WiFi

完整文档：

    _work_final/rtc_over_wifi/RTC_OVER_WIFI_DELIVERY.md

结论：

- 自定义 EtherType 0x88B5；
- H.264；
- 5G/2.4G 实测；
- 实时 30 fps；
- FEC/NACK；
- AP bridge 两 STA；
- 手机/浏览器不能直接参与；
- 标准 WebRTC 不能互通；
- 跨 AP/公网不可行。

关键原始数据：

    最小视频：64 chunks，0 丢，76456 B，90 帧
    实时：90 帧，97 chunks，3005 ms，0 丢，69414 B
    摄像头 5G：5754 chunks，0 丢，6.58 MB，181 帧
    2.4G：4979 chunks，25 丢，5.65 MB，181 帧
    FEC：丢 1 块恢复，SHA256 一致
    NACK：丢 seq5 重传，SHA256 一致
    UDP/IP：18 次，UDP 161–164 帧，RT-L2 5G 181/181

关键文件：

    _work_final/rtc_over_wifi/
      l2video_send_rt.c
      l2video_recv_rt.py
      l2fec_send.c
      l2fec_recv.py
      l2nack_send.c
      l2nack_recv.py
      l2send.c
      l2recv.c
      live_cam_send.py
      live_cam_recv.py
      matrix_raw.csv

---

## 7. 其他已完成模块

### 7.1 EDCA / A-MPDU / MCS / WDRR

仓库根目录：

    PROJECT_MANIFEST.md
    README.md
    _work_final/BPI-R4_EDCA_AMPDU_MCS_WDRR_实测报告.docx
    _work_final/modules/

要点：

- EDCA 可免重载实时下发；
- A-MPDU agg_win_cap 可实时改，cap=2 吞吐约 −50%；
- MCS 标准 iw 对 AP 下行不生效；
- WDRR 补丁跑通，但 fq 层 per-AC 加权架构性无效；
- VIP 2:1/4:1 用 nft per-STA 配额。

这些是另一条线，不要和当前 BK 方案混。

### 7.2 WiFi 主备切换

    _work_final/bai_failover/wifi_failover.sh
    _work_final/bai_failover/wifi-failover.init

功能：

- 有 Bai 连 Bai；
- 没有 Bai 连 DianGroup103；
- 检测到 Bai 自动切回。

测 AI 时建议：

    /etc/init.d/wifi-failover stop

避免 WAN 切回 Bai 后手机豆包不经过测试上游。

### 7.3 备份

    _work_recover/backups/backup_sem_20261029.tar.gz
    SHA256 8C6992D2A1C1E05E9FFE80629AEA182867B630A66932A6E60BD73E0FEBF31484

---

## 8. 仓库文件地图

    README.md
    PROJECT_MANIFEST.md
    _work_final/
      PROJECT_DELIVERY.md
      PROJECT_DELIVERY_V2.md
      OAF_BUSINESS_ACCELERATION_STATUS.md
      OAF_EDCA_AUTOTUNING_PROPOSAL.md
      oaf_accel/
      rtc_over_wifi/
      bai_failover/
      modules/
      vip_ratio.sh
    _work_recover/
      platform-tools/
      web_ab.py
      web_A.csv
      web_B.csv
      web_B_pilot.csv
      recordings/
      backups/
    _work_timeline/
    _work_v3/
    _build/

注意：

- 仓库里有很多未跟踪的 PPT/课题/临时报告，不要误当交付物；
- 以 README/PROJECT_MANIFEST/本文件为准；
- _work_recover 下含原始数据和录屏，体积大，不要随意提交 Git。

---

## 9. 当前状态与已知问题

已完成：

- BPI-R4 OpenWrt；
- 5G/2.4G AP；
- OAF 识别豆包 mark=1900；
- CS1/BK nft 规则；
- hostapd BK CW=1/AIFS=2 运行时配置；
- 网页 Chrome CDP 登录和自动化；
- A 组 32 行；
- A 组录屏；
- RTC over WiFi；
- 备份/回退。

未完成：

- B 组 32 行；
- A/B 受控 UDP 全程不断；
- TTFB 正确 AI API；
- TTFT 最终校验；
- 4×8 × 2 统计结论；
- 手机端最终确认。

已知坑：

1. wmm_ac_bk_* 写 UCI 不生效，必须直接改 hostapd 运行配置并 reload。
2. wifi reload 可能覆盖运行配置。
3. OAF 规则重启丢失。
4. iperf3 server 会 stale/busy，必须 killall 重启。
5. iperf3 -i 最大 60，写 300 会失败。
6. ping AP 可能 0 ms，要 ping 外网判断拥塞。
7. B 组脚本被 kill，CSV 只有 4 行，不可当结论。
8. TTFB 取到非回答 API，出现 3–5 ms 假值。
9. 手机 ADB 常掉线；网页测试不需要手机。
10. 当前 Chrome 主窗口不能随便杀，CDP 用独立 profile。

---

## 10. 下一个 AI 的执行顺序

第一步：恢复环境

    ssh root@192.168.240.1
    iw dev phy0.1-ap0 info
    grep wmm_ac_bk /var/run/hostapd-phy0.1.conf
    nft list table ip oaf_bk

PC：

    ping 192.168.240.1
    ping 223.5.5.5

第二步：A 组

    sed -i '/^wmm_ac_bk_/d' /var/run/hostapd-phy0.1.conf
    ubus call hostapd.phy0.1-ap0 reload
    nft delete table ip oaf_bk

第三步：B 组

    追加 wmm_ac_bk_*，reload
    nft add table/chain/rule CS1
    grep mark=1900

第四步：打流

    killall iperf3
    iperf3 -s -p 5201 -D
    iperf3 -s -p 5202 -D
    PC 两路 UDP -b 0 -P 8
    ping 223.5.5.5 确认 100+ ms 或丢包

第五步：修 TTFB

- 只匹配 AI 回答 API；
- 记录 URL；
- 排除 conversation/office/commerce/user；
- 用 CDP/SSE 或 PerformanceResourceTiming；
- 先跑 1 题验证 TTFB 不是 3 ms。

第六步：重跑

    python _work_recover/web_ab.py A 32 _work_recover/web_A2.csv
    python _work_recover/web_ab.py B 32 _work_recover/web_B2.csv

全程录屏；每 8 题检查 UDP 是否仍在跑。

第七步：分析

- TTFB p50/p95；
- TTFT p50/p95；
- 失败/空值；
- UDP 是否全程；
- 背景吞吐；
- 新 CSV/报告。

---

## 11. 结论

项目不是只把 AI 映射到 VO，而是：

    AI 业务 → BK
    BK 被配置为 CW=1/AIFS=2 的激进通道

当前已完成机制、脚本、网页自动化、A 组数据、RTC；  
缺少 B 组完整数据、正确 TTFB、全程 UDP 受控。

下一个 AI 先按第 10 节恢复环境，不要直接相信现有 web_A.csv/web_B.csv 的数值。

