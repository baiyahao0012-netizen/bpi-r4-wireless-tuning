# Six-clip L2 matrix with the buffered shim sender.
# Each clip: start receiver -> send full clip via GStreamer + l2_rtp_send_buf -> collect stats.
$ErrorActionPreference = "Continue"
$key = "C:/Users/15732/.ssh/id_ed25519_pi_rtc"
$pi = "bai@192.168.240.153"
$py = "python"
$recv = "_work_final\rtc_over_mac\l2_rtp_decode_reorder.py"
$sshOpts = @("-i", $key, "-o", "BatchMode=yes", "-o", "IdentitiesOnly=yes", "-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=8")

$clips = @(
    @("1080p24_1_sintel_trailer_52s.mp4", 52, "1080p24_1"),
    @("1080p24_2_caminandes_90s.mp4", 90, "1080p24_2"),
    @("1080p25_3_bbb_trailer_33s.mp4", 33, "1080p25_3"),
    @("1080p30_1_artemis_origins_85s.mp4", 85, "1080p30_1"),
    @("1080p30_2_artemis_avatar_76s.mp4", 76, "1080p30_2"),
    @("1080p30_3_artemis_recap_90s.mp4", 90, "1080p30_3")
)

Write-Output "clip,src_seconds,packets,dup,bad,seq_gaps,timestamps,frames,sender_total"
foreach ($c in $clips) {
    $file = $c[0]; $dur = [int]$c[1]; $name = $c[2]
    $secs = $dur + 16
    $out = Join-Path $env:TEMP ("l2mat_" + $name + ".h264")
    $log = Join-Path $env:TEMP ("l2mat_" + $name + ".txt")
    $err = $log + ".err"
    $p = Start-Process -FilePath $py -ArgumentList @($recv, "--seconds", "$secs", "--out", $out) -RedirectStandardOutput $log -RedirectStandardError $err -PassThru -NoNewWindow
    Start-Sleep -Seconds 3
    $remote = "export LC_ALL=C; F=/home/bai/rtc_test/testset_1080p/$file; echo 12345678 | sudo -S python3 /home/bai/rtc_test/l2_rtp_send_buf.py > /tmp/send_$name.log 2>&1 & sleep 2; timeout 200 gst-launch-1.0 -q -e filesrc location=`$F ! qtdemux ! h264parse ! rtph264pay config-interval=1 pt=96 mtu=1200 ! udpsink host=127.0.0.1 port=5004 sync=true; echo gst_done; sleep 8; tail -n 1 /tmp/send_$name.log"
    $sendOut = (& ssh @sshOpts $pi $remote 2>&1 | Out-String)
    $p.WaitForExit()
    $line = ""
    if (Test-Path $log) { $line = (Get-Content $log | Where-Object { $_ -match "^packets " } | Select-Object -First 1) }
    $total = "NA"
    if ($sendOut -match "total (\d+)") { $total = $Matches[1] }
    $csv = "NA"
    if ($line) {
        $m = [regex]::Matches($line, "(\w+) (\S+)")
        $h = @{}
        foreach ($x in $m) { $h[$x.Groups[1].Value] = $x.Groups[2].Value }
        $csv = "$name,$dur,$($h['packets']),$($h['dup']),$($h['bad']),$($h['seq_gaps']),$($h['timestamps']),$($h['frames']),$total"
    } else {
        $csv = "$name,$dur,NA,NA,NA,NA,NA,NA,$total"
    }
    Write-Output $csv
    Write-Output ("raw_" + $name + ": " + $line)
    if (Test-Path $out) { Remove-Item $out -Force -ErrorAction SilentlyContinue }
}
Write-Output "MATRIX_DONE"
