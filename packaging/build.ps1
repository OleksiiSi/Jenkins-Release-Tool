<#
Builds a distributable installer for Release Tool. Lives in packaging/
alongside everything else exe-packaging-related (installer.iss,
installer_output/, dist/, .build/); the actual app source (main.py, core/,
ui/, settings*.json) lives one level up in app/.
  1. Reads the version from pyproject.toml (single source of truth).
  2. Runs PyInstaller (--onedir) to produce packaging/dist/ReleaseTool/.
  3. Runs Inno Setup's ISCC.exe to wrap that folder into a versioned
     installer at packaging/installer_output/ReleaseTool-Setup-<version>.exe.

Requires: Poetry (dev dependencies installed - see pyproject.toml's
[tool.poetry.group.dev.dependencies]), Inno Setup 6 (free,
https://jrsoftware.org/isinfo.php) with ISCC.exe on PATH or in one of its
default install locations.

Usage (from anywhere - paths are absolute, not cwd-relative):
  .\build.ps1               # full build: PyInstaller + installer
  .\build.ps1 -SkipInstaller # PyInstaller only, skip the Inno Setup step
#>

param(
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"
$BuildDir = $PSScriptRoot
$RepoRoot = Split-Path $BuildDir -Parent
$AppDir = Join-Path $RepoRoot "app"

# ---- Version (read from pyproject.toml, never hand-edited elsewhere) ----
$pyprojectText = Get-Content (Join-Path $RepoRoot "pyproject.toml") -Raw
if ($pyprojectText -notmatch 'version\s*=\s*"([^"]+)"') {
    throw "Could not find a version in pyproject.toml"
}
$Version = $Matches[1]
Write-Host "Building Release Tool v$Version" -ForegroundColor Cyan

# ---- Clean previous build output ----
foreach ($dir in @("build", "dist")) {
    $path = Join-Path $BuildDir $dir
    if (Test-Path $path) {
        Remove-Item $path -Recurse -Force
    }
}

# ---- PyInstaller ----
Write-Host "Running PyInstaller..." -ForegroundColor Cyan
poetry run pyinstaller `
    (Join-Path $AppDir "main.py") `
    --name ReleaseTool `
    --onedir `
    --contents-directory bin `
    --noconsole `
    --icon "$(Join-Path $AppDir 'ui\assets\tray_icon.ico')" `
    --distpath (Join-Path $BuildDir "dist") `
    --workpath (Join-Path $BuildDir "build") `
    --specpath $BuildDir `
    --noconfirm

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE"
}

# ---- Place app-facing files at the top level, alongside the exe ----
# (deliberately not via --add-data: that would land them inside bin/ with
# PyInstaller's own runtime files, instead of next to ReleaseTool.exe where
# core/config.py's APP_DIR expects them)
$AppDist = Join-Path $BuildDir "dist\ReleaseTool"
Copy-Item (Join-Path $AppDir "ui") (Join-Path $AppDist "ui") -Recurse
Copy-Item (Join-Path $AppDir "settings.json") (Join-Path $AppDist "settings.json")
Copy-Item (Join-Path $AppDir "settings.default.json") (Join-Path $AppDist "settings.default.json")

if ($SkipInstaller) {
    Write-Host "Done (installer step skipped). App folder: packaging\dist\ReleaseTool" -ForegroundColor Green
    exit 0
}

# ---- Locate Inno Setup's compiler ----
$IsccFromPath = Get-Command ISCC.exe -ErrorAction SilentlyContinue
$IsccPathFromCommand = $null
if ($IsccFromPath) {
    $IsccPathFromCommand = $IsccFromPath.Source
}

$IsccCandidates = @(@(
    $IsccPathFromCommand,
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe",
    (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe")
) | Where-Object { $_ -and (Test-Path $_) })

if (-not $IsccCandidates) {
    throw "Inno Setup's ISCC.exe not found. Install Inno Setup 6 (https://jrsoftware.org/isinfo.php) or add ISCC.exe to PATH, then re-run, or use -SkipInstaller to build the app folder only."
}
$Iscc = $IsccCandidates[0]

# ---- Compile installer ----
$OutputDir = Join-Path $BuildDir "installer_output"
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
}

Write-Host "Compiling installer with Inno Setup..." -ForegroundColor Cyan
& $Iscc `
    "/DAppVersion=$Version" `
    "/DSourceDir=$(Join-Path $BuildDir 'dist\ReleaseTool')" `
    "/DOutputDir=$OutputDir" `
    (Join-Path $BuildDir "installer.iss")

if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup compilation failed with exit code $LASTEXITCODE"
}

Write-Host "Done. Installer: $OutputDir\ReleaseTool-Setup-$Version.exe" -ForegroundColor Green
