$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $root

python -m unittest discover -s tests -v
python -m PyInstaller --noconfirm --clean --onefile --windowed `
  --name 'CodexShift-v1.7.0-Windows-x64' `
  --icon 'assets\codexshift.ico' `
  --add-data 'assets\codexshift-logo.png;assets' `
  --add-data 'assets\codexshift.ico;assets' `
  --version-file 'version_info.txt' `
  'codex_switcher.py'

Write-Host "`nBuild complete: $root\dist\CodexShift-v1.7.0-Windows-x64.exe"
