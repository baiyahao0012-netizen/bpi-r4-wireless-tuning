try {
    Enable-NetAdapter -Name "WLAN 2" -Confirm:$false -ErrorAction Stop
    "enable ok"
} catch {
    "Enable-NetAdapter failed: " + $_.Exception.Message
    netsh interface set interface name="WLAN 2" admin=enable 2>&1 | Out-String
}
Start-Sleep -Seconds 3
Get-NetAdapter | Select-Object Name, Status, LinkSpeed | Format-Table -AutoSize | Out-String -Width 70
