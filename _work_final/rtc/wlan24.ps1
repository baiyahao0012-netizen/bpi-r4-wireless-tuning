"=== profiles ==="
netsh wlan show profiles | Select-String -Pattern "BPI" | Out-String -Width 70
"=== visible BPI ==="
netsh wlan show networks | Select-String -Pattern "SSID.*BPI" | Out-String -Width 70
"=== 8812BU state ==="
netsh wlan show interfaces | Select-String -Pattern "Name|State|SSID|Receive rate" | Out-String -Width 70
