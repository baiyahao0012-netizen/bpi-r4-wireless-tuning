$d = Get-PnpDevice -Class Net | Where-Object { $_.FriendlyName -match "8812BU" }
$d | Format-List Status, Problem, ProblemDescription, InstanceId, Present, ConfigManagerErrorCode | Out-String -Width 110
"=== 是否有 NetAdapter 关联 ==="
Get-NetAdapter -IncludeHidden | Where-Object { $_.InterfaceDescription -match "8812" } | Format-Table Name,Status -AutoSize | Out-String
"=== AX201 状态 ==="
netsh wlan show interfaces | Select-String -Pattern "Name|State|SSID|信号|Signal"
