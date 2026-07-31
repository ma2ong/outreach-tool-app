# Register a per-user scheduled task that runs the server at logon, windowless.
# Re-running replaces the existing task. Removal: uninstall_autostart.bat
param([Parameter(Mandatory = $true)][string]$Root)

$ErrorActionPreference = "Stop"
$TaskName = "Maxcolor Outreach Tool"
$backend = Join-Path $Root "backend"

$python = (Get-Command python).Source
$pythonw = $python -replace "python\.exe$", "pythonw.exe"
if (-not (Test-Path $pythonw)) { $pythonw = $python }

# run_server.py redirects stdout/stderr to a log file first: pythonw has no
# console, and uvicorn dies the moment it tries to log without one.
$runner = Join-Path $Root "scripts\run_server.py"
$action = New-ScheduledTaskAction -Execute $pythonw `
  -Argument "`"$runner`"" -WorkingDirectory $backend

$trigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
$trigger.Delay = "PT20S"   # let the desktop settle before booting the server

# Keep it alive: retry on crash, never time out, survive going on battery.
$settings = New-ScheduledTaskSettingsSet `
  -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
  -RestartInterval (New-TimeSpan -Minutes 1) -RestartCount 3 `
  -ExecutionTimeLimit (New-TimeSpan -Seconds 0) `
  -MultipleInstances IgnoreNew -StartWhenAvailable

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
  -Settings $settings -Description "Runs the Maxcolor outreach tool in the background at logon." -Force | Out-Null

# Public entrance. Only registered when the tunnel has been set up, so a plain
# local install stays local. The tunnel starts after the app: it would only
# serve 502s otherwise.
$vbs = Join-Path $Root "scripts\run_tunnel.vbs"
if (Test-Path "$env:USERPROFILE\.cloudflared\config.yml") {
  $tunnelTrigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
  $tunnelTrigger.Delay = "PT40S"
  Register-ScheduledTask -TaskName "$TaskName Tunnel" `
    -Action (New-ScheduledTaskAction -Execute "wscript.exe" -Argument "`"$vbs`"") `
    -Trigger $tunnelTrigger -Settings $settings `
    -Description "Publishes the outreach tool at crm.mcvisualled.com." -Force | Out-Null
  $tunnelNote = "公网地址 https://crm.mcvisualled.com 也会自动上线。"
} else {
  $tunnelNote = "（未配置隧道，仅本机可用。）"
}

# Desktop shortcut to the dashboard, so there is still one obvious thing to click.
$lnk = Join-Path ([Environment]::GetFolderPath("Desktop")) "客户开发系统.url"
"[InternetShortcut]`r`nURL=http://127.0.0.1:8000`r`n" | Set-Content -Path $lnk -Encoding ascii

Write-Output ""
Write-Output "[OK] 已设置开机自动运行。"
Write-Output "     开机登录 20 秒后服务自动在后台启动，没有黑窗口。"
Write-Output "     $tunnelNote"
Write-Output "     桌面已放好快捷方式：客户开发系统"
Write-Output ""
Write-Output "     现在就想启动一次：Start-ScheduledTask -TaskName '$TaskName'"
Write-Output "     取消开机自启：双击 uninstall_autostart.bat"
