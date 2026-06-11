---
name: build-exe
description: Build and verify the MusicTheoryMaster.exe Windows executable with PyInstaller. Use when shipping a release, after dependency changes, or when the build deadlocks/fails.
---

# Building the executable

```powershell
./build.ps1     # → dist/MusicTheoryMaster.exe (~150–250 MB onefile)
```

The script: fetches the SoundFont if missing → regenerates the icon →
runs PyInstaller with the work tree in `$env:TEMP` (NOT in the repo —
the repo is OneDrive-synced and cloud sync chokes on thousands of temp files).

## Verify after building
```powershell
$p = Start-Process dist\MusicTheoryMaster.exe -PassThru; Start-Sleep 20
if ($p.HasExited) { "FAILED: exited $($p.ExitCode)" } else { "OK"; Stop-Process -Id $p.Id }
```
Onefile self-extracts on launch, so first paint takes several seconds — wait
≥20s before declaring failure. Also sanity-check the size (a sudden drop means
data files were lost; a jump means an exclude regressed).

## Known landmines (documented in music_theory.spec — read it first)
- **Never** use `collect_all('music21')` → isolated-import deadlock. Only its data files are collected, corpus trimmed.
- **Never** force-import `fluidsynth` in the spec (DLL access violation in PyInstaller's probe). The guarded runtime import is enough.
- `torch`/`tensorflow`/`jax` must remain in `excludes` — torch's DLL load deadlocks dependency analysis.
- If the build hangs >10 min, it's almost always a new heavyweight package being probed: add it to `excludes`.
- App must keep working without music21/fluidsynth at runtime (pure-python fallbacks exist) — don't break that when adding imports.
