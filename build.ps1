$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Source = Join-Path $Root "src\keyboard_effects_studio.py"
$Vendor = Join-Path $Root "vendor\InsydeDCHU.dll"
$AppIcon = Join-Path $Root "assets\keyboard-effects-studio.ico"
$PythonRoot = Split-Path (Get-Command python.exe).Source
$TclRoot = Join-Path $PythonRoot "tcl"
if (-not (Test-Path -LiteralPath $Source)) { throw "Source not found: $Source" }
if (-not (Test-Path -LiteralPath $Vendor)) { throw "Vendor DLL not found: $Vendor" }
if (-not (Test-Path -LiteralPath $AppIcon)) { throw "App icon not found: $AppIcon" }
python.exe -m PyInstaller --version | Out-Null
if ($LASTEXITCODE -ne 0) { throw "PyInstaller is unavailable. Run: python -m pip install pyinstaller" }
$BinarySpec = "$Vendor;vendor"
$TclData = "$(Join-Path $TclRoot 'tcl8.6');_tcl_data"
$TkData = "$(Join-Path $TclRoot 'tk8.6');_tk_data"
$IconData = "$AppIcon;."
$Work = Join-Path $Root "build\work"
$Spec = Join-Path $Root "build\spec"
$Hooks = Join-Path $Root "build\hooks"
New-Item -ItemType Directory -Path $Work,$Spec -Force | Out-Null
Push-Location $Root
try {
    & python.exe -m PyInstaller --clean --noconfirm --onefile --windowed --uac-admin --name "KeyboardEffectsStudio" --icon $AppIcon --additional-hooks-dir $Hooks --hidden-import tkinter --add-data $TclData --add-data $TkData --add-data $IconData --add-binary $BinarySpec --distpath $Root --workpath $Work --specpath $Spec $Source
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }
}
finally {
    Pop-Location
}


