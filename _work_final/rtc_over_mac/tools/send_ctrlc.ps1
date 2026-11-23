param([Parameter(Mandatory=$true)][int]$TargetPid)
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class ConsoleCtrl {
  [DllImport("kernel32.dll", SetLastError=true)] public static extern bool AttachConsole(uint dwProcessId);
  [DllImport("kernel32.dll", SetLastError=true)] public static extern bool FreeConsole();
  [DllImport("kernel32.dll", SetLastError=true)] public static extern bool GenerateConsoleCtrlEvent(uint dwCtrlEvent, uint dwProcessGroupId);
}
"@
$ok = $false
[ConsoleCtrl]::FreeConsole() | Out-Null
if ([ConsoleCtrl]::AttachConsole([uint32]$TargetPid)) {
  $ok = [ConsoleCtrl]::GenerateConsoleCtrlEvent(0, 0)
  Start-Sleep -Milliseconds 800
  [ConsoleCtrl]::FreeConsole() | Out-Null
}
Write-Output "ctrl_c_sent=$ok pid=$TargetPid"
