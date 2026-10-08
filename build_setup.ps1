param([switch]$SkipApplicationBuild)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
& "$PSScriptRoot\build_installer.ps1" -SkipApplicationBuild:$SkipApplicationBuild
if ($LASTEXITCODE -ne 0) { throw 'MSI build failed.' }
& "$PSScriptRoot\build_msi_bridge.ps1"
if ($LASTEXITCODE -ne 0) { throw 'MSI bridge build failed.' }
