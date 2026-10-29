# BPI-R4 WiFi 主备切换：Bai 优先，DianGroup103 兜底

## 行为

- 当前已连接 Bai：不动作；
- 未连接 Bai，且能扫描到 Bai：切回 Bai；
- 未连接 Bai，且扫描不到 Bai：切到 DianGroup103；
- 当前在 DianGroup103，Bai 重新出现：自动切回 Bai。

## 配置

    PRIMARY=Bai
    PKEY=12345678
    FALLBACK=DianGroup103
    FKEY=DianGroup2002

注意：实际扫描到的 SSID 是 DianGroup103，没有下划线。

## 文件

    /root/wifi_failover.sh
    /etc/init.d/wifi-failover
    /etc/rc.d/S99wifi-failover

## 实测

### 兜底网络

手动切到 DianGroup103：

    SSID: DianGroup103
    inet 192.168.3.48/24
    ping 223.5.5.5: 0% packet loss

### 自动切回 Bai

手动切到 DianGroup103 后，脚本检测到 Bai 可见：

    logread:
    user.notice wifi-failover: switch to Bai

最终：

    SSID: Bai
    inet 192.168.13.209/24

### 当前状态

    SSID: Bai
    signal: -26 dBm
    5G AP: BPI-R4-5G
    管理: 以太网 192.168.240.2

## 注意

- 切换使用 wifi reload，会短暂重启 WiFi；5G AP 可能短暂断开；
- 脚本每 30 秒检查一次；在 fallback 时会扫描 Bai；
- 密码以 root 权限保存在 /root/wifi_failover.sh；
- 如果实际 SSID 是 DianGroup_103（带下划线），需要改脚本中的 FALLBACK。

## 停止/恢复

    /etc/init.d/wifi-failover stop
    /etc/init.d/wifi-failover disable

恢复固定连 Bai：

    uci set wireless.sta0.ssid='Bai'
    uci set wireless.sta0.key='12345678'
    uci commit wireless
    wifi reload
