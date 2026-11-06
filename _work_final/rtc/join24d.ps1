netsh wlan scan interface="WLAN 2" 2>&1 | Out-String
Start-Sleep -Seconds 6
netsh wlan connect name="BPI-R4" ssid="BPI-R4" interface="WLAN 2" 2>&1 | Out-String
Start-Sleep -Seconds 9
netsh wlan show interfaces | Select-String -Pattern "Name|State|SSID" | Out-String -Width 70
