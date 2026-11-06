$ErrorActionPreference = "Continue"
netsh wlan export profile name="BPI-R4-5G" folder="C:\rtc" key=clear interface="WLAN 2" | Out-Null
$f = Get-ChildItem "C:\rtc\*BPI-R4-5G.xml" | Select-Object -First 1
"exported: " + $f.FullName
$xml = Get-Content $f.FullName -Raw
$xml = $xml.Replace("BPI-R4-5G", "BPI-R4")
Set-Content -Path "C:\rtc\BPI-R4.xml" -Value $xml -Encoding UTF8
netsh wlan add profile filename="C:\rtc\BPI-R4.xml" user=all 2>&1 | Out-String
netsh wlan connect name="BPI-R4" ssid="BPI-R4" interface="WLAN 2" 2>&1 | Out-String
Start-Sleep -Seconds 9
netsh wlan show interfaces | Select-String -Pattern "Name|State|SSID|Receive rate|Signal" | Out-String -Width 70
