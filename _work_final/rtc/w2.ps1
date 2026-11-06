$o = netsh wlan show interfaces
$lines = $o.Split([char]10) | ForEach-Object { $_.TrimEnd([char]13) }
$blk = @()
foreach ($l in $lines) {
  if ($l -match "^\s*名称\s*:") { $blk = @($l) }
  elseif ($blk.Count -gt 0) { $blk += $l }
  if ($blk.Count -gt 0 -and $l -match "SSID\s*:" -and $blk[0] -notmatch "WLAN 2") { }
}
"=== 只显示 WLAN 2 ==="
$show = $false
foreach ($l in $lines) {
  if ($l -match "WLAN 2") { $show = $true }
  elseif ($l -match "^\s*名称\s*:" -and $show) { break }
  if ($show) { $l }
}
"=== 8812BU 适配器状态 ==="
Get-NetAdapter -Name "WLAN 2" | Select-Object Name, Status, LinkSpeed | Format-Table -AutoSize | Out-String
