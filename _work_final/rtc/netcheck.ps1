"=== 默认路由 ==="
Get-NetRoute -DestinationPrefix "0.0.0.0/0" | Select-Object InterfaceAlias, NextHop, InterfaceMetric | Format-Table -AutoSize | Out-String -Width 70
"=== ping 板子 ==="
ping -n 2 192.168.240.1
"=== ping 外网 ==="
ping -n 2 223.5.5.5
"=== DNS ==="
nslookup www.baidu.com 2>&1 | Select-Object -Last 4
