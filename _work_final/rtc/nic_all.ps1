"=== 所有网卡（含已禁用）==="
Get-NetAdapter -IncludeHidden | Select-Object Name, InterfaceDescription, Status, LinkSpeed |
    Format-Table -AutoSize | Out-String -Width 110
"=== USB 无线设备 ==="
Get-PnpDevice -Class Net | Where-Object { $_.FriendlyName -match "8812|Realtek|Wireless" } |
    Select-Object Status, FriendlyName | Format-Table -AutoSize | Out-String -Width 90
