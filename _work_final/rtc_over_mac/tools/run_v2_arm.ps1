param(
  [string]$Mode = "fifo",
  [double]$Rate = 10,
  [double]$Bulk = 30,
  [double]$Seconds = 10,
  [int]$Capacity = 200,
  [int]$MinPerFlow = 20,
  [bool]$Pacing = $true,
  [string]$Tag = "arm",
  [int]$MsgBase = 0
)
$ErrorActionPreference = "Continue"
$dir = "C:\Users\15732\AppData\Local\Temp\l2ai"
$out = "$env:TEMP\v2_$Tag.json"
$log = "$env:TEMP\v2_$Tag_srv.log"
$pace = if ($Pacing) { "--pacing" } else { "--no-pacing" }
$srv = Start-Process -FilePath (Get-Command python).Source `
  -ArgumentList @("$dir\l2_ai_server.py", "--mode", $Mode, "--seconds", ($Seconds + 8),
                  "--rate-mbps", $Rate, "--bulk-mbps", $Bulk,
                  "--capacity", $Capacity, "--min-per-flow", $MinPerFlow,
                  $pace, "--out", $out, "--csv", "$env:TEMP\v2_$Tag_srv.csv") `
  -WorkingDirectory $dir -PassThru -WindowStyle Hidden -RedirectStandardOutput $log -RedirectStandardError "$log.err"
Start-Sleep -Seconds 3
$key = "C:/Users/15732/.ssh/id_ed25519_pi_rtc"
$clientOut = "$env:TEMP\v2_$Tag_cli.json"
& ssh -i $key -o BatchMode=yes -o ConnectTimeout=8 bai@192.168.240.153 "cd /tmp && echo 12345678 | sudo -S python3 l2_ai_client.py --dst-mac 40:c2:ba:52:70:95 --seconds $Seconds --msg-base $MsgBase --out /tmp/v2_$Tag.json 2>/dev/null; cat /tmp/v2_$Tag.json" 2>&1 | Select-Object -Last 2
Wait-Process -Id $srv.Id -Timeout 30 -ErrorAction SilentlyContinue
"--- server($Tag) ---"
if (Test-Path $out) { Get-Content $out } else { "NO_SERVER_RESULT"; Get-Content $log -Tail 8 -ErrorAction SilentlyContinue }
