# Update-on-launch: the Start-menu / desktop shortcut runs this. It compares the installed version with the shared
# folder's inlinedataanalytics-latest.json and, if a newer one is published, re-runs install.ps1 (which updates and
# starts the app) before anything else. If the shared folder is unreachable, or anything goes wrong, it simply starts
# the version already installed — the app never fails to open because of the update check.
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$target = Join-Path $env:LOCALAPPDATA 'Programs\InlineDataAnalytics'
$exeName = 'InlineDataAnalytics.exe'
$log = Join-Path $env:TEMP 'InlineDataAnalytics-launch.log'
function Log([string]$m) { try { Add-Content -LiteralPath $log -Value "$(Get-Date -Format o) $m" } catch {} }

function Latest-InstalledDir {
  Get-ChildItem -LiteralPath $target -Directory -Filter 'app-*' -ErrorAction SilentlyContinue |
    Sort-Object { try { [version]($_.Name -replace '^app-', '') } catch { [version]'0.0.0' } } |
    Select-Object -Last 1
}
function Start-Installed {
  $d = Latest-InstalledDir
  if (-not $d) { Log 'no installed version found'; return }
  $exe = Join-Path $d.FullName $exeName
  if (Test-Path $exe) { Log "launching $exe"; Start-Process -FilePath $exe -WorkingDirectory $d.FullName }
  else { Log "exe missing: $exe" }
}

try {
  $installedDir = Latest-InstalledDir
  $installed = if ($installedDir) { [version]($installedDir.Name -replace '^app-', '') } else { [version]'0.0.0' }

  $shareFile = Join-Path $target 'update-folder.txt'
  $share = if (Test-Path $shareFile) { (Get-Content -Raw -LiteralPath $shareFile).Trim() } else { $null }
  $manifest = if ($share) { Join-Path $share 'inlinedataanalytics-latest.json' } else { $null }

  if ($share -and (Test-Path $manifest)) {
    $latest = Get-Content -Raw -Encoding UTF8 -LiteralPath $manifest | ConvertFrom-Json
    $avail = [version]([string]$latest.version)
    if ($avail -gt $installed) {
      $installPs1 = Join-Path $share 'install.ps1'
      if (Test-Path $installPs1) {
        Log "updating $installed -> $avail; running $installPs1"
        # install.ps1 unpacks the new version and starts the app itself.
        Start-Process -FilePath (Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe') `
          -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-WindowStyle', 'Hidden', '-File', "`"$installPs1`"")
        return
      }
    }
    Log "up to date (installed $installed, available $avail)"
  } else {
    Log "shared folder unreachable or no manifest; launching installed version"
  }
} catch {
  Log "update check failed: $($_.Exception.Message)"
}
Start-Installed
