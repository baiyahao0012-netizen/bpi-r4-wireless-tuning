$xml = Get-Content "C:\rtc\WLAN 2-BPI-R4-5G.xml" -Raw
$xml = $xml.Replace("BPI-R4-5G", "BPI-R4")
$xml = $xml.Replace("4250492D52342D3547", "4250492D5234")
Set-Content -Path "C:\rtc\BPI-R4.xml" -Value $xml -Encoding UTF8
$hex = [regex]::Match($xml, "<hex>([0-9A-Fa-f]+)</hex>").Groups[1].Value
"hex now: $hex"
netsh wlan delete profile name="BPI-R4" 2>&1 | Out-Null
netsh wlan add profile filename="C:\rtc\BPI-R4.xml" user=all 2>&1 | Out-String
netsh wlan connect name="BPI-R4" ssid="BPI-R4" interface="WLAN 2" 2>&1 | Out-String
Start-Sleep -Seconds 10
netsh wlan show interfaces | Select-String -Pattern "Name|State|SSID|Receive rate" | Out-String -Width 70
