param(
  [double]$AckDrop = 0.4,
  [double]$RespDrop = 0.4,
  [string]$Tag = "fb",
  [int]$MsgBase = 0,
  [double]$Seconds = 10
)
$dir = "C:\Users\15732\AppData\Local\Temp\l2ai"
$key = "C:/Users/15732/.ssh/id_ed25519_pi_rtc"
Copy-Item "D:\Desktop\AI 辅助对话\_work_final\rtc_over_mac\tools\l2_ai_server.py" $dir -Force
Copy-Item "D:\Desktop\AI 辅助对话\_work_final\rtc_over_mac\tools\l2_ai_sched.py" $dir -Force
Copy-Item "D:\Desktop\AI 辅助对话\_work_final\rtc_over_mac\tools\l2_ai_common.py" $dir -Force
$out = "$env:TEMP\fb_$Tag.json"
$csv = "$env:TEMP\fb_$Tag_srv.csv"
$log = "$env:TEMP\fb_$Tag_srv.log"
$srv = Start-Process -FilePath (Get-Command python).Source `
  -ArgumentList @("$dir\l2_ai_server.py", "--mode", "fifo", "--seconds", ($Seconds + 8),
                  "--bulk-mbps", 0, "--ack-drop", $AckDrop, "--resp-drop", $RespDrop,
                  "--resp-timeout-ms", 80, "--out", $out, "--csv", $csv) `
  -WorkingDirectory $dir -PassThru -WindowStyle Hidden `
  -RedirectStandardOutput $log -RedirectStandardError "$log.err"
Start-Sleep -Seconds 3
$cli = & ssh -i $key -o BatchMode=yes -o ConnectTimeout=8 bai@192.168.240.153 `
  "cd /tmp && echo 12345678 | sudo -S python3 l2_ai_client.py --dst-mac 40:c2:ba:52:70:95 --seconds $Seconds --msg-base $MsgBase --resp-timeout-ms 120 --out /tmp/fb_$Tag.json 2>/dev/null >/dev/null; cat /tmp/fb_$Tag.json" 2>&1 | Select-Object -Last 1
Wait-Process -Id $srv.Id -Timeout 30 -ErrorAction SilentlyContinue
"CLIENT: $cli"
if (Test-Path $out) { "SERVER: $(Get-Content $out)" } else { "NO_SERVER"; Get-Content $log -Tail 6 }
