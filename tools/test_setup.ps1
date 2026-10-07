param([string]$Version = '1.3.2')
$ErrorActionPreference = 'Stop'
$tiltRoot = Split-Path -Parent $PSScriptRoot
$tiltSetup = Join-Path $tiltRoot "dist\EFTX_Tilt-$Version-Setup-x64.exe"
$tiltManifest = Get-Content -LiteralPath "$tiltRoot\build\installer\$Version\payload-manifest.json" -Raw | ConvertFrom-Json
if (Test-Path 'HKCU:\Software\EFTX\TiltSetup') { throw 'Existing EXE installation: use a test account.' }
$tiltDesktopLink = Join-Path ([Environment]::GetFolderPath('Desktop')) 'EFTX Tilt Desktop.lnk'
$tiltMenu = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\EFTX Tilt Desktop"
if ((Test-Path -LiteralPath $tiltDesktopLink) -or (Test-Path -LiteralPath $tiltMenu)) { throw 'Existing EXE shortcuts: use a test account.' }
$tiltRun = Join-Path $tiltRoot ('.artifacts\setup-test-' + [Guid]::NewGuid().ToString('N'))
$tiltInstall = Join-Path $tiltRun 'instalacao limpa'
New-Item -ItemType Directory -Path $tiltRun | Out-Null
$tiltPreserved = @{}
foreach ($tiltFolder in @("$env:LOCALAPPDATA\EFTX\EFTX Tilt", "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\EFTX")) {
    if (Test-Path -LiteralPath $tiltFolder) {
        Get-ChildItem -LiteralPath $tiltFolder -File -Recurse | ForEach-Object {
            $tiltPreserved[$_.FullName] = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
        }
    }
}
$tiltResults = [ordered]@{version=$Version; run=$tiltRun; os=[Environment]::OSVersion.VersionString}
function Invoke-CheckedProcess([string]$File, [string]$Arguments) {
    $tiltProcess = Start-Process -FilePath $File -ArgumentList $Arguments -WindowStyle Hidden -PassThru
    if (-not $tiltProcess.WaitForExit(60000)) {
        $tiltProcess.Kill()
        throw "Timed out: $File"
    }
    $tiltProcess.Refresh()
    return $tiltProcess.ExitCode
}
$tiltSavedEnv = @{}
foreach ($tiltKey in @('PATH','PYTHONHOME','PYTHONPATH','QT_PLUGIN_PATH','QT_QPA_PLATFORM_PLUGIN_PATH','QML2_IMPORT_PATH','QT_QPA_PLATFORM')) {
    $tiltSavedEnv[$tiltKey] = [Environment]::GetEnvironmentVariable($tiltKey,'Process')
}
try {
    $tiltResults.license_rejection = Invoke-CheckedProcess $tiltSetup "/S /D=$tiltInstall"
    if ($tiltResults.license_rejection -ne 1603 -or (Test-Path -LiteralPath "$tiltInstall\EFTX_Tilt.exe")) { throw 'Silent EULA check failed.' }
    $tiltResults.install = Invoke-CheckedProcess $tiltSetup "/S /ACCEPTEULA=1 /D=$tiltInstall"
    if ($tiltResults.install -ne 0) { throw "Install failed: $($tiltResults.install)" }
    foreach ($tiltItem in $tiltManifest.files) {
        if ((Get-FileHash -LiteralPath (Join-Path $tiltInstall $tiltItem.path) -Algorithm SHA256).Hash -ne $tiltItem.sha256) { throw "Wrong installed bytes: $($tiltItem.path)" }
    }
    $tiltResults.verified_files = $tiltManifest.files.Count
    if (-not (Test-Path -LiteralPath $tiltDesktopLink)) { throw 'Desktop shortcut absent.' }
    $tiltLink = (New-Object -ComObject WScript.Shell).CreateShortcut($tiltDesktopLink)
    if ($tiltLink.TargetPath -ne "$tiltInstall\EFTX_Tilt.exe") { throw 'Shortcut target mismatch.' }
    'user-owned fixture' | Set-Content -LiteralPath "$tiltInstall\user-added.txt"
    $env:PATH = "$env:WINDIR\System32;$env:WINDIR"
    foreach ($tiltKey in @('PYTHONHOME','PYTHONPATH','QT_PLUGIN_PATH','QT_QPA_PLATFORM_PLUGIN_PATH','QML2_IMPORT_PATH')) {
        [Environment]::SetEnvironmentVariable($tiltKey, $null, 'Process')
    }
    foreach ($tiltPlatform in @('offscreen','windows')) {
        $env:QT_QPA_PLATFORM = $tiltPlatform
        $tiltResults["smoke_$tiltPlatform"] = Invoke-CheckedProcess "$tiltInstall\EFTX_Tilt.exe" "--smoke-test --database `"$tiltRun\$tiltPlatform.sqlite3`" --smoke-pdf `"$tiltRun\$tiltPlatform.pdf`" --smoke-diagnostics `"$tiltRun\$tiltPlatform.json`""
        if ($tiltResults["smoke_$tiltPlatform"] -ne 0 -or -not (Test-Path -LiteralPath "$tiltRun\$tiltPlatform.pdf")) { throw "Frozen smoke failed: $tiltPlatform" }
        $tiltDiagnostic = Get-Content -LiteralPath "$tiltRun\$tiltPlatform.json" -Raw | ConvertFrom-Json
        if ($tiltDiagnostic.application -ne $Version -or $tiltDiagnostic.external_runtime_modules.Count -ne 0) { throw 'Runtime loaded from outside the installed package.' }
        $tiltResults["local_runtime_modules_$tiltPlatform"] = $tiltDiagnostic.runtime_modules.Count
    }
    $tiltLicense = (Resolve-Path -LiteralPath "$tiltInstall\LICENSE.txt").Path
    if (-not $tiltLicense.StartsWith($tiltRun+'\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe test path.' }
    Remove-Item -LiteralPath $tiltLicense
    $tiltResults.reinstall = Invoke-CheckedProcess $tiltSetup "/S /ACCEPTEULA=1 /D=$tiltInstall"
    if ($tiltResults.reinstall -ne 0 -or -not (Test-Path -LiteralPath $tiltLicense)) { throw 'Reinstall did not restore package.' }
} finally {
    foreach ($tiltKey in $tiltSavedEnv.Keys) { [Environment]::SetEnvironmentVariable($tiltKey,$tiltSavedEnv[$tiltKey],'Process') }
    if (Test-Path 'HKCU:\Software\EFTX\TiltSetup') {
        $tiltRegistered = (Get-ItemProperty 'HKCU:\Software\EFTX\TiltSetup').InstallLocation
        if ($tiltRegistered -ne $tiltInstall) { throw 'Install location changed. Automatic uninstall cancelled.' }
        $tiltResults.uninstall_launcher = Invoke-CheckedProcess "$tiltInstall\Desinstalar.exe" '/S'
        $tiltDeadline = [DateTime]::UtcNow.AddSeconds(30)
        while ((Test-Path -LiteralPath "$tiltInstall\EFTX_Tilt.exe") -and [DateTime]::UtcNow -lt $tiltDeadline) { Start-Sleep -Milliseconds 200 }
    }
    $tiltResults | ConvertTo-Json | Set-Content -LiteralPath "$tiltRun\results.json" -Encoding UTF8
}
if ((Test-Path 'HKCU:\Software\EFTX\TiltSetup') -or (Test-Path -LiteralPath "$tiltInstall\EFTX_Tilt.exe") -or (Test-Path -LiteralPath $tiltDesktopLink)) { throw 'Incomplete uninstall.' }
if (-not (Test-Path -LiteralPath "$tiltInstall\user-added.txt")) { throw 'User file deleted.' }
foreach ($tiltPath in $tiltPreserved.Keys) {
    if ((Get-FileHash -LiteralPath $tiltPath -Algorithm SHA256).Hash -ne $tiltPreserved[$tiltPath]) { throw 'Preexisting data modified.' }
}
$tiltResults.preserved_files = $tiltPreserved.Count
$tiltResults.extra_file_preserved = $true
$tiltResults | ConvertTo-Json | Set-Content -LiteralPath "$tiltRun\results.json" -Encoding UTF8
$tiltResults | ConvertTo-Json
