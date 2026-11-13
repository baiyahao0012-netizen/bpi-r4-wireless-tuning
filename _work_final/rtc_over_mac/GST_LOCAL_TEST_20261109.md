# GStreamer 媒体层本地功能测试

日期：2026-11-09  
设备：Raspberry Pi 5（RPI-5），GStreamer 1.26.2  
素材：`1080p30_1_artemis_origins_85s.mp4`（1080p30，85.33 s，H.264 + AAC）  
测试位置：Pi 本地；视频 RTP 通过 `udpsink host=127.0.0.1` + Python RTP probe，未经过 Wi-Fi。

## 结果

| # | 测试 | 结果 |
|---|---|---|
| 1 | H.264 解码（85 s，`avdec_h264 ! fakesink`） | rc=0，耗时 12 s |
| 2 | H.264 RTP 打包（`rtph264pay`） | rc=0 |
| 3 | AAC → Opus RTP（`avdec_aac → opusenc → rtpopuspay`） | rc=0 |
| 4 | 视频 RTP 本地 UDP + RTP 头 probe | 5933 包，7.14 MB payload，seq gap=0，1 个 SSRC，PT=96 |
| 5 | 音频 RTP 本地 UDP + RTP 头 probe | 344 包，55.4 KB payload，seq gap=0，1 个 SSRC，PT=111 |
| 6 | 汇总 | PASS=5，FAIL=0 |

`video_udp_rc=124` / `audio_udp_rc=124` 是 `timeout` 主动结束发送进程的返回码，不是失败；probe 已收到有效 RTP 包。

## 结论

- GStreamer 媒体层在 Pi 本地可用；
- H.264 解码、H.264 RTP 打包、AAC→Opus RTP 均正常；
- 本地 UDP 上的 RTP 头、SSRC、PT、序号连续；
- 尚未验证：真实 Wi-Fi 上行、10/15/20 Mbps、SRTP 解密、RTCP/jitter/A-V sync、丢包恢复。

## 复现

```bash
cd /home/bai/rtc_test
./test_gst_local.sh
```

当前共享终端：`tmux attach -t rtc`。
