$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $root

python -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw "Tests failed with exit code $LASTEXITCODE" }
python -m PyInstaller --noconfirm --clean --onefile --windowed `
  --name 'CodexShift-v1.8.0-Windows-x64' `
  --icon 'assets\codexshift.ico' `
  --add-data 'assets\codexshift-logo.png;assets' `
  --add-data 'assets\codexshift.ico;assets' `
  --version-file 'version_info.txt' `
  'codex_switcher.py'
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }

Write-Host "`nBuild complete: $root\dist\CodexShift-v1.8.0-Windows-x64.exe"
