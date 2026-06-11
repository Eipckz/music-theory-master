# Build Music Theory Master into a single Windows executable.
# Usage:  ./build.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

Write-Host "==> Ensuring audio assets are present..." -ForegroundColor Cyan
$sf = Get-ChildItem -Path (Join-Path $root "music_theory\resources\soundfonts") -Filter *.sf2 -ErrorAction SilentlyContinue
if (-not $sf) {
    Write-Host "    SoundFont not found; fetching (one-time download)..." -ForegroundColor Yellow
    python build\fetch_audio_assets.py
    if ($LASTEXITCODE -ne 0) { throw "asset download failed" }
}

Write-Host "==> Generating icon..." -ForegroundColor Cyan
python build\make_icon.py
if ($LASTEXITCODE -ne 0) { throw "icon generation failed" }

Write-Host "==> Running PyInstaller..." -ForegroundColor Cyan
# Build the work tree on a local drive. If the project lives in a OneDrive /
# cloud-synced folder, PyInstaller's thousands of temporary work files can be
# painfully slow (and the sync filter may stall them), so keep work local.
$work = Join-Path $env:TEMP "mtm_build_work"
$dist = Join-Path $root "dist"
python -m PyInstaller --noconfirm --clean --workpath $work --distpath $dist music_theory.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed" }

$exe = Join-Path $root "dist\MusicTheoryMaster.exe"
if (Test-Path $exe) {
    $size = [math]::Round((Get-Item $exe).Length / 1MB, 1)
    Write-Host "==> Build complete: $exe ($size MB)" -ForegroundColor Green
} else {
    throw "expected executable not found at $exe"
}
