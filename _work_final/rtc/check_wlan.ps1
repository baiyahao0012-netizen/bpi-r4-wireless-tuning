Start-Sleep -Seconds 3
"=== 网卡 ==="
Get-NetAdapter | Select-Object Name, InterfaceDescription, Status, LinkSpeed | Format-Table -AutoSize | Out-String -Width 100
"=== 无线接口 ==="
netsh wlan show interfaces | Select-String -Pattern "Name|State|SSID|Channel|Receive rate|Transmit rate|Signal"
