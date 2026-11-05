param([string]$Action = "status", [string]$Name = "WLAN 2")
switch ($Action) {
    "disable" {
        Disable-NetAdapter -Name $Name -Confirm:$false -ErrorAction Stop
        "disabled: $Name"
    }
    "enable" {
        Enable-NetAdapter -Name $Name -Confirm:$false -ErrorAction Stop
        "enabled: $Name"
    }
    "status" {
        Get-NetAdapter | Select-Object Name, Status, LinkSpeed | Format-Table -AutoSize | Out-String -Width 70
    }
}
