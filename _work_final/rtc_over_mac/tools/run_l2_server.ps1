param([int]$Seconds = 10, [string]$Out = "C:\Users\15732\AppData\Local\Temp\l2ai_server.json")
$py = (Get-Command python).Source
$script = "C:\Users\15732\AppData\Local\Temp\l2ai\l2_ai_server.py"
$log = "$env:TEMP\l2ai_server.log"
Remove-Item $log -ErrorAction SilentlyContinue
Remove-Item $Out -ErrorAction SilentlyContinue
$inner = "& '$py' '$script' --seconds $Seconds --out '$Out' *> '$log'"
$p = Start-Process powershell -Verb RunAs -ArgumentList '-NoProfile','-Command',$inner -Wait -PassThru
Start-Sleep -Seconds 1
"elevated_exit=$($p.ExitCode)"
if (Test-Path $Out) { Get-Content $Out } else { "NO_OUT"; if (Test-Path $log) { Get-Content $log -Tail 20 } }

