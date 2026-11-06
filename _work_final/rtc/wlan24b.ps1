$out = netsh wlan show networks mode=bssid
$lines = $out.Split([char]10) | ForEach-Object { $_.TrimEnd([char]13) }
for ($i = 0; $i -lt $lines.Count; $i++) {
  if ($lines[$i] -match "SSID \d+ : BPI-R4$") {
    $end = [Math]::Min($i + 4, $lines.Count - 1)
    $lines[$i..$end] | ForEach-Object { $_.Trim() }
    "---"
  }
}
