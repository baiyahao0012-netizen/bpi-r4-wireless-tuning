# 真实 OAF 豆包流 + DSCP/AC 加速：A/B 验证（2026-10-25）

## 1. 环境

- 板：BPI-R4，OpenWrt 24.10.0 / 6.6.73；
- OAF：v7.0.1 源码，**仅内核模块 kmod-oaf 6.6.73** + 最小用户态 feature loader（无完整 oafd）；
- 自定义特征：
  ```text
  1900~DoubaoAI:[tcp;;443;doubao.com;;]
  ```
- OAF 已把 AppID 写入 conntrack mark 低 16 位；
- 加速规则：
  ```sh
  nft add rule ip oaf_accel post ct mark & 0xffff == 1900 counter ip dscp set ef
  ```

## 2. 验证 OAF 真实识别

PC 通过 BPI-R4 AP（192.168.240.126）访问：

```sh
curl --interface 192.168.240.126 -k https://www.doubao.com/
```

板端 `/proc/net/nf_conntrack` 出现：

```text
src=192.168.240.126 dst=122.189.80.185 sport=... dport=443 ... mark=1900
```

`nft` 计数：

```text
ct mark & 0x0000ffff == 0x0000076c counter packets 241 bytes 75543 ip dscp set ef
```

说明 OAF 的 SNI 识别、ct mark、nft DSCP 全部真实生效，不是 mock。

## 3. A/B 方法

- 同一 STA 192.168.240.126；
- 竞争负载：板端 iperf3 server :5201，PC 反向 TCP 30 s，约 410 Mbit/s；
- 豆包探针：`curl --interface 192.168.240.126 -k https://www.doubao.com/`，取 `time_starttransfer`，10 次；
- A 基线：不安装 `oaf_accel`；
- B 加速：`oaf_accel.sh install 1900 ef`，Doubao ct mark=1900 → EF → VO。

## 4. 结果

| 指标 | A 基线 | B 加速 | 变化 |
|---|---|---|---|
| 竞争负载 | 412 Mbit/s | 410 Mbit/s | 基本一致 |
| TTFB 均值 | 0.387 s | 0.233 s | −40% |
| TTFB p50 | **0.351 s** | **0.228 s** | **−35%** |
| TTFB p95 | **1.030 s** | **0.314 s** | **−70%** |

原始 10 次 TTFB（秒）：

```text
A: 0.363856 1.030147 0.438508 0.384177 0.282764 0.220456 0.153359 0.419537 0.238369 0.338740
B: 0.200092 0.217732 0.242296 0.297883 0.243548 0.313547 0.170663 0.239101 0.210447 0.192361
```

## 5. 解释

- 在约 410 Mbit/s 同 STA 竞争下，豆包 HTTPS 首字节 p95 从 1.03 s 降到 0.31 s；
- 说明“OAF 识别 → ct mark 1900 → nft EF → AC_VO”链路在真实豆包 SNI 流量上有效；
- 但这是 `curl` 到 doubao.com 的 HTTPS 探针，不是豆包 App 文字/语音/图片业务；真实 App 的 A/B 仍需手机 + 抖音直播；
- 竞争负载是 iperf3 TCP，不是抖音直播 UDP/QUIC；真实抖音直播的竞争更强，需下一步验证。

## 6. 限制

- 当前 OAF 只覆盖 `doubao.com` 的 TCP 443；豆包图片/语音/CDN/QUIC 可能不在内；
- 最小 loader 只加载特征，不提供完整 oafd 的 LuCI/记录/在线更新；
- `/proc/net/af_active_app` 在最小 loader 下未填充，但 conntrack mark 已足够用于加速；
- 真实手机 App A/B 尚未做。
