# A+ / force_rate 模块（三件套）

| 文件 | md5 | 说明 |
|---|---|---|
| mt76.ko | `bc05b23788a77d45e3d445b5a470d9e3` | per-WCID token bucket |
| mt76-connac-lib.ko | `0ad1ea7663f914f4add67469c7f9e3e4` | A+ 配套 |
| mt7996e.ko | `e3915b8cfc57bdca5e4a7e1ba2676a79` | A+ + `force_rate` debugfs |

## 替换

```sh
cd /lib/modules/6.6.73
cp -f mt76.ko mt76.ko.bak
cp -f mt76-connac-lib.ko mt76-connac-lib.ko.bak
cp -f mt7996e.ko mt7996e.ko.bak
# 上传本目录三件套后覆盖
sync
reboot
```

## 节点

- `/sys/kernel/debug/ieee80211/phy0/mt76/sta_weight`：读 `MAC weight tokens`，写 `MAC weight`；
- `/sys/kernel/debug/ieee80211/phy0/mt76/force_rate`：写 `he0` 或任意内容启用固定速率（当前 table 35=6M），重启恢复。

## 注意

- 三件套 ABI 绑定，不能只替换其中一个；
- `force_rate` 会置 `MT_TXD3_BA_DISABLE`，关闭聚合；
- HE-MCS0 仍待自定义 table index。
