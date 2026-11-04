$log = "D:\Desktop\AI 辅助对话\_work_final\rtc\powersave.log"
function W($s) { $s | Out-File -FilePath $log -Append -Encoding utf8 }
W "=== BEFORE ==="
Get-NetAdapterAdvancedProperty -Name "WLAN" | Where-Object {$_.DisplayName -match "省电|Random"} | Format-Table DisplayName,DisplayValue -AutoSize | Out-String | ForEach-Object { W $_ }
try { Set-NetAdapterAdvancedProperty -Name "WLAN" -DisplayName "空闲省电" -DisplayValue "禁用" -NoRestart -ErrorAction Stop; W "idle-ps: OK" } catch { W "idle-ps FAIL: $($_.Exception.Message)" }
try { Set-NetAdapterAdvancedProperty -Name "WLAN" -DisplayName "MAC Randomization" -DisplayValue "Disabled" -NoRestart -ErrorAction Stop; W "macrand: OK" } catch { W "macrand FAIL: $($_.Exception.Message)" }
W "=== AFTER ==="
Get-NetAdapterAdvancedProperty -Name "WLAN" | Where-Object {$_.DisplayName -match "省电|Random"} | Format-Table DisplayName,DisplayValue -AutoSize | Out-String | ForEach-Object { W $_ }
W "done"
