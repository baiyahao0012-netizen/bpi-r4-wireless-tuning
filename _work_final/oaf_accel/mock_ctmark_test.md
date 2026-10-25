# OAF 加速链路的 mock 验证（2026-10-25）

## 目的

当前板（OpenWrt 24.10 / 6.6.73）**没有安装 OAF**，无法直接做真实豆包流识别。
先用 nft 人为把一条测试流的 conntrack mark 置为 **1900**，模拟 OAF 识别结果，验证：

```text
ct mark 1900 → nft DSCP EF → mac80211 AC_VO → 同 STA 内优先
```

## 方法

- 板端 5G AP `phy0.1-ap0`，单个 STA `90:de:80:1c:6a:7a`（192.168.240.126）；
- 板端 iperf3 server 5201/5202，PC 反向双流 10 s，同一 STA；
- mock 规则：
  ```sh
  nft add rule ip mock_oaf out ip daddr 192.168.240.126 tcp sport 5201 ct mark set 0x0000076c
  ```
- 加速规则：
  ```sh
  nft add rule ip oaf_accel post ct mark & 0xffff == 0x76c counter ip dscp set ef
  ```

## 结果

| 组 | 5201 流 | 5202 流 | 说明 |
|---|---|---|---|
| 基线（无加速） | 229 Mbit/s | 249 Mbit/s | 约 0.92:1 |
| mock 加速（5201=1900） | **181 Mbit/s** | **84.5 Mbit/s** | **2.14:1** |

单流 5201（无竞争）约 213 Mbit/s。

### 计数器与 conntrack

```text
ct mark & 0x0000ffff == 0x0000076c counter packets 3364 bytes 117195928 ip dscp set ef
```

`/proc/net/nf_conntrack` 中可见：

```text
sport=5201 ... mark=1900 ...
```

说明 1900 标记、nft 匹配、DSCP 设置、计数增长全部生效。

## 解释

- 同一 STA 内，5201 流被标成 1900 → EF → VO；5202 流保持 BE；
- VO 获得约 2.14 倍于 BE 的吞吐；
- 但总吞吐从约 478 降到约 265 Mbit/s，说明 VO 优先级会牺牲总效率/聚合；
- 对豆包这种交互式业务，优先看 RTT/首响应/生存空间，不只看总吞吐。

## 限制

- 这是 **mock 1900**，不是 OAF 真实识别；
- 没有豆包/抖音真实流量，不能替代 A/B；
- 真实 OAF 验证需在装有 OAF v7.0.1 的板上进行（25.12.5/6.12.94）。

## 复现

```sh
/root/oaf_accel.sh install 1900 ef
nft add table ip mock_oaf
nft add chain ip mock_oaf out '{ type filter hook output priority mangle; }'
nft add rule ip mock_oaf out ip daddr 192.168.240.126 tcp sport 5201 ct mark set 0x0000076c
# 双流 iperf3 -R，10 s
/root/oaf_accel.sh remove
nft delete table ip mock_oaf
```
