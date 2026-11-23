$ErrorActionPreference = "Continue"
$bin = "C:\gstreamer\PFiles64\gstreamer\1.0\msvc_x86_64\bin\gst-launch-1.0.exe"
$dir = "C:/Users/15732/AppData/Local/Temp/t8r/tail"
New-Item -ItemType Directory -Force $dir | Out-Null
$clip = "1080p25_3_bbb_trailer_33s"
$key = "C:/Users/15732/.ssh/id_ed25519_pi_rtc"
$helper = "$env:TEMP\send_ctrlc.ps1"

function Start-Recv([string]$v, [string]$a) {
  $vArgs = '-e rtpbin name=r rtp-profile=avpf latency=500 udpsrc port=5004 buffer-size=8388608 caps="application/x-rtp,media=video,encoding-name=H264,payload=96,clock-rate=90000" ! r.recv_rtp_sink_0 r. ! rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! videoscale ! video/x-raw,format=I420,width=320,height=180 ! filesink location=' + $v + ' udpsrc port=5006 ! r.recv_rtcp_sink_0 r.send_rtcp_src_0 ! udpsink host=192.168.240.126 port=5005 sync=false async=false'
  $aArgs = '-e rtpbin name=r rtp-profile=avpf latency=500 udpsrc port=5008 buffer-size=8388608 caps="application/x-rtp,media=audio,encoding-name=OPUS,payload=111,clock-rate=48000" ! r.recv_rtp_sink_0 r. ! rtpopusdepay ! opusdec ! audioconvert ! audioresample ! audio/x-raw,format=S16LE,channels=1,rate=48000 ! filesink location=' + $a + ' udpsrc port=5010 ! r.recv_rtcp_sink_0 r.send_rtcp_src_0 ! udpsink host=192.168.240.126 port=5009 sync=false async=false'
  $vp = Start-Process -FilePath $bin -ArgumentList $vArgs -PassThru
  $ap = Start-Process -FilePath $bin -ArgumentList $aArgs -PassThru
  return @($vp, $ap)
}

function Send-Clip {
  & ssh -i $key -o BatchMode=yes -o ConnectTimeout=8 bai@192.168.240.153 "export LC_ALL=C; export GI_TYPELIB_PATH=/home/bai/.local/gi/usr/lib/aarch64-linux-gnu/girepository-1.0; python3 /tmp/file_av_lab.py sender --file /tmp/retest_clips/${clip}_10s.mp4 --seconds 12 --host 192.168.240.2 --bind-address 192.168.240.126 --video-rtp-port 5004 --video-rtcp-port 5006 --video-feedback-port 5005 --audio-rtp-port 5008 --audio-rtcp-port 5010 --audio-feedback-port 5009" 2>&1 | Out-Null
}

function Run-Variant([string]$tag, [bool]$useEos) {
  $v = "$dir/$tag.yuv"; $a = "$dir/$tag.pcm"
  Remove-Item $v -ErrorAction SilentlyContinue
  Remove-Item $a -ErrorAction SilentlyContinue
  $procs = Start-Recv $v $a
  Start-Sleep -Seconds 2
  Send-Clip
  Start-Sleep -Seconds 3
  if ($useEos) {
    foreach ($p in $procs) {
      & powershell -NoProfile -ExecutionPolicy Bypass -File $helper -TargetPid $p.Id | Out-Null
      Start-Sleep -Milliseconds 800
    }
    Start-Sleep -Seconds 2
    foreach ($p in $procs) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
  } else {
    foreach ($p in $procs) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
  }
  $vb = if (Test-Path $v) { (Get-Item $v).Length } else { 0 }
  $ab = if (Test-Path $a) { (Get-Item $a).Length } else { 0 }
  "TAIL $tag frames=$([math]::Floor($vb/86400)) video_bytes=$vb audio_bytes=$ab samples=$([math]::Floor($ab/2))"
}

Run-Variant "lat500_kill" $false
Run-Variant "lat500_eos" $true
"TAIL_DONE"


