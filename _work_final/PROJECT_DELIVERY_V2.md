# BPI-R4 AI 业务识别 + EDCA 自主调优 交付文档 V2

> 交接文档 · 2026-10-30
> 目标：上层软件层自主识别 AI 业务（以豆包为例），下层对 EDCA 参数自主调优，实现 AI 业务加速，并用视频/数据证明效果。

---

## 1. 项目目标（必须对齐）

1. **识别**：软件层自动识别哪些流量是 AI 业务（豆包）。
2. **调优**：对识别出的业务做 EDCA 参数自主调优（AC_VO 优先）。
3. **证明**：用视频 + 量化指标证明加速前后的差异。

**关键认知（务必先读）**：EDCA 是「跨 STA 抢空口」的优先级机制。当 AI 业务需求（视频约 2 Mbit/s）远小于空口容量（~100 Mbit/s）时，EDCA 的收益只体现在**时延尾部**（P90/最大 TTFB、抖动），**不会出现肉眼可见的“卡死→流畅”**。要做出肉眼效果，必须让空口容量接近或低于 AI 需求。

---

## 2. 环境与拓扑

### 硬件
- 开发板：BPI-R4（MediaTek MT7988 + MT7996A WiFi），OpenWrt
- 手机：Redmi K60（23013RK75C），Android 15
- PC：Windows，Python 3.10

### 网络
| 设备 | 接口 | 地址 | 说明 |
|---|---|---|---|
| 板子 5G AP | phy0.1-ap0 | 192.168.240.1 | SSID **BPI-R4-5G**，ch149，HT20 |
| 板子 2.4G AP | phy0.0-ap0 | — | SSID BPI-R4 |
| 板子 WAN | phy0.0-sta0 | 10.75.4.209 | STA 连外部 AP（如 `Bai`） |
| 手机 | wlan0 | **192.168.240.219** | MAC 06:65:45:fc:44:3d |
| PC 有线 | 以太网 | 192.168.240.2 | 连板子 LAN |
| PC WLAN | Realtek 8852CE | 192.168.240.147 | MAC c0:35:32:19:cc:fb |
| PC WLAN 3 | MediaTek USB | 192.168.240.126 | MAC 90:de:80:1c:6a:7a |

- 板子 SSH：`ssh root@192.168.240.1`（root，空密码/key）
- 手机 ADB：`_work_recover/platform-tools/platform-tools/adb.exe`，序列号 `109be14a`
- 板子时间与本地有偏差（板子约 UTC+8 但显示不同步），日志对时间时注意。

---

## 3. 核心架构

```
手机/PC 流量
   ↓
OAF 识别（SNI/DNS 匹配特征库，写 conntrack mark 低 16 位 = app_id）
   ↓  mark=1900（豆包 doubao.com:443）
nft postrouting（priority mangle）
   ct mark & 0xffff == 0x76c → ip dscp set ef
   ↓  DSCP EF(46)
mac80211 cfg80211_classify8021d() 映射 → AC_VO
   ↓
mt7996 EDCA 参数（AIFS/CW/TXOP）→ 高优先级抢空口
   ↓
手机侧优先得到 AI 业务数据
```

### 关键组件
| 组件 | 位置 | 作用 |
|---|---|---|
| OAF 内核模块 | /root/oaf.ko | 流量识别，写 conntrack mark |
| OAF loader | /root/oaf_load | 加载特征文件 |
| 特征库 | /root/oaf_feature_plain.txt | 49 条，含 `1900~DoubaoAI:[tcp;;443;doubao.com;;]` |
| nft 加速规则 | /root/oaf_accel.sh | mark→DSCP EF |
| EDCA 调参工具 | /root/edca_set（aarch64） | nl80211 SET_WIPHY+TXQ_PARAMS 实时改 AC 参数 |
| 开机脚本 | /root/oaf_boot.sh + /etc/rc.local | 开机自动加载 OAF + EDCA |
| 看板 | 本地 dashboard.py（8099） | 实时指标 + 加速开关 + 背景流 + CSV 记录 |

---

## 4. 已实现文件清单

### 板子端（/root 与 /etc）
| 文件 | 说明 |
|---|---|
| /root/oaf.ko | OAF 模块 |
| /root/oaf_load | 特征加载器 |
| /root/oaf_feature_plain.txt | 特征库（49 条） |
| /root/oaf_accel.sh | `install/remove/status/verify`，加速规则 |
| /root/edca_set | EDCA 参数下发二进制 |
| /root/edca_set.py | 源码/说明 |
| /root/oaf_boot.sh | 开机延迟 20s 加载 OAF + EDCA |
| /etc/rc.local | 调用 oaf_boot.sh |
| /root/phone_police.sh | 可选：手机下行 nft 限速（**不是 EDCA，演示慎用**） |
| /root/txrate.sh | 测手机下行速率（station tx bytes） |

### PC 端（_work_final/doubao_test/）
| 文件 | 说明 |
|---|---|
| dashboard.py | 看板服务（8099），见第 8 节 |
| udpflood.py | 同 STA 背景流：单线程、多目标端口产生 N 条流 |
| bgload.py | 跨 STA 背景流：从指定源 IP 拉板子大文件 |
| ttfb2.py | pcap 双向流分析（TTFB/停顿） |
| dscp_count.py | pcap DSCP 分布统计 |
| flow_analyze.py | pcap 流级统计 |
| evidence.py | DNS + 端口证据 |
| analyze_dash.py | 读看板 CSV/接口做前后对比 |
| oaf_boot.sh / rc.local | 板子开机脚本的本地副本 |
| dash_log.csv | 看板逐秒记录（测试数据） |

### 板子端大文件
- /tmp/big.bin（300MB，tmpfs，重启丢失）
- /www/big.bin → /tmp/big.bin（uhttpd 下载源，重启后需重建）

---

## 5. 已验证的数据与证据（真实测到）

### 5.1 识别链路
- `/proc/net/af_visit`：手机 MAC 对应 `www.doubao.com`
- `grep -c mark=1900 /proc/net/nf_conntrack`：>0
- `nft list table ip oaf_accel` 计数：`mark==0x76c → EF` **1125 包 / 766 KB**（文本/API 场景）
- 视频 app10：`mark==0xa → EF` **426 包 / 309 KB**

### 5.2 EDCA 参数（edca_set 返回）
| AC | aifs | cwmin/cwmax | txop | 计算延迟 |
|---|---|---|---|---|
| VO (AC3) | 1 | 3/7 | 94 | **405.6 µs** |
| VI (AC2) | 2 | 7/15 | 94 | 356.3 µs |
| BE (AC0) | 3 | 31/1023 | 0 | **595.4 µs** |

### 5.3 同条件加速前后（60s 窗口，6M+背景流）
| 指标 | 加速前 | 加速后 |
|---|---|---|
| TTFB 均值 | 167.6 ms | 133.2 ms |
| TTFB P50 | 109.2 ms | 116.3 ms |
| **TTFB P90** | **552.1 ms** | **273.1 ms** |
| **TTFB 最大** | **857.9 ms** | **390.4 ms** |
| EF 加速流量 | 0 | 5.72 KB/s |

> 结论：尾部时延腰斩，中位数被服务器处理时间掩盖。

### 5.4 容量限制（force_rate）有效性
| 条件 | 手机实际下行 |
|---|---|
| 自动速率 | **14.47 MB/s（116 Mbit/s）** |
| force_rate=0（6M） | **0.59 MB/s（4.7 Mbit/s）** |

### 5.5 背景流拥塞有效性（手机 RTT）
| 条件 | RTT avg | max |
|---|---|---|
| 无背景 | 32.7 ms | 99.4 ms |
| **同 STA 100 条** | **141.7 ms** | **560.7 ms** |
| 跨 STA 2 个 PC 网卡 | 12.5 ms | 29.7 ms |

> 结论：**同 STA 背景流有效**（4 倍时延），跨 STA 2 个不够（公平份额仍够用）。

---

## 6. 已知限制与坑（重要）

1. **OAF 模块重启必丢**：已用 `/etc/rc.local → /root/oaf_boot.sh` 持久化。若没加载，`/proc/net/af_*`、`/proc/sys/fwx/*` 都不存在，mark 永远 0，加速表空转。**这是之前“没效果”的最常见原因。**
2. **视频媒体（UDP 9924）识别不稳定**：OAF 有时标 app10、有时标 0；文本/API（doubao.com:443）稳定识别 1900。
3. **force_rate 只有 6M 一档**：写入任意值 dmesg 都是 `force fixed rate table 35 = 0xb`，实际只有 6 Mbit/s。**复位只能断电**（软重启/写 -1/0xffffffff 都无效）。
4. **force_rate 不能与模块重载混用**：重载 mt7996e 曾导致 WiFi 芯片 PCIe FLR 卡死，需断电。
5. **同 STA 背景流不会让 AI“卡死”**：它是同 STA 内竞争，AQL 限制队列深度，AI 小流量仍能过；只提升 RTT。
6. **跨 STA 2 个不够**：4.7 Mbit/s 由 3 个 STA 公平分，手机仍有 ~1.5 Mbit/s。
7. **dashboard 曾因同步 SSH + 锁卡住**：已改为后台采样缓存 + 前端 4s 超时；仍建议单标签页使用。
8. **WAN 依赖外部 AP**：板子 WAN 是 2.4G STA（如 `Bai`），该 AP 掉线则整个网络无公网，视频通话打不开。
9. **板子重启后 /tmp/big.bin 丢失**：需重建 `dd + ln`，否则 bgload 拉不到文件。
10. **手机可能瞬移到别的 WiFi**（如 192.168.59.x）：测试前必须确认手机 IP 是 192.168.240.219 且板子 station 列表里有它。

---

## 7. 复现步骤（从零到可测）

### 7.1 板子初始化
```sh
# 1) 加载 OAF
insmod /root/oaf.ko
/root/oaf_load /root/oaf_feature_plain.txt
echo 1 > /proc/sys/fwx/appfilter_enable
echo 1 > /proc/sys/fwx/feature_init
cat /proc/sys/fwx/feature_count          # 应为 49

# 2) EDCA 调参
/root/edca_set phy0.1-ap0 3 1 3 7 94     # VO
/root/edca_set phy0.1-ap0 0 3 31 1023 0  # BE
/root/edca_set phy0.1-ap0 2 2 7 15 94    # VI

# 3) 加速规则（基线先不装）
sh /root/oaf_accel.sh install            # 开
# nft delete table ip oaf_accel          # 关

# 4) 大文件（背景流用）
dd if=/dev/zero of=/tmp/big.bin bs=1M count=300
ln -sf /tmp/big.bin /www/big.bin

# 5) 6M 窄带（可选，演示用；断电才能复位）
echo 0 > /sys/kernel/debug/ieee80211/phy0/mt76/force_rate
```

### 7.2 PC 看板
```powershell
cd "D:\Desktop\AI 辅助对话"
python _work_final\doubao_test\dashboard.py 8099
```
浏览器打开 <http://127.0.0.1:8099>

### 7.3 验证识别
```powershell
# 手机访问豆包
& adb shell "curl -s -o /dev/null https://www.doubao.com"
# 板子看 mark
ssh root@192.168.240.1 "grep -c mark=1900 /proc/net/nf_conntrack; nft list table ip oaf_accel"
```

### 7.4 背景流
- 同 STA：看板「同STA背景流」开，条数 100。（实测 RTT 33→142ms）
- 跨 STA：看板「跨STA背景流」开（PC 两张 WiFi 卡需连 BPI-R4-5G）。

---

## 8. 看板说明（dashboard.py）

- 地址：<http://127.0.0.1:8099>
- 控件：
  - **加速**：同步等待板子真实结果（off ~333ms / on ~341ms）
  - **同STA背景流** + 条数（10–200）：PC→手机 UDP 背景流
  - **跨STA背景流**：PC 两张 WiFi 卡拉板子大文件
  - **记录**：下载 CSV / 清空
- 指标（1–2s 刷新，Y 轴自动缩放）：TTFB、AI 下行、EF 加速流量、手机 RTT
- 记录文件：`_work_final/doubao_test/dash_log.csv`
  - 字段：time, accel, bg, bg_n, phone_kbs, ai_dl_kbs, ef_kbs, ttfb_last_ms, ttfb_p50_ms, ttfb_max_ms, ttfb_n, rtt_avg_ms, signal, tx_rate
- 注意：TTFB 来自板子 tcpdump 流（443/9924/8080），AI 识别为近似值；RTT 为板子 ping 手机。

---

## 9. 当前状态（交接时刻）

| 项 | 状态 |
|---|---|
| 板子 5G AP | BPI-R4-5G，ch149，HT20，**3 个 STA 全 6.0 Mbit/s** |
| 6M（force_rate=0） | **开**（需断电复位） |
| OAF | 已加载（49 条特征） |
| 加速规则 | **关**（只剩 fw4） |
| 同 STA 背景流 | **开，100 条** |
| 手机 | 192.168.240.219，视频通话测试中 |
| WAN | 连 `Bai`（2.4G ch11） |
| 看板 | 运行中（8099） |
| 板子开机脚本 | 已持久化（OAF + EDCA 自动加载） |

---

## 10. 下一步建议（给接手的 Agent）

### 优先级 1：确认「效应」到底能不能做出来
- 先复现第 5.3 节的 60s 对照（同条件、只切加速），确认尾部 TTFB 是否稳定腰斩。
- 用 `analyze_dash.py` 读 CSV 出正式表格。

### 优先级 2：扩大识别覆盖（这是收益上限）
- 给 `/root/oaf_feature_plain.txt` 增加豆包相关域名（api.doubao.com、snssdk.com、byteimg.com、ecombdimg.com、bytedance.com、volccdn.com 等），TCP+UDP 443。
- 视频媒体（UDP 9924）没有 SNI，只能按端口或设备级兜底；加规则前先确认端口稳定。

### 优先级 3：做出肉眼可见的卡→不卡
- 需要把空口容量压到 < 2 Mbit/s；`force_rate` 只给 6M（4.7 Mbit/s），做不到。
- 可选：换 `mt7996e_edca2.ko` / 自定义固定速率表（/root 下有多个 mt7996e 变体），或改用 nft policer 造窄带（但那时瓶颈不是空口，EDCA 不再是主因，报告要写清）。
- 或用多 STA（>10 个）稀释公平份额（不现实）。

### 优先级 4：工程化
- 把 dashboard 做成 nft/SSH 失败自动重试，避免锁卡。
- 开机脚本增加「6M/自动」的选择（注意复位只能断电）。
- 记录每次测试的 CSV + 配置快照，便于对比。

---

## 11. 关键命令速查

```sh
# OAF 状态
cat /proc/sys/fwx/feature_count
ls /proc/net/af_*
cat /proc/net/af_visit

# 识别与标记
grep -c mark=1900 /proc/net/nf_conntrack
nft list table ip oaf_accel
nft list tables

# EDCA
/root/edca_set phy0.1-ap0 3 1 3 7 94

# 速率 / 6M
iw dev phy0.1-ap0 station dump | grep -E 'tx bitrate|signal'
echo 0 > /sys/kernel/debug/ieee80211/phy0/mt76/force_rate

# 背景流文件
dd if=/dev/zero of=/tmp/big.bin bs=1M count=300
ln -sf /tmp/big.bin /www/big.bin
```

---

## 12. 一句话总结

**识别→DSCP EF→AC_VO→EDCA 调参链路已打通并验证（mark=1900、EF 命中、VO 405µs vs BE 595µs、TTFB 尾部腰斩）；但受限于 100 Mbit/s 空口与 AI 业务 2 Mbit/s 需求的巨大差距，以及 force_rate 只有 6M 一档，目前只能证明「时延尾部改善」，做不出「肉眼卡死→流畅」。接手后若要视频效果，需先解决更低的空口容量或更高码率的被测业务。**
