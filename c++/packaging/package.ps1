# Builds InlineDataAnalytics (Release), bundles the Qt + MSVC runtime with windeployqt into a staging folder,
# zips it as InlineDataAnalytics-<version>-win.zip, computes the SHA-256, writes inlinedataanalytics-latest.json,
# and copies the zip + json + install/uninstall/.cmd into the shared distribution folder.
#
# Version source: the single authoritative version is the VERSION file in the repo root (..\VERSION).
# Bump it before packaging a new release. (The app's own main.cpp applicationVersion is cosmetic and not read here.)
#
# No admin rights needed anywhere: windeployqt --compiler-runtime copies the Visual C++ runtime DLLs next to the
# exe (app-local), so the end user never runs vc_redist.
#
# Usage (from a normal PowerShell, no VS prompt needed):
#   powershell -NoProfile -ExecutionPolicy Bypass -File packaging\package.ps1
#   optional: -Version 1.2.0   (overrides the VERSION file and rewrites it)
#             -NoPublish        (build + zip locally, do not copy to the shared folder)
[CmdletBinding()]
param(
  [string]$Version,
  [switch]$NoPublish
)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

# --- Paths (edit here if the toolchain moves) ---------------------------------------------------
$pkgDir   = Split-Path -Parent $MyInvocation.MyCommand.Path          # ...\c++\packaging
$repoDir  = Split-Path -Parent $pkgDir                               # ...\c++
$versionFile = Join-Path $repoDir 'VERSION'
$qtBin    = 'C:\Qt\6.11.1\msvc2022_64'
$windeploy = Join-Path $qtBin 'bin\windeployqt.exe'
$vcvars   = 'C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat'
$jom      = 'C:\Qt\Tools\QtCreator\bin\jom\jom.exe'
$cmake    = Join-Path 'C:\Qt\Tools\CMake_64\bin' 'cmake.exe'
if (-not (Test-Path $cmake)) { $cmake = 'cmake' }                    # fall back to PATH
$buildDir = Join-Path $repoDir 'build\Release_pkg'
$stageRoot = Join-Path $repoDir 'build\stage'
$share    = 'B:\Transfer\Transfer_apps\InlineDataAnalytics'
$exeName  = 'InlineDataAnalytics.exe'

function Step($m) { Write-Host "==> $m" -ForegroundColor Cyan }

# --- Version ------------------------------------------------------------------------------------
if ($Version) {
  Set-Content -LiteralPath $versionFile -Value $Version -Encoding ASCII
} else {
  if (-not (Test-Path $versionFile)) { throw "VERSION file not found at $versionFile" }
  $Version = (Get-Content -Raw -LiteralPath $versionFile).Trim()
}
if ($Version -notmatch '^\d+\.\d+\.\d+$') { throw "Version '$Version' must look like 1.2.3" }
Step "Packaging InlineDataAnalytics $Version"

foreach ($t in @($windeploy, $vcvars, $jom)) {
  if (-not (Test-Path $t)) { throw "Required tool not found: $t" }
}

# --- Configure + build Release (via a .cmd wrapper that sources vcvars64) -----------------------
Step "Configuring and building (Release)"
if (Test-Path $buildDir) { Remove-Item -LiteralPath $buildDir -Recurse -Force }
New-Item -ItemType Directory -Force -Path $buildDir | Out-Null

$buildCmd = Join-Path $env:TEMP 'ida-build.cmd'
@"
@echo off
call "$vcvars" || exit /b 1
"$cmake" -G "NMake Makefiles JOM" -DCMAKE_MAKE_PROGRAM="$jom" -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH="$qtBin" -S "$repoDir" -B "$buildDir" || exit /b 1
"$cmake" --build "$buildDir" --config Release || exit /b 1
"@ | Set-Content -LiteralPath $buildCmd -Encoding ASCII
& cmd.exe /c "`"$buildCmd`""
if ($LASTEXITCODE -ne 0) { throw "Build failed (exit $LASTEXITCODE)." }

$builtExe = Join-Path $buildDir $exeName
if (-not (Test-Path $builtExe)) { throw "Build did not produce $exeName at $builtExe" }

# --- Stage + windeployqt ------------------------------------------------------------------------
Step "Staging and running windeployqt"
$stage = Join-Path $stageRoot "InlineDataAnalytics-$Version"
if (Test-Path $stage) { Remove-Item -LiteralPath $stage -Recurse -Force }
New-Item -ItemType Directory -Force -Path $stage | Out-Null
Copy-Item -LiteralPath $builtExe -Destination (Join-Path $stage $exeName) -Force

& $windeploy --release --no-translations --dir $stage (Join-Path $stage $exeName)
if ($LASTEXITCODE -ne 0) { throw "windeployqt failed (exit $LASTEXITCODE)." }

# Bundle the Visual C++ runtime DLLs app-locally (no vc_redist, no admin). windeployqt's --compiler-runtime only
# works from a VS environment, so copy the redist CRT DLLs directly from the newest VC redist folder.
Step "Bundling Visual C++ runtime"
$vsRoot = 'C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Redist\MSVC'
$vcrt = Get-ChildItem -Path $vsRoot -Recurse -Filter 'vcruntime140.dll' -File -ErrorAction SilentlyContinue |
  Where-Object { $_.DirectoryName -match 'Microsoft\.VC\d+\.CRT$' } |
  Sort-Object FullName | Select-Object -Last 1
if (-not $vcrt) { throw "Could not find the VC redist CRT folder under $vsRoot" }
Copy-Item -Path (Join-Path $vcrt.DirectoryName '*.dll') -Destination $stage -Force
if (-not (Test-Path (Join-Path $stage 'vcruntime140.dll'))) { throw "VC runtime (vcruntime140.dll) was not bundled." }

# --- Zip ----------------------------------------------------------------------------------------
Step "Creating zip"
$zipName = "InlineDataAnalytics-$Version-win.zip"
$zipPath = Join-Path $stageRoot $zipName
if (Test-Path $zipPath) { Remove-Item -LiteralPath $zipPath -Force }
Compress-Archive -Path (Join-Path $stage '*') -DestinationPath $zipPath -CompressionLevel Optimal
$sha = (Get-FileHash -Algorithm SHA256 -LiteralPath $zipPath).Hash.ToLower()

# --- Manifest -----------------------------------------------------------------------------------
$manifest = [ordered]@{ version = $Version; file = $zipName; sha256 = $sha }
$jsonName = 'inlinedataanalytics-latest.json'
$jsonPath = Join-Path $stageRoot $jsonName
$manifest | ConvertTo-Json | Set-Content -LiteralPath $jsonPath -Encoding UTF8

Write-Host ""
Write-Host "zip:    $zipPath" -ForegroundColor Green
Write-Host "sha256: $sha" -ForegroundColor Green

# --- Publish to shared folder -------------------------------------------------------------------
if ($NoPublish) { Step "NoPublish set - not copying to $share"; return }
if (-not (Test-Path $share)) { throw "Shared folder not reachable: $share (zip + json are in $stageRoot)" }
Step "Publishing to $share"
Copy-Item -LiteralPath $zipPath  -Destination (Join-Path $share $zipName)  -Force
Copy-Item -LiteralPath $jsonPath -Destination (Join-Path $share $jsonName) -Force
foreach ($f in @('install.ps1', 'uninstall.ps1', 'launcher.ps1', 'InlineDataAnalytics installieren.cmd')) {
  Copy-Item -LiteralPath (Join-Path $pkgDir $f) -Destination (Join-Path $share $f) -Force
}
Step "Done. Published InlineDataAnalytics $Version to $share"
