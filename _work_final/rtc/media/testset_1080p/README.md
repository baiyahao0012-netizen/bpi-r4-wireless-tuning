# 1080P 带音频测试素材集（24–30 fps，各三部）

给 RTC over MAC 第一阶段「喂文件源」用：STA 无线上行到 AP，1080P + 带音频，单条 15 s–2 min。
所有参数均为 **ffmpeg 实测**，不是文件名或网站声明值。

## 一、文件清单

| # | 文件 | 分辨率 | 帧率 | 时长 | 视频码率 | 音频 | 体积 |
|---|---|---|---|---|---|---|---|
| 1 | `1080p24_1_sintel_trailer_52s.mp4` | 1920×1080 | **24.000** | 52.21 s | 2108 kb/s | AAC-LC 48 kHz 立体声 126 kb/s | 13.9 MB |
| 2 | `1080p24_2_caminandes_90s.mp4` | 1920×1080 | **24.000** | 90.04 s | 6767 kb/s | AAC-LC 48 kHz 立体声 125 kb/s | 76.5 MB |
| 3 | `1080p25_3_bbb_trailer_33s.mp4` | 1920×1080 | **25.000** | 33.00 s | 7162 kb/s | AAC-LC 48 kHz 5.1 428 kb/s | 29.4 MB |
| 4 | `1080p30_1_artemis_origins_85s.mp4` | 1920×1080 | **30.000** | 85.33 s | 4999 kb/s | AAC-LC 48 kHz 立体声 159 kb/s | 52.6 MB |
| 5 | `1080p30_2_artemis_avatar_76s.mp4` | 1920×1080 | **30.000** | 75.77 s | 4997 kb/s | AAC-LC 48 kHz 立体声 159 kb/s | 46.7 MB |
| 6 | `1080p30_3_artemis_recap_90s.mp4` | 1920×1080 | **30.000** | 90.07 s | 4995 kb/s | AAC-LC 48 kHz 立体声 160 kb/s | 55.7 MB |
| 7 | `anchor_1080p30_clapper_10s.mkv` | 1920×1080 | **30.000** | 10.00 s | 21 kb/s（合成信号） | Opus 48 kHz 立体声 128 kb/s | 0.17 MB |

前六条合计 274.9 MB。视频一律 H.264（High/Main profile，yuv420p，progressive），封装一律 MP4（`+faststart`，moov 在前）；第 7 条为合成锚点信号，MKV + Opus，规格见 2.1。

## 二、两组怎么用

| 组 | 帧率 | 各自的用途 |
|---|---|---|
| 24/25 组（1–3） | 24.000 / 25.000 | 模拟「胶片/PAL 节奏」的片源，帧间隔 41.67 / 40.00 ms |
| 30 组（4–6） | 30.000 | 模拟「NTSC 节奏」的片源，帧间隔 33.33 ms |

**为什么这组数字对 RTP 很干净**：RTP 时间戳时钟是 90 kHz，

- 24 fps → 每帧步长 `90000/24 = 3750`（整数）
- 25 fps → `90000/25 = 3600`（整数）
- 30 fps → `90000/30 = 3000`（整数）

三条都能整除，时间戳不会产生累积取整误差，可以直接拿它验证 RFC 3550 的 `timestamp += 90000/fps` 递推是否和抖动缓冲、RTCP SR 的 NTP/RTP 对应关系自洽。
如果换成 29.97 或 23.976，步长就变成 3003 / 3753.75 这种非整数，反而会引入额外变量——所以这六条都是**整数帧率**。

### 2.1 音画锚点素材（第 7 条，合成打板信号）

`anchor_1080p30_clapper_10s.mkv` 不是影片，是为测 A/V 同步造的合成信号：

- 每 1.000 s：**一整帧纯白**（视频锚点）+ **50 ms 的 1 kHz 短音**（音频锚点），两者同刻；共 10 对。
- H.264 High，**无 B 帧**，GOP=30（白闪对齐 I 帧，抗丢包更稳）；Opus 48 kHz 立体声 128 kb/s；MKV 封装。
- 用法：接收端检测白帧 PTS 与短音起点 PTS，差值即 A/V 同步偏差。UDP baseline 量出基准偏差，L2 再量一次，两者相减才是「换传输造成的偏差」。
- 测量分辨率：视频 ±33.3 ms（一帧），音频 ±20 ms（分析窗）；需要更细可另出 60 fps 版本。
- 生成脚本：`../make_anchor_material.py`，参数可改（时长/帧率/短音长度/码率），重跑即可复现。

## 三、码率不够怎么办（重编码到 10/15/20 Mbps）

这六条是「成品码率」（5–7 Mbps）。你的实验要打 10/15/20 Mbps，需要先重编码到目标码率再喂 RTP，否则测的是 6 Mbps 而不是 20 Mbps。

固定 GOP + CBR，音频直接拷贝：

```powershell
# 以 20 Mbps 为例；10M / 15M 改 -b:v/-maxrate/-bufsize 即可
ffmpeg -i 1080p30_1_artemis_origins_85s.mp4 `
  -c:v libx264 -preset veryfast -profile:v high -pix_fmt yuv420p `
  -x264-params "nal-hrd=cbr:force-cfr=1" `
  -b:v 20M -minrate 20M -maxrate 20M -bufsize 20M `
  -g 60 -keyint_min 60 -sc_threshold 0 `
  -c:a copy -movflags +faststart 1080p30_1_20Mbps.mp4
```

关键参数说明：

- `-g 60`：固定 GOP。**必须固定**，否则 IDR 帧位置随机，分片数、I 帧尖峰、丢包恢复时间都不可复现。
- `-sc_threshold 0`：关掉场景切换插入 I 帧，同上。
- `nal-hrd=cbr`：让码率真正贴住目标值，便于对照空口预算。
- `-c:a copy`：音频不动，避免引入第二个变量。

本机有 NVIDIA GPU，想快可以换硬件编码（同码率参数）：

```powershell
ffmpeg -i 1080p30_1_artemis_origins_85s.mp4 `
  -c:v h264_nvenc -preset p5 -rc cbr -b:v 20M -maxrate 20M -bufsize 20M `
  -g 60 -c:a copy -movflags +faststart out.mp4
```

注意：NVENC 与 x264 的码率控制曲线不同，**同一实验里不要混用**，要么全 x264 要么全 NVENC。

## 四、校验命令

```powershell
# 单条查规格（重点看 Duration、fps、Stream #0:1 是否有 Audio）
ffmpeg -hide_banner -i 1080p24_1_sintel_trailer_52s.mp4

# 抽 3 帧存盘，肉眼确认不是黑屏/花屏
ffmpeg -hide_banner -i 1080p30_2_artemis_avatar_76s.mp4 -vf "select='eq(n,0)+eq(n,300)+eq(n,1200)'" -vsync 0 chk_%02d.png
```

## 五、来源与许可

| # | 来源 | 许可 |
|---|---|---|
| 1 | `https://download.blender.org/durian/trailer/sintel_trailer-1080p.mp4`（Sintel 官方预告片，原片 24 fps，未改动） | CC BY 3.0，Blender Foundation |
| 2 | `https://download.blender.org/demo/movies/caminandes_gran_dillama.mp4.zip`（Caminandes: Gran Dillama，原片 2:26，此处截取前 90 s，流拷贝） | CC BY 4.0，Blender Foundation |
| 3 | `https://download.blender.org/peach/trailer/trailer_1080p.mov`（Big Buck Bunny 官方预告片，原片 25 fps，仅 MOV→MP4 重封装） | CC BY 3.0，Blender Foundation |
| 4 | `https://images-assets.nasa.gov/video/Artemis Origins/Artemis Origins~large.mp4` | NASA，公共领域 |
| 5 | `https://images-assets.nasa.gov/video/Artemis II Science - AVATAR Horizontal Video/…~large.mp4` | NASA，公共领域 |
| 6 | `https://images-assets.nasa.gov/video/ARTEMIS II Mission Recap_ANB_V3/…~large.mp4`（原片 3:32，此处截取前 90 s） | NASA，公共领域 |

## 六、被排除的源（别重复踩）

| 源 | 为什么不能用 |
|---|---|
| BBB 官方 1080p **30 fps** | 只有 `bbb_sunflower_1080p_30fps_normal.mp4.zip`（275 MB，10 分钟全片），无短片段直链；为一条测试片下整部片子不划算，故 30 fps 组改用 NASA |
| Tears of Steel 预告片 | 实测 **1920×800**（2.4:1 宽银幕），不是 1080p；但它是 24 fps、**55 Mbps** 的素材，将来要测「远超空口容量」的极限码率可以单独取 |
| Elephants Dream 预告片 | 实测 **960×540、MPEG-4 Part 2**，分辨率和编码都不合格 |
| Big Buck Bunny 预告片（24 fps 版） | 网上流传的 1080p 预告片实为 **25 fps PAL 版**，与「24 fps」不符；本集按实际 25 fps 归档，不冒充 24 |
| NASA 的 `~large.mp4` | 分辨率/帧率**不固定**：同批条目里既有 1920×1080/30，也有 1280×720/59.94（`Meet the Artemis Team` 甚至是 44 分钟的 720p60，1.65 GB）。必须逐条下载实测，不能看元数据就下结论（元数据描述的是 `~orig`，不是 `~large`） |
| filesamples.com | 直链 403 |
| test-videos.co.uk 的 1080p 样例 | 一律 10 s，不满足 15 s 下限 |
