$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
& '.\.venv\Scripts\python.exe' -m pip install 'pyinstaller>=6,<7' 'pillow>=10'
if ($LASTEXITCODE -ne 0) { throw 'Falha nas dependências de empacotamento.' }
$tiltVersion = & '.\.venv\Scripts\python.exe' -c 'from tilt import __version__; print(__version__)'
if ($LASTEXITCODE -ne 0) { throw 'Não foi possível identificar a versão.' }
& '.\.venv\Scripts\python.exe' -m PyInstaller --noconfirm --distpath "dist\$tiltVersion" EFTX_Tilt.spec
if ($LASTEXITCODE -ne 0) { throw 'Falha no empacotamento.' }
Write-Host "Executável: dist\$tiltVersion\EFTX_Tilt\EFTX_Tilt.exe. Distribua a pasta inteira."
