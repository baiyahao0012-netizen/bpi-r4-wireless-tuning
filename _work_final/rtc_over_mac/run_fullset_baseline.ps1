$ErrorActionPreference = 'Continue'
$gst = 'C:\gstreamer\PFiles64\gstreamer\1.0\msvc_x86_64\bin\gst-launch-1.0.exe'
$key = Join-Path $env:USERPROFILE '.ssh\id_ed25519_pi_rtc'
$pi = 'bai@192.168.240.153'
$work = 'C:\Users\15732'
$results = @()

$clips = @(
  @{ tag='24_1'; file='1080p24_1_sintel_trailer_52s.mp4'; frames=1253; dur=52.21 },
  @{ tag='24_2'; file='1080p24_2_caminandes_90s.mp4'; frames=2161; dur=90.04 },
  @{ tag='25_3'; file='1080p25_3_bbb_trailer_33s.mp4'; frames=812; dur=32.48 },
  @{ tag='30_1'; file='1080p30_1_artemis_origins_85s.mp4'; frames=2560; dur=85.33 },
  @{ tag='30_2'; file='1080p30_2_artemis_avatar_76s.mp4'; frames=2273; dur=75.77 },
  @{ tag='30_3'; file='1080p30_3_artemis_recap_90s.mp4'; frames=2702; dur=90.07 }
)

foreach ($c in $clips) {
  $out = "C:/Users/15732/gst_full_$($c.tag).yuv"
  $so = "$work\gst_full_$($c.tag).out.log"
  $se = "$work\gst_full_$($c.tag).err.log"
  Remove-Item $out,$so,$se -ErrorAction SilentlyContinue

  $args = @(
    '-e',
    'udpsrc','address=192.168.240.2','port=5004','timeout=30000000000','buffer-size=8388608',
    'caps=application/x-rtp,media=video,encoding-name=H264,payload=96,clock-rate=90000',
    '!','rtpjitterbuffer','latency=200',
    '!','rtph264depay','!','h264parse','!','avdec_h264',
    '!','videoconvert','!','videoscale',
    '!','video/x-raw,format=I420,width=320,height=180',
    '!','filesink','sync=false',"location=$out"
  )
  $p = Start-Process -FilePath $gst -ArgumentList $args -RedirectStandardOutput $so -RedirectStandardError $se -PassThru -WindowStyle Hidden
  Start-Sleep -Seconds 10

  $send = & ssh -i $key -o IdentitiesOnly=yes -o BatchMode=yes $pi "/home/bai/run_send_full.sh $($c.file)" 2>&1
  $sendRc = $LASTEXITCODE
  Start-Sleep -Seconds 5
  if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
  Start-Sleep -Seconds 1

  $bytes = if (Test-Path $out) { (Get-Item $out).Length } else { 0 }
  $got = [math]::Floor($bytes / 86400)
  $pct = if ($c.frames -gt 0) { [math]::Round(100.0 * $got / $c.frames, 3) } else { 0 }
  $row = [pscustomobject]@{
    clip = $c.file; source_frames = $c.frames; decoded_frames = $got
    frame_pct = $pct; bytes = $bytes; sender_rc = $sendRc
    duration_s = $c.dur
  }
  $results += $row
  $row | Format-List | Out-String | Write-Output
}

$results | Export-Csv -NoTypeInformation -Encoding UTF8 -Path "$work\fullset_baseline.csv"
$results | Format-Table -AutoSize | Out-String | Write-Output
