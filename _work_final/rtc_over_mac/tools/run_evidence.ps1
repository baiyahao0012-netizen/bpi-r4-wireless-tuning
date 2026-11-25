param(
  [string]$Tag = "E1",
  [string]$DropResp = "",
  [string]$FailResp = "",
  [string]$DropAckReq = "",
  [string]$DropReq = "",
  [string]$FailReq = "",
  [string]$DropAckResp = "",
  [int]$MsgBase = 100000,
  [double]$Seconds = 6,
  [string]$Iface = "wlan0",
  [string]$SrcMac = "90:de:80:1c:6a:7a",
  [string]$ClientMac = "90:de:80:1c:6a:7a",
  [int]$Capacity = 200,
  [int]$BufferDepth = 64,
  [double]$RateMbps = 10,
  [string]$Mode = "fifo",
  [double]$AiInterval = 100,
  [switch]$FastTx,
  [double]$BulkDelay = 0,
  [double]$BulkMbps = 0,
  [double]$SrvRespTimeout = 80,
  [double]$CliAckTimeout = 60,
  [double]$CliRespTimeout = 120,
  [string]$Evidence = "C:\Users\15732\AppData\Local\Temp\evidence"
)
$dir = "C:\Users\15732\AppData\Local\Temp\l2ai"
$key = "C:/Users/15732/.ssh/id_ed25519_pi_rtc"
New-Item -ItemType Directory -Force $Evidence | Out-Null
$srvOut = "$env:TEMP\ev_${Tag}_srv.json"
$srvLedger = "$env:TEMP\ev_${Tag}_srv.jsonl"
$cliLedger = "/tmp/ev_${Tag}_cli.jsonl"
# never reuse a stale ledger: a missing/old file must not be mistaken for a run
Remove-Item $srvLedger -ErrorAction SilentlyContinue
Remove-Item "$Evidence\${Tag}_srv.jsonl" -ErrorAction SilentlyContinue
Remove-Item "$Evidence\${Tag}_cli.jsonl" -ErrorAction SilentlyContinue
& ssh -i $key -o BatchMode=yes -o ConnectTimeout=8 bai@192.168.240.153 "rm -f $cliLedger" 2>&1 | Out-Null
$sargs = @("--mode", $Mode, "--seconds", ($Seconds + 8), "--bulk-mbps", $BulkMbps, "--bulk-delay", $BulkDelay,
           "--client-mac", $ClientMac, "--capacity", $Capacity,
           "--buffer-depth", $BufferDepth, "--rate-mbps", $RateMbps,
           "--resp-timeout-ms", $SrvRespTimeout, "--ledger", $srvLedger, "--out", $srvOut)
if ($FastTx)     { $sargs += @("--fast-tx") }
if ($DropResp)   { $sargs += @("--drop-resp", $DropResp) }
if ($FailResp)   { $sargs += @("--fail-resp", $FailResp) }
if ($DropAckReq) { $sargs += @("--drop-ack-req", $DropAckReq) }
$cov = "bash /tmp/covariates.sh"
& ssh -i $key -o BatchMode=yes -o ConnectTimeout=8 bai@192.168.240.153 $cov 2>&1 | Out-File "$Evidence\${Tag}_cov_before.json" -Encoding utf8
$srv = Start-Process -FilePath (Get-Command python).Source -ArgumentList (@("$dir\l2_ai_server.py") + $sargs) `
  -WorkingDirectory $dir -PassThru -WindowStyle Hidden `
  -RedirectStandardOutput "$env:TEMP\ev_${Tag}_srv.log" -RedirectStandardError "$env:TEMP\ev_${Tag}_srv.err"
Start-Sleep -Seconds 3
$clientArgs = "--dst-mac 40:c2:ba:52:70:95 --seconds $Seconds --iface $Iface --src-mac $SrcMac --msg-base $MsgBase --ai-interval-ms $AiInterval --ack-timeout-ms $CliAckTimeout --resp-timeout-ms $CliRespTimeout --ledger $cliLedger --out /tmp/ev_${Tag}_cli.json"
if ($DropReq)     { $clientArgs += " --drop-req $DropReq" }
if ($FailReq)     { $clientArgs += " --fail-req $FailReq" }
if ($DropAckResp) { $clientArgs += " --drop-ack-resp $DropAckResp" }
$cli = & ssh -i $key -o BatchMode=yes -o ConnectTimeout=8 bai@192.168.240.153 `
  "cd /tmp && echo 12345678 | sudo -S python3 l2_ai_client.py $clientArgs 2>/dev/null >/dev/null; cat /tmp/ev_${Tag}_cli.json" 2>&1 | Select-Object -Last 1
Wait-Process -Id $srv.Id -Timeout 30 -ErrorAction SilentlyContinue
Copy-Item $srvLedger "$Evidence\${Tag}_srv.jsonl" -Force -ErrorAction SilentlyContinue
& ssh -i $key -o BatchMode=yes -o ConnectTimeout=8 bai@192.168.240.153 $cov 2>&1 | Out-File "$Evidence\${Tag}_cov_after.json" -Encoding utf8
& scp -i $key -o IdentitiesOnly=yes "bai@192.168.240.153:$cliLedger" "$Evidence\${Tag}_cli.jsonl" 2>&1 | Out-Null
"$Tag CLIENT: $cli"
if (Test-Path $srvOut) { "$Tag SERVER: $(Get-Content $srvOut)" } else { "$Tag NO_SERVER"; Get-Content "$env:TEMP\ev_${Tag}_srv.err" -Tail 5 }
