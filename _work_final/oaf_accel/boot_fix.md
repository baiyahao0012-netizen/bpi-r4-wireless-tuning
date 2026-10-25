# 串口启动需要回车的修复（2026-10-25）

## 现象

重启后 U-Boot 自动启动，Linux 启动完成后停在：

```text
Please press Enter to activate this console.
```

必须串口发一次回车才出现 `OpenWrt login:`。

## 原因

不是 U-Boot。U-Boot 日志显示：

```text
Hit any key to stop autoboot: 3 2 1
MMC read ...
Starting kernel ...
```

已经自动进入内核。

OpenWrt `/etc/inittab` 原来是：

```text
::askconsole:/usr/libexec/login.sh
```

`askconsole` 会等待一次回车才激活串口控制台；系统/网络/SSH 实际已经启动。

## 修复

板端 `/etc/inittab` 改为：

```text
ttyS0::respawn:/bin/login
```

备份：`/etc/inittab.bak`。

说明：板端没有 `/sbin/getty`，所以直接用 `/bin/login`（BusyBox login），仍然需要用户名/密码，不会自动登录 root。

重启验证：串口直接出现 `OpenWrt login:`，不再要求回车。

## 恢复

```sh
cp /etc/inittab.bak /etc/inittab
reboot
```
