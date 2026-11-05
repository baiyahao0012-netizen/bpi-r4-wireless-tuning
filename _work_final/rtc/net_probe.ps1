param([string]$Action = "valid")

$name = "WLAN"
switch ($Action) {
    "toac" {
        Set-NetAdapterAdvancedProperty -Name $name -RegistryKeyword IEEE11nMode -DisplayValue "3. 802.11ac"
        Restart-NetAdapter -Name $name
        "now = " + (Get-NetAdapter -Name $name | Get-NetAdapterAdvancedProperty -RegistryKeyword IEEE11nMode).DisplayValue
    }
    "toax" {
        Set-NetAdapterAdvancedProperty -Name $name -RegistryKeyword IEEE11nMode -DisplayValue "4. 802.11ax"
        Restart-NetAdapter -Name $name
        "now = " + (Get-NetAdapter -Name $name | Get-NetAdapterAdvancedProperty -RegistryKeyword IEEE11nMode).DisplayValue
    }
    "nosmps" {
        Set-NetAdapterAdvancedProperty -Name $name -RegistryKeyword MIMOPowerSaveMode -DisplayValue "无 SMPS"
        Restart-NetAdapter -Name $name
        "now = " + (Get-NetAdapter -Name $name | Get-NetAdapterAdvancedProperty -RegistryKeyword MIMOPowerSaveMode).DisplayValue
    }
    "show" {
        "mode   = " + (Get-NetAdapter -Name $name | Get-NetAdapterAdvancedProperty -RegistryKeyword IEEE11nMode).DisplayValue
        "smps   = " + (Get-NetAdapter -Name $name | Get-NetAdapterAdvancedProperty -RegistryKeyword MIMOPowerSaveMode).DisplayValue
        netsh wlan show interfaces | Select-String -Pattern "Receive rate|Transmit rate|Radio type|State"
    }
}
