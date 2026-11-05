netsh wlan scan interface="WLAN 2" 2>&1 | Out-String
Start-Sleep -Seconds 5
"=== WLAN 2 看到的网络 ==="
netsh wlan show networks interface="WLAN 2" | Select-String -Pattern "SSID" | Out-String -Width 80
"=== 连接 ==="
netsh wlan connect name="BPI-R4-5G" ssid="BPI-R4-5G" interface="WLAN 2" 2>&1 | Out-String
Start-Sleep -Seconds 8
netsh wlan show interfaces | Select-String -Pattern "Name|State|SSID|Channel|Receive rate|Transmit rate|Signal" | Out-String -Width 80
