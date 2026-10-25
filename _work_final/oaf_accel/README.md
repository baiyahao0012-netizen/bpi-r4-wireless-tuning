# OAF AppID → DSCP/AC 加速

## 1. 原理

OAF v7.0.1 在识别到自定义应用后，会把 AppID 写入 **conntrack mark 低 16 位**：

```c
#define FWX_CT_APPID_MASK 0x0000FFFFU
fwx_ct_set_appid(ct, app_id);
```

因此不需要改 OAF 内核，也不需要用户态轮询 `/proc`，直接用 nftables 匹配：

```text
ct mark & 0xffff == 1900  →  ip dscp set ef  →  mac80211 AC_VO
```

豆包（1900）进入 VO，抖音直播保持 BE，从而在抖音直播饱和时优先服务豆包。

## 2. 前置条件

- OAF v7.0.1（或确认同样把 AppID 写入 ct mark 的版本）已加载；
- `/etc/fwxd/custom_feature.cfg` 已有豆包规则：
  ```text
  1900~豆包（实验）:[tcp;;443;doubao.com;;]
  ```
- `/proc/net/af_active_app` 可见 1900；
- 板端有 `nft`、`tcpdump`（抓包可选）。

## 3. 安装/卸载

```sh
# 默认 1900 → EF
sh oaf_accel.sh install

# 指定其他 AppID / DSCP
sh oaf_accel.sh install 1901 ef

# 查看
sh oaf_accel.sh status
sh oaf_accel.sh verify

# 卸载
sh oaf_accel.sh remove
```

`verify` 会打印 nft 规则、计数器、以及 `/proc/net/nf_conntrack` 中低 16 位为 AppID 的 conntrack。

## 4. 验证顺序

1. 手机只开豆包，发一条文字聊天；
2. 板端：
   ```sh
   awk 'NR>1 && $1==1900 {print}' /proc/net/af_active_app | tail
   nft -s list table ip oaf_accel
   ```
3. 看到 1900 行 + nft counter 增长；
4. 抓包确认 DSCP EF：
   ```sh
   tcpdump -i br-oaf -nn -v 'ip and ip[1] & 0xfc == 0xb8'
   ```
5. 再开抖音直播，确认 1900 规则仍增长，抖音连接不被误标。

## 5. A/B 采集

```sh
# A 基线：先卸载加速
sh oaf_accel.sh remove
sh oaf_ab_capture.sh A 180 br-oaf /tmp/oaf_ab_A

# B 加速：安装后采集
sh oaf_accel.sh install 1900 ef
sh oaf_ab_capture.sh B 180 br-oaf /tmp/oaf_ab_B
```

采集内容：`capture.pcap`、`app_samples.txt`、`nft_before/after.txt`、`link_before/after.txt`、`summary.txt`。

### 场景

- 同一手机，抖音直播最高画质 + 豆包文字聊天；
- 每组 3–5 轮，每轮 3 分钟，随机顺序；
- 记录豆包 RTT p50/p95、首响应、卡顿；抖音直播码率/卡顿。

## 6. 指标

| 指标 | 方式 |
|---|---|
| 豆包 API RTT | `tcpdump` 抓 `br-oaf`，看 TCP RTT |
| 豆包首响应 | 录屏/客户端日志 |
| 豆包卡顿/重传 | tcpdump 重传、人工记录 |
| 抖音直播码率/卡顿 | 播放器统计/抓包 |
| OAF 命中 | `/proc/net/af_active_app` 1900 行 |
| 加速命中 | nft counter |
| DSCP | `tcpdump -v` ToS |

## 7. 限制

- 当前 OAF 规则只覆盖 `doubao.com` 的 **TCP 443**；图片/语音/CDN/QUIC 可能不在内；
- 首包可能未标记，长连接/后续包生效；
- OAF 的 5–10 秒是脚本观察间隔，不是内核识别延迟；
- VO 是优先级，不是无限带宽；抖音直播占满 PHY 时豆包仍受物理上限；
- 如 OAF 版本不写 ct mark，需改用 `/proc` watcher 或内核 hook。

## 8. 参考

- OAF 仓库：<https://github.com/destan19/OpenAppFilter>
- 验证提交：`b88fcb082597486a816187ec1e02812082161d5e`
- OAF 交接文档：豆包/千问/元宝各 3 轮正向 + 静置/网页对照；AppID 1900/1901/1902。
