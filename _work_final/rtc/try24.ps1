"=== 可见的 BPI 网络 ==="
$o = netsh wlan show networks
$o.Split([char]10) | Select-String -Pattern "SSID.*BPI|身份验证|加密" | Out-String -Width 70
"=== 尝试连接 BPI-R4 ==="
netsh wlan connect name="BPI-R4" ssid="BPI-R4" interface="WLAN 2" 2>&1 | Out-String
Start-Sleep -Seconds 10
Get-NetAdapter -Name "WLAN 2" | Select-Object Name, Status, LinkSpeed | Format-Table -AutoSize | Out-String
