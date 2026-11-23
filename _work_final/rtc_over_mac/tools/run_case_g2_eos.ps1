$ErrorActionPreference = "Continue"
$bin = "C:\gstreamer\PFiles64\gstreamer\1.0\msvc_x86_64\bin\gst-launch-1.0.exe"
$dir = "C:/Users/15732/AppData/Local/Temp/t8r/g2"
New-Item -ItemType Directory -Force $dir | Out-Null
$clips = @("1080p24_1_sintel_trailer_52s","1080p24_2_caminandes_90s","1080p25_3_bbb_trailer_33s",
           "1080p30_1_artemis_origins_85s","1080p30_2_artemis_avatar_76s","1080p30_3_artemis_recap_90s")
$key = "C:/Users/15732/.ssh/id_ed25519_pi_rtc"
$helper = "$env:TEMP\send_ctrlc.ps1"
$vTpl = '-e rtpbin name=r rtp-profile=avpf latency=500 udpsrc port=5004 buffer-size=8388608 caps="application/x-rtp,media=video,encoding-name=H264,payload=96,clock-rate=90000" ! r.recv_rtp_sink_0 r. ! rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! videoscale ! video/x-raw,format=I420,width=320,height=180 ! filesink location=__V__ udpsrc port=5006 ! r.recv_rtcp_sink_0 r.send_rtcp_src_0 ! udpsink host=192.168.240.126 port=5005 sync=false async=false'
$aTpl = '-e rtpbin name=r rtp-profile=avpf latency=500 udpsrc port=5008 buffer-size=8388608 caps="application/x-rtp,media=audio,encoding-name=OPUS,payload=111,clock-rate=48000" ! r.recv_rtp_sink_0 r. ! rtpopusdepay ! opusdec ! audioconvert ! audioresample ! audio/x-raw,format=S16LE,channels=1,rate=48000 ! filesink location=__A__ udpsrc port=5010 ! r.recv_rtcp_sink_0 r.send_rtcp_src_0 ! udpsink host=192.168.240.126 port=5009 sync=false async=false'

"G2_START"
foreach ($c in $clips) {
  $v = "$dir/$c.yuv"; $a = "$dir/$c.pcm"
  Remove-Item $v -ErrorAction SilentlyContinue; Remove-Item $a -ErrorAction SilentlyContinue
  $vp = Start-Process -FilePath $bin -ArgumentList ($vTpl -replace "__V__", $v) -PassThru
  $ap = Start-Process -FilePath $bin -ArgumentList ($aTpl -replace "__A__", $a) -PassThru
  Start-Sleep -Seconds 2
  & ssh -i $key -o BatchMode=yes -o ConnectTimeout=8 bai@192.168.240.153 "export LC_ALL=C; export GI_TYPELIB_PATH=/home/bai/.local/gi/usr/lib/aarch64-linux-gnu/girepository-1.0; python3 /tmp/file_av_lab.py sender --file /tmp/retest_clips/${c}_10s.mp4 --seconds 12 --host 192.168.240.2 --bind-address 192.168.240.126 --video-rtp-port 5004 --video-rtcp-port 5006 --video-feedback-port 5005 --audio-rtp-port 5008 --audio-rtcp-port 5010 --audio-feedback-port 5009" 2>&1 | Out-Null
  Start-Sleep -Seconds 3
  foreach ($p in @($vp, $ap)) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $helper -TargetPid $p.Id | Out-Null
    Start-Sleep -Milliseconds 900
  }
  Start-Sleep -Seconds 2
  foreach ($p in @($vp, $ap)) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
  $vb = if (Test-Path $v) { (Get-Item $v).Length } else { 0 }
  $ab = if (Test-Path $a) { (Get-Item $a).Length } else { 0 }
  "G2_RESULT $c frames=$([math]::Floor($vb/86400)) video_bytes=$vb audio_bytes=$ab samples=$([math]::Floor($ab/2))"
}
"G2_DONE"
