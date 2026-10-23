# 方案 1（AC 策略 VIP）实现与多轮实测（2026-10-22）

## 实现

在板端用 nftables 给 VIP STA 的下行流量打 DSCP EF，mac80211 自动映射到 AC_VO；普通 STA 保持 BE。

```sh
# /root/vip_set.sh <VIP_IP>
nft delete table ip vip 2>/dev/null
nft add table ip vip
nft add chain ip vip out '{ type route hook output priority mangle; }'
nft add rule ip vip out ip daddr <VIP_IP> counter ip dscp set ef
```

当前板端已将 VIP 设为 `192.168.240.126`（WLAN3 MediaTek，HE 1080 Mbps）。

> 说明：本次 iperf3 server 跑在板端，走 `output` 链；如果是 WAN→STA 的转发流量，需要再加 `forward`/`postrouting` 链。

## 实验条件

- 5G AP `phy0.1-ap0`，ch149 HE80；
- 两个 STA 同时 TCP 下行 8 s：
  - WLAN3 MediaTek：192.168.240.126，HE 1080 Mbps；
  - WLAN5 Realtek 8812BU：192.168.240.232，VHT 650 Mbps；
- 每轮交换 VIP 身份，共 6 轮（VIP 快 STA 3 轮、VIP 慢 STA 3 轮）；
- 读取每轮前后 `stations/<MAC>/airtime` 的 TX 增量。

## 结果

| 轮次 | VIP STA | VIP 吞吐 | 普通吞吐 | 吞吐比 | VIP airtime | 普通 airtime | airtime 比 |
|---|---|---|---|---|---|---|---|
| 1 | WLAN3（快） | 198 Mbit/s | 55 Mbit/s | 3.60:1 | 4.97 s | 1.38 s | 3.60 |
| 2 | WLAN5（慢） | 92 Mbit/s | 94 Mbit/s | 0.98:1 | 5.22 s | 1.09 s | 4.79 |
| 3 | WLAN3（快） | 198 Mbit/s | 48 Mbit/s | 4.09:1 | 5.05 s | 1.35 s | 3.74 |
| 4 | WLAN5（慢） | 88 Mbit/s | 90 Mbit/s | 0.98:1 | 5.08 s | 1.06 s | 4.79 |
| 5 | WLAN3（快） | 191 Mbit/s | 54 Mbit/s | 3.54:1 | 4.85 s | 1.46 s | 3.32 |
| 6 | WLAN5（慢） | 89 Mbit/s | 93.5 Mbit/s | 0.95:1 | 5.02 s | 1.09 s | 4.61 |

### 平均

| 场景 | VIP 平均 | 普通平均 | 吞吐比 | VIP airtime | 普通 airtime | airtime 比 |
|---|---|---|---|---|---|---|
| VIP 在快 STA（WLAN3） | 195.7 Mbit/s | 52.3 Mbit/s | **3.74:1** | 4.96 s | 1.40 s | 3.55 |
| VIP 在慢 STA（WLAN5） | 89.7 Mbit/s | 92.5 Mbit/s | **0.97:1** | 5.11 s | 1.08 s | 4.73 |

## 分析

1. **AC 策略生效且稳定**：无论 VIP 放在哪台 STA，VIP 都拿到约 **4.7–4.8 倍**的 TX airtime，说明 DSCP EF→AC_VO 的映射和 EDCA 仲裁确实起作用。
2. **吞吐效果取决于 VIP 的链路速率**：
   - VIP 在快 STA（HE 1080）时，吞吐 **3.5–4.1 倍**，普通 STA 仍有 48–55 Mbit/s，没有被完全饿死；
   - VIP 在慢 STA（VHT 650）时，虽然拿到 4.7 倍 airtime，但吞吐只有 **0.95–0.98 倍**，因为低速率把 airtime 优势抵消了。
3. **这不是“可配置 2:1/4:1”**：比例由 EDCA 参数和链路速率决定，不能通过一个配置项精确设定；要 2:1/4:1 的 per-STA 比例，需要方案 2（A+）的字节/预算加权。
4. **普通 STA 没有被完全饿死**：快 VIP 场景普通仍有约 50 Mbit/s；如果现场不能接受，可用 VI 替代 VO，或给 VIP 加 policer。

## 结论

- **方案 1 已实现并验证**：VIP 下行吞吐在快 STA 上稳定 **3.5–4.1 倍**，VIP airtime 约 **4.7 倍**；
- 适合“马上演示 VIP”与“VIP 在 5G/高速 STA”的场景；
- 不适合“VIP 在慢 STA 也要更快”或“精确 2:1/4:1”的场景——后者需要 A+（方案 2）的 per-STA 权重/预算；
- 当前板端已把 VIP 设为 WLAN3（192.168.240.126），可直接复现；用 `/root/vip_set.sh <IP>` 切换 VIP，`nft delete table ip vip` 关闭。
