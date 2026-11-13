# 10 只读侦察命令与走无线硬证据

所有命令都是**只读**，不改配置、不发包压测。用于每次发流前后核对状态、归因问题。

---

## 一、SSH 登录

```powershell
# Pi（用户 bai，密钥免密；其他用户名会被拒）
C:\Windows\System32\OpenSSH\ssh.exe -i C:\Users\15732\.ssh\id_ed25519_pi_rtc bai@192.168.240.153

# AP（OpenWrt，root 免密）
C:\Windows\System32\OpenSSH\ssh.exe -o BatchMode=yes root@192.168.240.1
```

> AP 是 busybox：没有 `nohup/setsid/pkill`；`ip` 无 `-br`；`netstat -ulnp` 可用；
> bash 循环会吞变量，**一次只发一条命令**。

---

## 二、Pi 侧接口与路由核查

### 2.1 看接口 / 地址

```bash
ip -br link          # 链路层：网卡名、MAC、UP/DOWN
ip -br addr          # 各接口 IP
```

要点：
- `eth0` = 管理口 `.153`；`wlan1` = 媒体口 `.126`（MT7921AU）；`wlan0` 保持 DOWN；
- 不应存在残留的 netns / macvlan：`ip netns list` 应为空，`ip link show type macvlan` 无输出。

### 2.2 看路由出口（最关键的一条）

```bash
ip route get 192.168.240.1 from 192.168.240.126
```

- **判据**：结果必须是 `dev wlan1`；若是 `dev eth0`，媒体走了有线，测试作废；
- 这就是 06 号脚本护栏检查的同一条命令；
- 修复见 07 号脚本（策略路由）或独立子网方案。

### 2.3 看接口计数器（归因必须用增量，不能用累计值）

```bash
ip -s link show eth0
ip -s link show wlan1
```

记录发流**前**的 TX bytes/packets，发流 10 秒后再记一次，相减得增量：
- `eth0` TX 增量 ≈ 0；
- `wlan1` TX 增量 ≈ 码率 × 时长（20 Mbps × 10 s ≈ 25 MB 量级，含 RTP/链路开销）。

> 计数器是开机累计值，单次快照分不清哪轮走了哪条线；必须前后差值对比。

### 2.4 无线关联状态

```bash
iw dev wlan1 link
```

看 SSID、信道、信号、RX/TX 速率。MT7921AU 个别驱动不暴露 `link` 详情，缺失时以 AP 侧 `station dump` 为准。

---

## 三、AP 侧证据

### 3.1 站点统计（最硬的证据，无法伪造）

```bash
iw dev phy0.1-ap0 station dump
```

按 STA MAC `90:de:80:1c:6a:7a` 查看：

| 字段 | 含义 | 判读 |
|---|---|---|
| `rx bytes` / `rx packets` | AP 从该 STA 收到的字节/包数 | 发流前后增量应对上 Pi `wlan1` TX 增量 |
| `tx bytes` / `tx packets` | AP 回发给 STA 的量（RTCP RR/NACK 等） | 反馈通道是否活的线索 |
| `tx retries` | 重传次数 | 空口质量指标；持续上涨说明干扰/弱信号 |
| `signal` | 信号强度 dBm | -48 dBm 属良好 |

### 3.2 抓包（方向证据，不能直接算丢包率）

```bash
# 绑无线接口 phy0.1-ap0，不要绑 br-lan；udp port 5004 是视频 RTP
tcpdump -i phy0.1-ap0 udp port 5004 -w ap_rtp.pcap
```

要点：
- A-MSDU 聚合后，一个抓包记录可能装多个 RTP 包，**序号会跳变**；
- 所以这份 pcap 只能证明"包到过无线口、方向是 STA→AP"；
- 丢包率/帧完整率要靠 03 号脚本重建 H.264 后数帧。

### 3.3 看 AP 上有没有接收进程在跑

```bash
netstat -ulnp | grep 5004
```

- 有 `gst-launch-1.0` 监听 5004 = 接收端在跑；
- 当前历史进程是 `udpsrc port=5004 ! fakesink`，只听不存，不算完整接收。

### 3.4 看 AP 上 GStreamer 有哪些元件

```bash
gst-inspect-1.0 | grep -E 'udpsrc|rtpjitterbuffer|rtph264depay|rtpopusdepay|filesink|h264parse|avdec_h264'
```

AP（1.24.8）现状：`udpsrc` `rtpjitterbuffer` `rtph264depay` `rtpopusdepay` `filesink` 有；
**缺** `h264parse`、`avdec_h264`——所以 AP 只能落原始 H.264，解码拿回 Pi/PC 做。

---

## 四、四条硬证据（证明媒体真走了无线 STA→AP）

| # | 证据 | 采集点 | 期望 |
|---|---|---|---|
| 1 | `eth0` TX 增量 ≈ 0 | Pi `ip -s link` | 管理流量除外，媒体不在有线口 |
| 2 | `wlan1` TX 增量 ≈ 码率×时长 | Pi `ip -s link` | 与发送码率量级吻合 |
| 3 | AP 无线口抓到 `0x88B5`/UDP 5004 帧 | AP `tcpdump -i phy0.1-ap0` | 方向 STA→AP，单 SSRC |
| 4 | `station dump` rx bytes 增量对上 wlan1 TX 增量 | AP `iw ... station dump` | 两边差值一致，无法伪造 |

> 反常识提醒：**数据太漂亮本身就是异常信号**。20 Mbps 跑 1080p30，如果丢包 0.00%、时延 <1 ms、抖动 0.1 ms，大概率是走了有线或被本机回环接住；正常无线应有 0.05–0.5% 丢包、几 ms 抖动、retries 在涨。

---

## 五、常见误判对照

| 现象 | 误判 | 正确归因方法 |
|---|---|---|
| 收端 300 帧完好 | "STA→AP 基线通过" | 先确认接收端是不是 AP/有线参考端；同机 netns 不算 |
| AP 抓到包 | "AP 完整接收成功" | fakesink 只听不存；要落盘 + 解码数帧才算 |
| `bind-address=.126` | "流量走 wlan1" | bind 只改源 IP；出口看 `ip route get` |
| pcap 序号跳变 | "大量丢包" | A-MSDU 聚合所致；重建 H.264 后数帧才算 |
| 退出码 rc=0 | "功能正常" | rc=0 只代表管线没崩；帧完整率/同步偏差要另测 |
