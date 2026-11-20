# Removes Inline Data Analytics from this PC (Windows "Apps" › Inline Data Analytics › Deinstallieren): the program
# folder (including the kept presets), the shortcuts, the "Apps" entry, and the app's own QSettings.
# The app keeps its settings in the registry (HKCU\Software\Inline\Inline Data Analytics via QSettings), not in
# %APPDATA%, so there is nothing to remove under %APPDATA%.
$ErrorActionPreference = 'SilentlyContinue'
$target = Join-Path $env:LOCALAPPDATA 'Programs\InlineDataAnalytics'
Get-Process -Name 'InlineDataAnalytics' | Where-Object { $_.Path -like "$target*" } | Stop-Process -Force
Start-Sleep -Milliseconds 800
foreach ($dir in @([Environment]::GetFolderPath('Programs'), [Environment]::GetFolderPath('Desktop'))) {
  Remove-Item -LiteralPath (Join-Path $dir 'Inline Data Analytics.lnk') -Force
}
Remove-Item -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\InlineDataAnalytics' -Recurse -Force
# The app's own settings (QSettings, NativeFormat = registry).
Remove-Item -Path 'HKCU:\Software\Inline\Inline Data Analytics' -Recurse -Force
# The folder last: this script runs from inside it. (The presets junction is removed with rmdir; rmdir /s on a
# junction deletes the link, not the store's real contents elsewhere — but here the store IS inside $target, so it
# goes with the folder, which is the intended full uninstall.)
Start-Process -FilePath 'cmd.exe' -ArgumentList "/c timeout /t 2 >nul & rmdir /s /q `"$target`"" -WindowStyle Hidden
