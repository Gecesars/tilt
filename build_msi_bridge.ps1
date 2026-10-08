param()
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$tiltVersion = & '.\.venv\Scripts\python.exe' -c 'from tilt import __version__; print(__version__)'
if ($LASTEXITCODE -ne 0) { throw 'Version unavailable.' }
$tiltMsi = Join-Path $PSScriptRoot "dist\EFTX_Tilt-$tiltVersion-Windows-x64.msi"
if (-not (Test-Path -LiteralPath $tiltMsi)) { throw 'Build the MSI first.' }
$tiltCompiler = & '.\.venv\Scripts\python.exe' tools\fetch_nsis.py
if ($LASTEXITCODE -ne 0) { throw 'NSIS verification failed.' }
$tiltAssets = Join-Path $PSScriptRoot "build\installer\$tiltVersion"
$tiltOutput = Join-Path $PSScriptRoot "dist\EFTX_Tilt-$tiltVersion-Setup-x64.exe"
& $tiltCompiler /V3 /WX /NOCONFIG /INPUTCHARSET UTF8 "/DVERSION=$tiltVersion" "/DMSI=$tiltMsi" "/DASSETS=$tiltAssets" "/DOUTPUT=$tiltOutput" installer\MsiBridge.nsi
if ($LASTEXITCODE -ne 0) { throw 'MSI bridge build failed.' }
Write-Host "MSI compatibility bridge: $tiltOutput"
