---
name: verify-app
description: Verify Music Theory Master works end-to-end — run the test suite, launch the GUI, and exercise the adaptive/lesson flows. Use after any change, before building a release, or when investigating "app closes/crashes" reports.
---

# Verifying the app

## 1. Test suite (headless, ~2 min)
```powershell
python -m pytest tests -q
```
Watch the **exit code**, not just the dots: exit `9`/`-1073740791` (0xC0000409)
with passing dots = a native crash (historically: fluidsynth instances leaked
past `engine.close()`, or PyQt slot exceptions without `@guard`). Re-run the
GUI files individually to localize:
`tests/test_lessons.py tests/test_features_gui.py tests/test_gui_smoke.py`.

## 2. Live launch check
```powershell
$p = Start-Process python -ArgumentList "main.py" -PassThru -WindowStyle Minimized
Start-Sleep 12
if ($p.HasExited) { "CRASHED: $($p.ExitCode)" } else { (Get-Process -Id $p.Id).MainWindowTitle; Stop-Process -Id $p.Id }
```
Crash log: `%APPDATA%\MusicTheoryMaster\logs\app.log` (rotating; every guarded
exception and the excepthook write here — read it after any incident).

## 3. Flow-level checks (what the GUI tests simulate)
- Fresh profile → Learn: first skill must show its **lesson pages**, then the exercise.
- Answer 10 items → summary card → Continue → next lesson starts (no dead-end).
- Placement: finishes all 3 domains, results card appears, dashboard levels match.
- Aural exercises auto-play; Replay button must not error with audio missing.
- Practice: difficulty label rises on correct answers, falls on wrong.

## 4. Placement calibration (after touching adaptive/)
Run the simulation: sweep true ability 0.5–9.5 against
`PlacementTest`, assert mean estimate ≤ true level and overestimation(+1.0)
stays rare — `tests/test_adaptive.py::test_placement_resists_overestimation`
codifies the floor case. Conservative placement is a product requirement.
