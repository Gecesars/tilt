param([switch]$SkipApplicationBuild)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$tiltVersion = & '.\.venv\Scripts\python.exe' -c 'from tilt import __version__; print(__version__)'
if ($LASTEXITCODE -ne 0) { throw 'Version unavailable.' }
if (-not $SkipApplicationBuild) {
    & "$PSScriptRoot\build_windows.ps1" -OutputRoot 'dist\release'
    if ($LASTEXITCODE -ne 0) { throw 'Application build failed.' }
}
$tiltCompiler = & '.\.venv\Scripts\python.exe' tools\fetch_nsis.py
if ($LASTEXITCODE -ne 0) { throw 'NSIS download verification failed.' }
& '.\.venv\Scripts\python.exe' tools\prepare_setup.py
if ($LASTEXITCODE -ne 0) { throw 'Setup resources failed.' }
$tiltPayload = Join-Path $PSScriptRoot "dist\release\$tiltVersion\EFTX_Tilt"
$tiltAssets = Join-Path $PSScriptRoot "build\installer\$tiltVersion"
$tiltOutput = Join-Path $PSScriptRoot "dist\EFTX_Tilt-$tiltVersion-Setup-x64.exe"
& $tiltCompiler /V3 /WX /NOCONFIG /INPUTCHARSET UTF8 "/DVERSION=$tiltVersion" "/DPAYLOAD=$tiltPayload" "/DASSETS=$tiltAssets" "/DOUTPUT=$tiltOutput" installer\Setup.nsi
if ($LASTEXITCODE -ne 0) { throw 'NSIS compilation failed.' }
Write-Host "Setup: $tiltOutput"
