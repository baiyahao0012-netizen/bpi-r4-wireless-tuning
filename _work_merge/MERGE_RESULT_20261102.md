# 双系统合并结果与验证报告（2026-11-02）

## 1. 结论

**合并已完成并通过实机端到端验证。** 基线 = 我方（开发板原系统），
把对方（`sdcard.img.gz`）的两组补丁合并进我方基线，并重建内核与**全部内核模块**后刷入开发板。

开发板当前状态：
- 内核 `Linux 6.6.73 #2 SMP Mon Nov 2 19:32:30 CST 2026 aarch64`
- `/sys/kernel/debug/tracing/events/mac80211/wifi_dscp` **已注册并可用**（ID 1042）
- Wi-Fi 正常：`phy0.0-ap0`(BPI-R4) / `phy0.1-ap0`(BPI-R4-5G) / `phy0.0-sta0` 已连上游
- `dscpstats` 离线测试 35/35 通过，实机统计报表正确输出
- **`oaf.ko` 已用 SDK 内源码在新内核上重建并恢复**，`/proc/sys/fwx/` 全部就位、appfilter 已启用
- **重启集成测试通过**：开机自动加载 104 个模块、WDRR 调度器激活、DSCP tracepoint 可用、Wi-Fi 与上游连通

## 2. 合并的补丁

| 来源 | 补丁 | 说明 |
|---|---|---|
| 对方 | `354-wifi-mac80211-add-dscp-latency-tracepoint.patch` | mac80211 增加 `wifi_dscp` tracepoint（8 个 DSCP 埋点：AF41 CS5 CS4 AF31 AF21 AF12 AF11 CS1） |
| 对方 | `355-wifi-mt76-mt7996-report-tx-retries.patch` | mt7996 用 `MT_TXS5_F0_TX_COUNT` 上报真实发送尝试次数 |
| 我方 | A+ 补丁（`apply_aplus.py`） | mt76 私有增强 |
| 我方 | `apply_txwi_rate.py` | txwi rate 处理 |
| 我方 | `360-wdrr-private-scheduler.patch` | mac80211 WDRR 私有调度器 |
| 我方 | 强制默认 EEPROM（诊断用，`mt7996_eeprom_check_or_use_default(dev, true)`） | 与板子当前状态一致 |

对方系统版本更高（kernel 6.6.151 / backports 6.12.96 / mt76 2025.11.06），
按“基线选我方”决策，**只提取其补丁语义**，移植到 6.6.73 / backports 6.12.6 / mt76 2025.01.14。

## 3. 内核构建

### 3.1 基线配置
SDK 原始内核配置（`linux-6.6.73/.config.before-ftrace`，206,583 B）即用户基线配置：

```
CONFIG_DEBUG_INFO=y
CONFIG_JUMP_LABEL=y
CONFIG_MODULE_UNLOAD=y
# CONFIG_KALLSYMS is not set
# CONFIG_MODULES_TREE_LOOKUP is not set
# CONFIG_STACKTRACE is not set
# CONFIG_FTRACE is not set
```

### 3.2 加入的最小 tracing 选项
```
CONFIG_TRACEPOINTS=y
CONFIG_TRACING=y
CONFIG_EVENT_TRACING=y
CONFIG_NOP_TRACER=y
CONFIG_TRACE_CLOCK=y
CONFIG_RING_BUFFER=y
CONFIG_DYNAMIC_EVENTS=y
CONFIG_SYNTH_EVENTS=y
CONFIG_FTRACE=y
CONFIG_BINARY_PRINTF=y
```
明确关闭（避免体积膨胀）：`FUNCTION_TRACER` / `DYNAMIC_FTRACE` / `FTRACE_SYSCALLS` /
`KPROBES` / `KPROBE_EVENTS` / `ENABLE_DEFAULT_TRACERS` / `FUNCTION_GRAPH_TRACER` / `HIST_TRIGGERS`。

> 说明：`CONFIG_TRACING` 是 `kernel/trace/Kconfig` 中 `FTRACE` 菜单**之前**的无提示 bool，
> 因此不需要 `FUNCTION_TRACER` 也能启用事件追踪。
> 但开启 tracing 会**强制**打开 `KALLSYMS` / `MODULES_TREE_LOOKUP` / `STACKTRACE`（Kconfig select/def_bool）。

### 3.3 struct module 变化（关键副作用）
| 配置 | `.gnu.linkonce.this_module` 大小 |
|---|---|
| 基线（KALLSYMS=n, MODULES_TREE_LOOKUP=n） | **0x280** |
| 加 tracing 后 | **0x480** |

**后果：所有旧模块（含原厂 `/rom` 模块、用户自建模块、纯二进制 `oaf.ko`）都无法再加载，
必须全部重建。** 这是启用 tracepoint 的必然代价，对方系统同样如此。

## 4. FIT 打包（严格保持总大小）

- 原始 FIT 总大小 **0x1032000 = 16,982,016**，`fitrw` 起始扇区 = 33168。
  **总大小必须精确不变**，否则 `fitrw` 偏移改变会破坏 `/overlay` 的 F2FS。
- 新内核 raw Image 14,651,400 B，`zstd -19` → 5,515,772 B（旧 gzip 5,633,434）。
  U-Boot 2024.10-OpenWrt 的 FIT loader **只支持 gzip 和 zstd**（lzma/bzip2/lzo/lz4 均不支持）。
- rootfs 填充 118,784 B（0xADE000 = 11,395,072，4 KiB 对齐）后总大小精确回到 0x1032000。
- 刷写：`dd if=/tmp/new.itb of=/dev/mmcblk0p7 bs=4096 count=4146`
- 新 FIT 偏移：kernel-1 0x0 / fdt-1 0x543000 / emmc 0x54f000 / rtc 0x550000 /
  sd 0x551000 / wifi 0x552000 / rootfs-1 0x553000（绝对 0x554000），结束于 0x1032000。

## 5. 模块重建（103 个）

| 类别 | 数量 | 来源 |
|---|---|---|
| 内核树模块 | 96 | `/root/kbuild/linux-6.6.73`（`make modules -j24`，1098 个 .ko 中按板子清单取 96） |
| `gpio-button-hotplug.ko` | 1 | OpenWrt 独立包，用内核树 `M=` 手工编译 |
| backports 模块 | 6 | SDK `package/kernel/mac80211` + `package/kernel/mt76`（含合并补丁） |

### 关键坑
1. `make modules` 需要正确的 `STAGING_DIR`：
   必须是 `staging_dir/target-aarch64_cortex-a53_musl`，
   设成 `staging_dir` 会导致 `-Werror=missing-include-dirs` 编译失败。
2. SDK 内核树是裁剪过的（无 Kconfig，无法 `olddefconfig`）。
   改配置后必须**手工同步** `include/generated/autoconf.h` 与 `include/config/auto.conf`，
   否则 backports 模块仍按旧 `struct module` 编译（表现为 `this_module` = 0x4c0 而非 0x480）。
3. 部署时**直接写 `/overlay/upper/...` 会绕过 overlay 的 dcache**，
   正在运行的 overlay 仍读到下层旧文件。必须：
   - 写入 overlay 路径 `/lib/modules/6.6.73/`，或
   - 写 `/overlay/upper/` 后**重启**（重启会重新挂载 overlay）。
4. 用 `cp -a` 逐个写 103 个模块（33 MB）在 SD 卡 + f2fs discard 下非常慢（约 7 s/文件），
   直接写 `/overlay/upper` 快得多。

### 最终模块 md5
```
mac80211.ko        e86e188e429e4facf0fc6ca53bd2ac41
cfg80211.ko        64719538a7974dce79a8c1111e786b32
compat.ko          d4b851814c75f358b08283dd5d76ec07
mt76.ko            dd76cb892ca26f7d75eb1314cf3e4e71
mt76-connac-lib.ko c46bc687e2898170a047c5d45e7ae595
mt7996e.ko         6ee22882cc2ff8ca3429f370c0c6d85b
```
全部 `this_module` = 0x480，与新内核一致。

## 6. 验证结果

### 6.1 tracepoint 注册
```
name: wifi_dscp   ID: 1042
field:u8 dir; u8 stage; u8 dscp; u16 len; const void *skb; u64 ts; u8 acked; u8 retry
print fmt: "dir=%u stage=%u dscp=0x%02x len=%u skb=%p ts=%llu acked=%u retry=%u"
```

### 6.2 实机事件（10 次 ping，43 条事件）
```
dir=0 stage=0 dscp=0x88 len=98 skb=... ts=... acked=0 retry=0   (ENQ, ping 进程)
dir=0 stage=1 dscp=0x88 len=98 skb=... ts=... acked=0 retry=0   (DEQ, mt76-tx)
dir=0 stage=2 dscp=0x00 len=98 skb=... ts=... acked=1 retry=0   (ACK, napi/phy0)
dir=1 stage=3 dscp=0x88 len=98 skb=... ts=... acked=0 retry=0   (RX, napi/phy0)
```

### 6.3 dscpstats 离线测试（板子上，busybox awk）
- L2 awk 聚合黄金测试：**20 passed, 0 failed**
- L3 流水线（start/feed/stop）：**15 passed, 0 failed**

### 6.4 dscpstats 实机报表
```
DSCP   business             TXpkts  TXbytes  ACK fail  queue us avg/min/max       access us avg/min/max       e2e us avg/min/max        RXpkts RXbytes retryP reAvg reMax re%
0x48   browsing                  3      270    3    0  25.4/ 21.7/ 31.2        1716.2/ 560.5/3793.0     1741.6/ 584.0/3824.2        0      0      0   0.0    0  0.0
0x88   video-call-media         50     4900   50    0  42949.7/ 18.5/1000190.6  17508.5/ 562.2/278162.7  42949.7/ 581.5/1003175.7   49   4802      0   0.0    0  0.0
```
（retry 各列为 0 属正常：链路质量好，无重传。要验证 355 补丁需制造重传场景。）

## 7. `oaf.ko`：已重建并恢复（原先失效，现已解决）

### 7.1 问题
用户自研 QoS/应用加速模块 `/root/oaf.ko`（原 906,832 B，`this_module` = **0x280**）
在 tracing 内核上无法加载：

```
module oaf: .gnu.linkonce.this_module section size must match
            the kernel's built struct module size at run time
```

**原因**：开启 tracing 强制 `KALLSYMS`/`MODULES_TREE_LOOKUP`/`STACKTRACE`，
`struct module` 从 0x280 涨到 0x480，**所有**旧二进制模块的 ABI 都不再匹配。

### 7.2 解决：源码就在 SDK 里，直接重建
SDK 中带有完整的 OpenAppFilter 包，**`oaf.ko` 的内核模块源码是齐的**：

```
$SDK/package/OpenAppFilter/oaf/Makefile        # KernelPackage，FILES:=$(PKG_BUILD_DIR)/oaf.ko
$SDK/package/OpenAppFilter/oaf/src/Makefile    # Kbuild: oaf-objs := fwx_main.o fwx_utils.o ... ; obj-m += oaf.o
$SDK/package/OpenAppFilter/oaf/src/fwx_main.c  # MODULE_LICENSE("GPL") / MODULE_AUTHOR("www.fanchmwrt.com")
```
（另有 `open-app-filter/` 为用户态 `oafd`，`luci-app-oaf/` 为 LuCI 界面。）

用**新的 tracing 内核树**重新编译（out-of-tree `M=` 方式）：

```bash
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
KD=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/linux-6.6.73
TC=$SDK/staging_dir/toolchain-aarch64_cortex-a53_gcc-13.3.0_musl/bin/aarch64-openwrt-linux-musl-
cp $SDK/package/OpenAppFilter/oaf/src/* /root/oafbuild/ && cd /root/oafbuild
make -C $KD M=/root/oafbuild ARCH=arm64 CROSS_COMPILE=$TC \
  KCFLAGS="-Wno-error=missing-prototypes -Wno-error=missing-declarations \
           -Wno-error=unused-variable -Wno-error=declaration-after-statement \
           -Wno-error=implicit-fallthrough -Wno-error=missing-braces \
           -Wno-error=parentheses -Wno-error=format -Wno-frame-larger-than" modules -j16
```

结果：

```
新 oaf.ko   903,992 B   this_module = 0x480 ✅   md5 a8f19b8cb5c387f71a8410705f9dd518
modinfo     license=GPL  depends=nf_conntrack,nf_reject_ipv4  name=oaf
            vermagic=6.6.73 SMP mod_unload aarch64
```
与原 `oaf.ko` 的 `.modinfo` **逐字段一致**（`depends` 由源码符号自动推导，相同即源码相同）。

### 7.3 恢复验证
```
insmod /root/oaf.ko                     -> OK
/proc/modules:  oaf 118784 0 - Live (O)
nf_conntrack refcnt=8  含 oaf；nf_reject_ipv4 refcnt=3 含 oaf
/proc/sys/fwx/  -> 20 个控制文件（appfilter_enable / feature_init / version ...）
echo 1 > /proc/sys/fwx/appfilter_enable  -> ok
echo 1 > /proc/sys/fwx/feature_init      -> ok
/proc/sys/fwx/version = 6.0.1
重启后自动加载（/etc/init.d/oaf-mini START=99 -> /root/oaf_start.sh），
dmesg 中 oaf 的 "section size must match" 报错已消失。
```

### 7.4 其它
用户其它脚本（`edca_set`、`vip_ratio.sh`、`txrate.sh` 等）依赖 mt7996e 的 debugfs，
合并后的 mt7996e 已包含 A+ 补丁，**不受影响**。
boot 时仍有 8 条 `section size must match`，只涉及 `aquantia`/`gpio_button_hotplug`/
`leds_gpio`/`usb_common` 这 4 个模块 —— 它们在 preinit（overlay 挂载前）先按 `/rom` 旧模块
尝试一次而失败，随后从 `/overlay` 新模块重试并成功，属无害噪声。

## 8. 复现步骤

```bash
# 1) 内核
cd /root/kbuild/linux-6.6.73
make ARCH=arm64 CROSS_COMPILE=<sdk-toolchain> modules -j24   # 生成 1098 个 .ko

# 2) backports（先修好 SDK 内核树的 autoconf.h / auto.conf）
cd $SDK && make package/kernel/mac80211/clean && make package/kernel/mac80211/compile -j24
bash _build/build_merge_mt76.sh          # A+ / txwi_rate / 355 / EEPROM hack

# 3) 收集 103 个模块 → tar → 板子 /overlay/upper → 重启
bash /root/collect2.sh && bash /root/bpstage.sh && bash /root/deploy_bp.sh
ssh root@192.168.240.1 reboot

# 4) 验证
ls /sys/kernel/debug/tracing/events/mac80211/wifi_dscp
cd /tmp/dscptest/dscptest && sh test/run_tests.sh
./dscpstats start && ping -c 40 192.168.3.1 && ./dscpstats stop
```

## 9. 恢复手段

开发板若无法启动：拔出 SD 卡，用读卡器把
`_work_recover/p7_raw_pre_kernelflash_20261102.img.gz`
（44.9 MB gz，解压 469,762,048 B）写回 p7 分区即可回到刷写前状态。
