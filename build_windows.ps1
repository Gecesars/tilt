$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
& '.\.venv\Scripts\python.exe' -m pip install 'pyinstaller>=6,<7' 'pillow>=10'
if ($LASTEXITCODE -ne 0) { throw 'Falha nas dependências de empacotamento.' }
& '.\.venv\Scripts\python.exe' -m PyInstaller --noconfirm EFTX_Tilt.spec
if ($LASTEXITCODE -ne 0) { throw 'Falha no empacotamento.' }
Write-Host 'Executável: dist\EFTX_Tilt\EFTX_Tilt.exe. Distribua a pasta inteira.'
