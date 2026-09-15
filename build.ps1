# build.ps1 — Build FO76TagCustomizer.exe with PyInstaller
#
# Usage:
#   .\build.ps1           # build
#   .\build.ps1 -Clean    # wipe build/ and dist/ first, then build

param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot

Set-Location $ProjectRoot

# Locate pyinstaller — prefer the Scripts dir of the known Python install, then fall
# back to whatever is on PATH.
$PyInstallerExe = "C:\Users\mshie\AppData\Local\Python\pythoncore-3.14-64\Scripts\pyinstaller.exe"
if (-not (Test-Path $PyInstallerExe)) {
    $PyInstallerExe = (Get-Command pyinstaller -ErrorAction SilentlyContinue).Source
}
if (-not $PyInstallerExe) {
    Write-Host "ERROR: pyinstaller not found. Run: pip install pyinstaller" -ForegroundColor Red
    exit 1
}

if ($Clean) {
    Write-Host "Cleaning build/ and dist/..." -ForegroundColor Cyan
    Remove-Item -Recurse -Force "build", "dist" -ErrorAction SilentlyContinue
}

Write-Host "Building FO76TagCustomizer.exe..." -ForegroundColor Cyan
& $PyInstallerExe fo76_tag_customizer.spec

if ($LASTEXITCODE -ne 0) {
    Write-Host "Build FAILED (exit $LASTEXITCODE)" -ForegroundColor Red
    exit $LASTEXITCODE
}

$exe = Join-Path $ProjectRoot "dist\FO76TagCustomizer.exe"
if (Test-Path $exe) {
    $size = [math]::Round((Get-Item $exe).Length / 1MB, 1)
    Write-Host ""
    Write-Host "Build succeeded!" -ForegroundColor Green
    Write-Host "  $exe  ($size MB)"
} else {
    Write-Host "Build finished but exe not found at expected path." -ForegroundColor Yellow
}
