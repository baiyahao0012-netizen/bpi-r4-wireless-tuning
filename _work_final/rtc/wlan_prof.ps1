"=== WLAN 2 的配置文件 ==="
netsh wlan show profiles interface="WLAN 2" | Out-String -Width 90
"=== 所有配置文件 ==="
netsh wlan show profiles | Select-String -Pattern "所有用户配置文件|All User Profile|BPI" | Out-String -Width 90
"=== 从 AX201 导出 BPI-R4-5G 配置 ==="
$key = "clear"
netsh wlan export profile name="BPI-R4-5G" folder="C:\rtc" key=$key interface="WLAN" 2>&1 | Out-String -Width 100
Get-ChildItem C:\rtc\*.xml -ErrorAction SilentlyContinue | Select-Object Name | Out-String
