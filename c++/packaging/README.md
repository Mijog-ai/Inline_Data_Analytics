# Inline Data Analytics — no-admin install & auto-update

Distribution modeled on the InFlow Electron app: one shared network folder holds the current zip plus a JSON
manifest, and each PC installs into the user's own profile (no admin rights) and self-updates on next launch.

Shared folder: `B:\Transfer\Transfer_apps\InlineDataAnalytics`
Publisher: InLine Hydraulik GmbH

## Files

| File | Role |
|------|------|
| `package.ps1` | Build Release, bundle Qt + MSVC runtime (windeployqt), zip, hash, write manifest, publish to the shared folder. Run by the developer. |
| `install.ps1` | Run on each PC from the shared folder. Unpacks into `%LOCALAPPDATA%\Programs\InlineDataAnalytics\app-<version>\`, keeps presets, makes shortcuts + an "Apps" uninstall entry, launches the app. |
| `launcher.ps1` | What the shortcuts point to. Checks the shared folder for a newer version, runs `install.ps1` if so, otherwise starts the installed app. No-ops if the folder is unreachable. |
| `uninstall.ps1` | Removes the program folder, shortcuts, the "Apps" entry, and the app's QSettings (`HKCU\Software\Inline`). |
| `InlineDataAnalytics installieren.cmd` | Double-click launcher that starts `install.ps1` hidden. |

## Version source

The single authoritative version is the [`VERSION`](../VERSION) file in the repo root (e.g. `1.0.0`).
Bump it (or pass `-Version` to `package.ps1`) before packaging a release. `package.ps1` writes it into
`inlinedataanalytics-latest.json`, and `launcher.ps1` compares it (as a `[version]`) against the installed
`app-<version>` folder to decide whether to update.

## Release a new version

```powershell
# from the c++ repo root
packaging\package.ps1 -Version 1.1.0
```

This builds Release with the MSVC2022 toolchain (vcvars64 + jom), runs `windeployqt --release --compiler-runtime`
(so the Visual C++ runtime ships next to the exe — no vc_redist, fully no-admin), zips to
`InlineDataAnalytics-<version>-win.zip`, computes SHA-256, writes `inlinedataanalytics-latest.json`, and copies the
zip + json + the four scripts into the shared folder. Use `-NoPublish` to build/zip locally without copying.

## Install on a PC

Open the shared folder and double-click **`InlineDataAnalytics installieren.cmd`**. No admin rights needed.
After that, the Start-menu / desktop shortcut updates the app automatically whenever a newer version is published.

## Notes

- Presets live beside the exe (`presets\`). Because each version gets its own folder and old ones are deleted on
  update, `install.ps1` keeps a single `presets\` store in the program root and junctions each version's `presets\`
  to it, so presets survive updates.
- QSettings uses the Windows registry (`HKCU\Software\Inline\Inline Data Analytics`), not `%APPDATA%`; `uninstall.ps1`
  removes it.
- Logs: `%TEMP%\InlineDataAnalytics-install.log`, `%TEMP%\InlineDataAnalytics-launch.log`.
