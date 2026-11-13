$ErrorActionPreference = 'Continue'
$py = (Get-Command python).Source
$scriptPath = 'C:\Users\15732\l2_rtp_decode_reorder.py'
$key = Join-Path $env:USERPROFILE '.ssh\id_ed25519_pi_rtc'
$pi = 'bai@192.168.240.153'
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
  $out = "C:/Users/15732/l2_$($c.tag).h264"
  $so = "C:\Users\15732\l2_$($c.tag).out.log"
  $se = "C:\Users\15732\l2_$($c.tag).err.log"
  Remove-Item ($out -replace '/','\'),$so,$se -ErrorAction SilentlyContinue

  $sec = [int]($c.dur + 15)
  $args = @($scriptPath, '--seconds', $sec, '--out', $out)
  $p = Start-Process -FilePath $py -ArgumentList $args -RedirectStandardOutput $so -RedirectStandardError $se -PassThru -WindowStyle Hidden
  Start-Sleep -Seconds 3

  $send = & ssh -i $key -o IdentitiesOnly=yes -o BatchMode=yes $pi "/home/bai/rtc_test/run_l2_file.sh $($c.file)" 2>&1
  $sendRc = $LASTEXITCODE
  $p.WaitForExit(180000) | Out-Null
  Start-Sleep -Seconds 1

  $txt = Get-Content $so -ErrorAction SilentlyContinue | Out-String
  $frames = 0; $packets = 0; $gaps = 0; $crc = 0; $dup = 0
  if ($txt -match 'frames (\d+)') { $frames = [int]$Matches[1] }
  if ($txt -match 'packets (\d+)') { $packets = [int]$Matches[1] }
  if ($txt -match 'seq_gaps (\d+)') { $gaps = [int]$Matches[1] }
  if ($txt -match 'bad (\d+)') { $crc = [int]$Matches[1] }
  if ($txt -match 'dup (\d+)') { $dup = [int]$Matches[1] }
  $pct = [math]::Round(100.0 * $frames / $c.frames, 3)
  $row = [pscustomobject]@{
    clip = $c.file; source_frames = $c.frames; decoded_frames = $frames;
    frame_pct = $pct; l2_packets = $packets; seq_gaps = $gaps; crc_bad = $crc; dup = $dup;
    sender_rc = $sendRc; duration_s = $c.dur
  }
  $results += $row
  $row | Format-List | Out-String | Write-Output
}

$results | Export-Csv -NoTypeInformation -Encoding UTF8 -Path 'C:\Users\15732\l2_fullset.csv'
$results | Format-Table -AutoSize | Out-String | Write-Output
