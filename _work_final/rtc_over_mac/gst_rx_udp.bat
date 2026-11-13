@echo off
set GST=C:\gstreamer\PFiles64\gstreamer\1.0\msvc_x86_64\bin
"%GST%\gst-launch-1.0.exe" -e ^
  udpsrc address=192.168.240.2 port=5004 timeout=5000000 ^
  caps="application/x-rtp,media=video,encoding-name=H264,payload=96,clock-rate=90000" ^
  ! rtpjitterbuffer latency=100 ^
  ! rtph264depay ! h264parse ! avdec_h264 ^
  ! videoconvert ! videoscale ^
  ! video/x-raw,format=I420,width=320,height=180 ^
  ! filesink location="D:\Desktop\AI 辅助对话\_work_final\rtc_over_mac\gst_rx.yuv"
