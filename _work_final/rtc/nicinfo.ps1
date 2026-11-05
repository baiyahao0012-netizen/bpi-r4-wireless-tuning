$ErrorActionPreference = "SilentlyContinue"
"=== 网卡 ==="
Get-NetAdapter | Sort-Object Name |
    Select-Object Name, InterfaceDescription, Status, LinkSpeed, MacAddress |
    Format-Table -AutoSize | Out-String -Width 120
"=== IPv4 ==="
Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.IPAddress -notlike "127.*" } |
    Select-Object InterfaceAlias, IPAddress, PrefixLength |
    Format-Table -AutoSize | Out-String -Width 80
"=== 无线连接 ==="
netsh wlan show interfaces | Select-String -Pattern "Name|SSID|Channel|Receive rate|Signal"
"=== 默认路由 ==="
Get-NetRoute -DestinationPrefix "0.0.0.0/0" | Select-Object InterfaceAlias, NextHop, InterfaceMetric | Format-Table -AutoSize | Out-String -Width 80
