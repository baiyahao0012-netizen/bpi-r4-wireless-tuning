# 模块与工具清单（2026-10-22）

| 文件 | md5 | 用途 |
|---|---|---|
| mac80211.wdrr.ko | 49f2aca91f3228adcd83b205f5338d61 | WDRR 私有调度器（fq_weight） |
| mt7996e_edca_eeprom.ko | bb9f774c3fcf5aa44c675cad8f9ddf4c | EDCA debugfs 回读 + 强制默认 EEPROM |
| mt7996e_ampdu_eeprom.ko | 226812a1edc1159026d3305273b1c496 | A-MPDU agg_win_cap + 强制默认 EEPROM |
| mt76.mcs.ko | 98950b1412ffb9c5fc110c04022462ed | force_mcs debugfs（mt76.ko） |
| mt76-connac-lib.mcs.ko | 750d1abde6decb9afdbdcf439820548e | sta_rec RX MCS mask 覆盖 |
| mt7996e.mcs.ko | 0ac042a8fbfe4b39ba08c4f2999132be | MCS 驱动 + 强制默认 EEPROM |
| edca_set | — | aarch64 静态 nl80211 EDCA 下发工具 |

## 切换方法

三套 mt7996e 构建互斥，按实验切换：

```sh
# EDCA
cp /root/mt7996e_edca_eeprom.ko /lib/modules/6.6.73/mt7996e.ko && sync && reboot

# A-MPDU
cp /root/mt7996e_ampdu_eeprom.ko /lib/modules/6.6.73/mt7996e.ko && sync && reboot

# MCS（需同时替换 mt76/connac）
cp /root/mt76.mcs.ko /lib/modules/6.6.73/mt76.ko
cp /root/mt76-connac-lib.mcs.ko /lib/modules/6.6.73/mt76-connac-lib.ko
cp /root/mt7996e.mcs.ko /lib/modules/6.6.73/mt7996e.ko
sync && reboot
```

WDRR 的 mac80211.ko 与上述 mt76 构建相互独立，可同时使用。
