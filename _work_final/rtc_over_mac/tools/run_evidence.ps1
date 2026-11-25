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
  [double]$RateMbps = 10,
  [double]$SrvRespTimeout = 80,
  [double]$CliAckTimeout = 60,
  [double]$CliRespTimeout = 120,
  [string]$Evidence = "D:\Desktop\AI 辅助对话\_work_final\rtc_over_mac\evidence\feedback_evidence_20261125"
)
$dir = "C:\Users\15732\AppData\Local\Temp\l2ai"
$key = "C:/Users/15732/.ssh/id_ed25519_pi_rtc"
$tools = "D:\Desktop\AI 辅助对话\_work_final\rtc_over_mac\tools"
foreach ($f in @("l2_ai_common.py", "l2_ai_sched.py", "l2_ai_server.py", "l2_ai_client.py")) {
  Copy-Item "$tools\$f" $dir -Force
}
New-Item -ItemType Directory -Force $Evidence | Out-Null
$srvOut = "$env:TEMP\ev_${Tag}_srv.json"
$srvLedger = "$env:TEMP\ev_${Tag}_srv.jsonl"
$cliLedger = "/tmp/ev_${Tag}_cli.jsonl"
$sargs = @("--mode", "fifo", "--seconds", ($Seconds + 8), "--bulk-mbps", 0,
           "--client-mac", $ClientMac, "--capacity", $Capacity,
           "--rate-mbps", $RateMbps, "--resp-timeout-ms", $SrvRespTimeout,
           "--ledger", $srvLedger, "--out", $srvOut)
if ($DropResp)   { $sargs += @("--drop-resp", $DropResp) }
if ($FailResp)   { $sargs += @("--fail-resp", $FailResp) }
if ($DropAckReq) { $sargs += @("--drop-ack-req", $DropAckReq) }
$srv = Start-Process -FilePath (Get-Command python).Source -ArgumentList (@("$dir\l2_ai_server.py") + $sargs) `
  -WorkingDirectory $dir -PassThru -WindowStyle Hidden `
  -RedirectStandardOutput "$env:TEMP\ev_${Tag}_srv.log" -RedirectStandardError "$env:TEMP\ev_${Tag}_srv.err"
Start-Sleep -Seconds 3
$clientArgs = "--dst-mac 40:c2:ba:52:70:95 --seconds $Seconds --iface $Iface --src-mac $SrcMac --msg-base $MsgBase --ack-timeout-ms $CliAckTimeout --resp-timeout-ms $CliRespTimeout --ledger $cliLedger --out /tmp/ev_${Tag}_cli.json"
if ($DropReq)     { $clientArgs += " --drop-req $DropReq" }
if ($FailReq)     { $clientArgs += " --fail-req $FailReq" }
if ($DropAckResp) { $clientArgs += " --drop-ack-resp $DropAckResp" }
$cli = & ssh -i $key -o BatchMode=yes -o ConnectTimeout=8 bai@192.168.240.153 `
  "cd /tmp && echo 12345678 | sudo -S python3 l2_ai_client.py $clientArgs 2>/dev/null >/dev/null; cat /tmp/ev_${Tag}_cli.json" 2>&1 | Select-Object -Last 1
Wait-Process -Id $srv.Id -Timeout 30 -ErrorAction SilentlyContinue
Copy-Item $srvLedger "$Evidence\${Tag}_srv.jsonl" -Force -ErrorAction SilentlyContinue
& scp -i $key -o IdentitiesOnly=yes "bai@192.168.240.153:$cliLedger" "$Evidence\${Tag}_cli.jsonl" 2>&1 | Out-Null
"$Tag CLIENT: $cli"
if (Test-Path $srvOut) { "$Tag SERVER: $(Get-Content $srvOut)" } else { "$Tag NO_SERVER" }
