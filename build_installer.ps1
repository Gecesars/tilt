param([switch]$SkipApplicationBuild)
$ErrorActionPreference = 'Stop'
$env:DOTNET_ROLL_FORWARD = 'Major'
Set-Location -LiteralPath $PSScriptRoot
$tiltVersion = & '.\.venv\Scripts\python.exe' -c 'from tilt import __version__; print(__version__)'
if ($LASTEXITCODE -ne 0) { throw 'Falha ao obter versão.' }
if (-not $SkipApplicationBuild) {
    & "$PSScriptRoot\build_windows.ps1" -OutputRoot 'dist\release'
    if ($LASTEXITCODE -ne 0) { throw 'Falha no aplicativo.' }
}
$tiltPayload = Join-Path $PSScriptRoot "dist\release\$tiltVersion\EFTX_Tilt"
$tiltAssets = Join-Path $PSScriptRoot "build\installer\$tiltVersion"
$tiltMsi = Join-Path $PSScriptRoot "dist\EFTX_Tilt-$tiltVersion-Windows-x64.msi"
& '.\.venv\Scripts\python.exe' tools\prepare_installer.py $tiltPayload $tiltAssets
if ($LASTEXITCODE -ne 0) { throw 'Falha nos recursos do instalador.' }
& dotnet tool restore
if ($LASTEXITCODE -ne 0) { throw 'Falha ao restaurar WiX 5.0.2.' }
& dotnet tool run wix -- extension add WixToolset.UI.wixext/5.0.2
if ($LASTEXITCODE -ne 0) { throw 'Falha na extensão de interface WiX.' }
$tiltProductCode = (Get-Content -LiteralPath "$tiltAssets\product-code.txt" -Raw).Trim()
$tiltNugetLine = & dotnet nuget locals global-packages --list --force-english-output
if ($LASTEXITCODE -ne 0 -or $tiltNugetLine -notmatch '^global-packages: (.+)$') { throw 'Cache NuGet não localizado.' }
$tiltWixDll = Join-Path $Matches[1].Trim() 'wix\5.0.2\tools\net6.0\any\wix.dll'
# SDK 10 tool dispatch drops repeated -d options. Invoke the restored tool DLL
# directly so every definition reaches WiX, with runtime roll-forward enabled.
& dotnet exec --roll-forward Major $tiltWixDll build installer\Product.wxs "$tiltAssets\Payload.wxs" -arch x64 -culture pt-br -ext WixToolset.UI.wixext -d "Version=$tiltVersion" -d "ProductCode=$tiltProductCode" -d "PayloadDir=$tiltPayload" -d "AssetsDir=$tiltAssets" -intermediatefolder "$tiltAssets\intermediate" -pdb "$tiltAssets\EFTX_Tilt.wixpdb" -out $tiltMsi
if ($LASTEXITCODE -ne 0) { throw 'Falha ao compilar/validar MSI.' }
Write-Host "Instalador: $tiltMsi"
