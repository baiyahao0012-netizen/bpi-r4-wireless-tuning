$d = Get-PnpDevice -Class Net | Where-Object { $_.FriendlyName -match "8812BU" }
"before: " + $d.Status + "  " + $d.InstanceId
if ($d.Status -ne "OK") {
    try {
        Enable-PnpDevice -InstanceId $d.InstanceId -Confirm:$false -ErrorAction Stop
        "enable requested"
    } catch {
        "enable failed: " + $_.Exception.Message
    }
}
Start-Sleep -Seconds 4
"=== 网卡 ==="
Get-NetAdapter | Select-Object Name, InterfaceDescription, Status, LinkSpeed | Format-Table -AutoSize | Out-String -Width 100
