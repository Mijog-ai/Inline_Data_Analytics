# Installs Inline Data Analytics on this PC from the shared folder: unpacks the current version into the user's own
# program folder (no admin rights), keeps the user's presets, adds Start-menu and desktop shortcuts and an entry
# under Windows "Apps" to uninstall it, remembers where the shared folder is (for updates), and starts the app.
# Started by "InlineDataAnalytics installieren.cmd" in the shared folder, and re-run by launcher.ps1 when a newer
# version is published. Shows a progress window and, at the end, a message saying plainly whether it worked.
# Log: %TEMP%\InlineDataAnalytics-install.log.
# Layout: %LOCALAPPDATA%\Programs\InlineDataAnalytics\ app-<version>\ (one folder per version), presets\ (kept across
# updates), update-folder.txt, launcher.ps1, uninstall.ps1.
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$share = Split-Path -Parent $MyInvocation.MyCommand.Path
$target = Join-Path $env:LOCALAPPDATA 'Programs\InlineDataAnalytics'
$log = Join-Path $env:TEMP 'InlineDataAnalytics-install.log'
$exeName = 'InlineDataAnalytics.exe'
function Log([string]$m) { Add-Content -LiteralPath $log -Value "$(Get-Date -Format o) $m" }
function AppRunning { Get-Process -Name 'InlineDataAnalytics' -ErrorAction SilentlyContinue | Where-Object { $_.Path -and $_.Path.StartsWith($target, [StringComparison]::OrdinalIgnoreCase) } }

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.IO.Compression.FileSystem
$form = New-Object System.Windows.Forms.Form
$form.Text = 'Inline Data Analytics'
$form.Size = New-Object System.Drawing.Size(460, 150)
$form.StartPosition = 'CenterScreen'
$form.FormBorderStyle = 'FixedDialog'
$form.ControlBox = $false
$form.TopMost = $true
$label = New-Object System.Windows.Forms.Label
$label.Location = New-Object System.Drawing.Point(20, 18)
$label.Size = New-Object System.Drawing.Size(410, 40)
$label.Font = New-Object System.Drawing.Font('Segoe UI', 10)
$form.Controls.Add($label)
$bar = New-Object System.Windows.Forms.ProgressBar
$bar.Location = New-Object System.Drawing.Point(20, 64)
$bar.Size = New-Object System.Drawing.Size(410, 22)
$form.Controls.Add($bar)
function Show([string]$text, [int]$percent) {
  $label.Text = $text
  $bar.Value = [Math]::Max(0, [Math]::Min(100, $percent))
  [System.Windows.Forms.Application]::DoEvents()
}
$form.Show()

try {
  Log "install from $share into $target"
  $latest = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $share 'inlinedataanalytics-latest.json') | ConvertFrom-Json
  $version = [string]$latest.version
  Show "Inline Data Analytics $version wird geprüft …`nInline Data Analytics $version is being checked …" 2
  $zipPath = Join-Path $share $latest.file
  $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $zipPath).Hash.ToLower()
  if ($latest.sha256 -and $hash -ne ([string]$latest.sha256).ToLower()) { throw "Die Datei $($latest.file) ist beschädigt (SHA-256 stimmt nicht). / The file $($latest.file) is corrupted (SHA-256 mismatch)." }

  Show "Inline Data Analytics wird geschlossen …`nInline Data Analytics is being closed …" 5
  AppRunning | Stop-Process -Force
  for ($i = 0; $i -lt 30 -and (AppRunning); $i++) { Start-Sleep -Milliseconds 500; [System.Windows.Forms.Application]::DoEvents() }
  if (AppRunning) { throw 'Inline Data Analytics läuft noch und konnte nicht beendet werden. / Inline Data Analytics is still running and could not be closed.' }

  # Each version in its own folder app-<version>\: unpacked file by file (with the percent) into app-<version>.partial\,
  # which becomes app-<version>\ only when complete.
  New-Item -ItemType Directory -Force -Path $target | Out-Null
  $dest = Join-Path $target "app-$version"
  $partial = "$dest.partial"
  if (Test-Path $partial) { Remove-Item -LiteralPath $partial -Recurse -Force }
  $zip = [System.IO.Compression.ZipFile]::OpenRead($zipPath)
  try {
    $total = ($zip.Entries | Measure-Object -Property Length -Sum).Sum
    if (-not $total) { $total = 1 }
    $done = 0; $lastP = -1
    foreach ($e in $zip.Entries) {
      $out = Join-Path $partial ($e.FullName -replace '/', '\')
      if ($e.FullName.EndsWith('/')) { New-Item -ItemType Directory -Force -Path $out | Out-Null; continue }
      New-Item -ItemType Directory -Force -Path ([System.IO.Path]::GetDirectoryName($out)) | Out-Null
      [System.IO.Compression.ZipFileExtensions]::ExtractToFile($e, $out, $true)
      $done += $e.Length
      $p = 5 + [int](80 * $done / $total)
      if ($p -ne $lastP) { $lastP = $p; Show "Inline Data Analytics $version wird installiert … $p %`nInline Data Analytics $version is being installed … $p %" $p }
    }
  } finally { $zip.Dispose() }
  if (-not (Test-Path (Join-Path $partial $exeName))) { throw "$exeName fehlt im Paket. / $exeName missing from the package." }
  if (Test-Path $dest) { Remove-Item -LiteralPath $dest -Recurse -Force }
  Rename-Item -LiteralPath $partial -NewName (Split-Path -Leaf $dest)

  # Presets are stored beside the exe. Keep them in a shared target\presets\ folder and expose them to the new
  # version via a directory junction, so they survive updates even though old version folders are deleted.
  Show "Einstellungen werden übernommen …`nCarrying over settings …" 88
  $presetStore = Join-Path $target 'presets'
  $newPresets = Join-Path $dest 'presets'
  if (-not (Test-Path $presetStore)) {
    # Seed from this version's bundled presets, or from the previous install's presets, if any.
    $seed = $null
    if (Test-Path $newPresets) { $seed = $newPresets }
    else { $seed = Get-ChildItem -LiteralPath $target -Directory -Filter 'app-*' -ErrorAction SilentlyContinue | Where-Object { $_.FullName -ne $dest -and (Test-Path (Join-Path $_.FullName 'presets')) } | Select-Object -First 1 | ForEach-Object { Join-Path $_.FullName 'presets' } }
    New-Item -ItemType Directory -Force -Path $presetStore | Out-Null
    if ($seed -and (Test-Path $seed)) { Copy-Item -LiteralPath (Join-Path $seed '*') -Destination $presetStore -Recurse -Force -ErrorAction SilentlyContinue }
  }
  if (Test-Path $newPresets) { Remove-Item -LiteralPath $newPresets -Recurse -Force }
  cmd.exe /c mklink /J "`"$newPresets`"" "`"$presetStore`"" | Out-Null

  Show "Alte Versionen werden entfernt …`nRemoving old versions …" 92
  # Everything else in the program folder goes, except the kept items (this version, the presets store, the
  # folder-level marker files). Compare by leaf name so path-form differences never delete the fresh install.
  $keepNames = @((Split-Path -Leaf $dest), 'presets', 'update-folder.txt', 'launcher.ps1', 'uninstall.ps1')
  Get-ChildItem -LiteralPath $target -Force | Where-Object { $keepNames -notcontains $_.Name } | ForEach-Object {
    Remove-Item -LiteralPath $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
  }
  Set-Content -LiteralPath (Join-Path $target 'update-folder.txt') -Value $share -Encoding UTF8
  Copy-Item -LiteralPath (Join-Path $share 'uninstall.ps1') -Destination (Join-Path $target 'uninstall.ps1') -Force
  if (Test-Path (Join-Path $share 'launcher.ps1')) {
    Copy-Item -LiteralPath (Join-Path $share 'launcher.ps1') -Destination (Join-Path $target 'launcher.ps1') -Force
  }

  Show "Verknüpfungen werden angelegt …`nCreating shortcuts …" 95
  $exe = Join-Path $dest $exeName
  $launcher = Join-Path $target 'launcher.ps1'
  $shell = New-Object -ComObject WScript.Shell
  foreach ($dir in @([Environment]::GetFolderPath('Programs'), [Environment]::GetFolderPath('Desktop'))) {
    $lnk = $shell.CreateShortcut((Join-Path $dir 'Inline Data Analytics.lnk'))
    if (Test-Path $launcher) {
      # Shortcut runs the launcher (checks for a newer version, then starts the app). Icon stays the app's.
      $lnk.TargetPath = (Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe')
      $lnk.Arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$launcher`""
    } else {
      $lnk.TargetPath = $exe
    }
    $lnk.WorkingDirectory = $dest
    $lnk.IconLocation = "$exe,0"
    $lnk.Description = 'Inline Data Analytics'
    $lnk.Save()
  }

  # Windows "Apps" › Inline Data Analytics › Deinstallieren.
  $key = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\InlineDataAnalytics'
  New-Item -Path $key -Force | Out-Null
  Set-ItemProperty -Path $key -Name DisplayName -Value 'Inline Data Analytics'
  Set-ItemProperty -Path $key -Name DisplayVersion -Value $version
  Set-ItemProperty -Path $key -Name Publisher -Value 'InLine Hydraulik GmbH'
  Set-ItemProperty -Path $key -Name DisplayIcon -Value $exe
  Set-ItemProperty -Path $key -Name InstallLocation -Value $target
  Set-ItemProperty -Path $key -Name UninstallString -Value ("powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"" + (Join-Path $target 'uninstall.ps1') + "`"")
  Set-ItemProperty -Path $key -Name NoModify -Value 1 -Type DWord
  Set-ItemProperty -Path $key -Name NoRepair -Value 1 -Type DWord
  Log "installed $version"
  Show "Inline Data Analytics $version ist installiert.`nInline Data Analytics $version is installed." 100
  $form.Close()
  [System.Windows.Forms.MessageBox]::Show("Inline Data Analytics $version ist installiert und startet jetzt.`n`nInline Data Analytics $version is installed and starts now.", 'Inline Data Analytics', 'OK', 'Information') | Out-Null
  Start-Process -FilePath $exe -WorkingDirectory $dest
} catch {
  Log "FAILED: $($_.Exception.Message)"
  $form.Close()
  [System.Windows.Forms.MessageBox]::Show("Inline Data Analytics konnte nicht installiert werden:`n$($_.Exception.Message)`n`nProtokoll / log: $log", 'Inline Data Analytics', 'OK', 'Error') | Out-Null
}
