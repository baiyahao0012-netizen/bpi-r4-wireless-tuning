RTC over WiFi —— 接收端（台式机）部署包
==========================================

一、安装依赖（只做一次）

  1) Python 3.10 或更高版本
     若未安装：https://www.python.org/downloads/
     安装时务必勾选 "Add Python to PATH"

  2) Npcap（必需，抓包用）
     https://npcap.com/#download
     安装时勾选：
       [x] Install Npcap in WinPcap API-compatible Mode
     装完需要重启（或至少重插网卡）

  3) Python 包
     在命令行执行：
       pip install av numpy sounddevice

二、确认网卡名称（只做一次）

  python list_nics.py

  会列出所有可用网卡，例如：
      [0] \Device\NPF_{...}  : Realtek 8852CE WiFi 6E PCI-E NIC
      [1] \Device\NPF_{...}  : Realtek PCIe GbE Family Controller

  无线网卡用于**接收数据**，有线网卡用于**发送反馈**。

三、运行接收端

  命令里 --iface / --fb-iface 填网卡名称的**一段子串**即可（比如 8852、GbE）。

  【实时视频通话模式】弹出窗口看画面，同时从音箱听声音：

  python receiver.py --transport l2 ^
      --iface 8812BU ^
      --fb 1 --fb-iface 2.5GbE ^
      --fb-dst 40-C2-BA-52-70-95 ^
      --fb-src a4-0C-66-1A-D5-8B ^
      --seconds 120 ^
      --show 1

  【录制模式】不弹窗，把收到的视频存成 mp4：

  python receiver.py --transport l2 ^
      --iface 8812BU ^
      --fb 1 --fb-iface 2.5GbE ^
      --fb-dst 40-C2-BA-52-70-95 ^
      --fb-src a4-0C-66-1A-D5-8B ^
      --seconds 60 ^
      --mp4 out.mp4

  两种可以同时用（--show 1 --mp4 out.mp4）。窗口里按 Esc 或直接关窗口不会中断收流。

  参数说明：
    --iface 8852          在无线网卡上抓 RTC2 数据帧
    --fb                  启用反馈
    --fb-iface GbE        反馈帧从有线网卡发出（无线网卡无法注入）
    --fb-dst              发送端（笔记本有线）的 MAC
    --fb-src              本机有线网卡的 MAC
    --seconds 30          运行时长，要比发送端长几秒
    --mp4 out.mp4         把收到的视频存成文件

  看不到画面时可以加 --verbose 看详细日志。

四、正常输出长这样

  receiver transport=l2 on ...   jitter_buffer=on [40..200 ms]
  feedback -> 40-C2-BA-52-70-95 every 50 ms x3
  RESULT video ok=250 lost=0 frame_loss=0.00% decoded=249 ...
  one-way latency ms: p50=9.8 p95=29.4 ...
  audio ok=420 lost=0 ...
  A/V sync skew ms: p50=16.2 p95=29.5

五、常见问题

  1) 报 "No device found matching ..."
     网卡名子串写错了，跑 list_nics.py 重新看。

  2) ok=0 / chunks=0
     说明没抓到包。检查：
       - 发送端是否已经在发
       - --iface 是不是指向无线网卡
       - 无线是否连的是 BPI-R4-5G

  3) 有画面但卡顿
     看 jitter buffer 的 D 值和 video under 计数。

  4) 反馈发不出去
     确认 --fb-iface 指向有线网卡，且 --fb-dst 是发送端的有线 MAC。
