"=== adapters ==="
Get-NetAdapter | Select-Object Name, InterfaceDescription, Status, LinkSpeed, MacAddress | Format-Table -AutoSize | Out-String -Width 110
"=== wireless ==="
netsh wlan show interfaces | Select-String -Pattern "Name|State|SSID|AP BSSID|Receive rate|Signal" | Out-String -Width 70
"=== IPv4 ==="
Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" } | Select-Object InterfaceAlias, IPAddress | Format-Table -AutoSize | Out-String
