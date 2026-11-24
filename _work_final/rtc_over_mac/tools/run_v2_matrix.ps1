$ErrorActionPreference = "Continue"
$dir = "C:\Users\15732\AppData\Local\Temp\l2ai"
$key = "C:/Users/15732/.ssh/id_ed25519_pi_rtc"
$rows = @()
$base = 100000
foreach ($pacing in @($true, $false)) {
  foreach ($mode in @("fifo", "quota", "ai-first", "both")) {
    $tag = "$mode" + $(if ($pacing) { "_pace" } else { "_nopace" })
    $out = "$env:TEMP\v2_$tag.json"
    $log = "$env:TEMP\v2_$tag_srv.log"
    $paceArg = if ($pacing) { "--pacing" } else { "--no-pacing" }
    $srv = Start-Process -FilePath (Get-Command python).Source `
      -ArgumentList @("$dir\l2_ai_server.py", "--mode", $mode, "--seconds", 18,
                      "--rate-mbps", 10, "--bulk-mbps", 30, "--capacity", 200,
                      "--min-per-flow", 20, $paceArg, "--out", $out,
                      "--csv", "$env:TEMP\v2_$tag_srv.csv") `
      -WorkingDirectory $dir -PassThru -WindowStyle Hidden `
      -RedirectStandardOutput $log -RedirectStandardError "$log.err"
    Start-Sleep -Seconds 3
    $cli = & ssh -i $key -o BatchMode=yes -o ConnectTimeout=8 bai@192.168.240.153 "cd /tmp && echo 12345678 | sudo -S python3 l2_ai_client.py --dst-mac 40:c2:ba:52:70:95 --seconds 10 --msg-base $base --out /tmp/v2_$tag.json 2>/dev/null >/dev/null; cat /tmp/v2_$tag.json" 2>&1 | Select-Object -Last 1
    Wait-Process -Id $srv.Id -Timeout 25 -ErrorAction SilentlyContinue
    $c = $null; $s = $null
    try { $c = ($cli -replace '^RESULT ', '') | ConvertFrom-Json } catch {}
    try { if (Test-Path $out) { $s = ((Get-Content $out) -replace '^RESULT ', '') | ConvertFrom-Json } } catch {}
    $rows += [pscustomobject]@{
      arm = $tag; mode = $mode; pacing = $pacing
      delivered = $c.delivered; requests = $c.requests
      ttft_p50 = $c.ttft_p50_us; ttft_p95 = $c.ttft_p95_us
      resends = $c.resends
      evictions = $s.evictions; rejections = $s.rejections
      max_depth = $s.max_queue_depth; bulk_sent = $s.bulk_sent
    }
    "$tag done: p50=$($c.ttft_p50_us) delivery=$($c.delivered)/$($c.requests) depth=$($s.max_queue_depth) evict=$($s.evictions)"
    $base += 100000
  }
}
$rows | Export-Csv "$env:TEMP\v2_matrix.csv" -NoTypeInformation -Encoding UTF8
"MATRIX_SAVED $env:TEMP\v2_matrix.csv"
