param([string]$Version = '1.4.0', [string]$UpgradeFrom = '', [switch]$CheckUpdates)
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
    $tiltInstallArguments = "/S /ACCEPTEULA=1 /D=$tiltInstall"
    if ($UpgradeFrom) {
        $tiltOldSetup = Join-Path $tiltRoot "dist\EFTX_Tilt-$UpgradeFrom-Setup-x64.exe"
        if (-not (Test-Path -LiteralPath $tiltOldSetup)) { throw 'Previous installer unavailable.' }
        $tiltResults.previous_install = Invoke-CheckedProcess $tiltOldSetup $tiltInstallArguments
        if ($tiltResults.previous_install -ne 0) { throw 'Previous installer failed.' }
        'preserved during upgrade' | Set-Content -LiteralPath "$tiltInstall\upgrade-user-file.txt"
        $tiltInstallArguments = '/S /ACCEPTEULA=1'
    }
    $tiltResults.install = Invoke-CheckedProcess $tiltSetup $tiltInstallArguments
    if ($tiltResults.install -ne 0) { throw "Install failed: $($tiltResults.install)" }
    if ($UpgradeFrom -and -not (Test-Path -LiteralPath "$tiltInstall\upgrade-user-file.txt")) { throw 'Upgrade did not retain user file/path.' }
    $tiltRegistration = Get-ItemProperty 'HKCU:\Software\EFTX\TiltSetup'
    if ($tiltRegistration.Version -ne $Version -or $tiltRegistration.InstallLocation -ne $tiltInstall) { throw 'Wrong registered version or path.' }
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
        $tiltResults["central_$tiltPlatform"] = Invoke-CheckedProcess "$tiltInstall\EFTX_Tilt.exe" "--smoke-test --smoke-center --database `"$tiltRun\central-$tiltPlatform.sqlite3`" --smoke-pdf `"$tiltRun\central-$tiltPlatform.pdf`""
        if ($tiltResults["central_$tiltPlatform"] -ne 0 -or -not (Test-Path -LiteralPath "$tiltRun\central-$tiltPlatform.pdf")) { throw "Central-feed smoke failed: $tiltPlatform" }
    }
    if ($CheckUpdates) {
        $tiltResults.update_https = Invoke-CheckedProcess "$tiltInstall\EFTX_Tilt.exe" "--smoke-test --database `"$tiltRun\updates.sqlite3`" --smoke-updates `"$tiltRun\updates.json`" --smoke-update-download"
        if ($tiltResults.update_https -ne 0) { throw 'Frozen updater HTTPS/download failed.' }
        $tiltUpdate = Get-Content -LiteralPath "$tiltRun\updates.json" -Raw | ConvertFrom-Json
        if (-not $tiltUpdate.ok -or -not $tiltUpdate.download_verified -or $tiltUpdate.installer_executed -or $tiltUpdate.tls_backend -ne 'schannel') { throw 'Frozen updater failed its integrity/TLS contract.' }
    }
    $tiltLicense = (Resolve-Path -LiteralPath "$tiltInstall\LICENSE.txt").Path
    if (-not $tiltLicense.StartsWith($tiltRun+'\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe test path.' }
    Remove-Item -LiteralPath $tiltLicense
    # A live application holds the DLLs. Setup must wait, then resume only after
    # the application exits. This exercises the same /WAITPID as the updater.
    $tiltLive = Start-Process -FilePath "$tiltInstall\EFTX_Tilt.exe" -ArgumentList "--smoke-test --smoke-delay-ms 8000 --database `"$tiltRun\waitpid.sqlite3`"" -WindowStyle Hidden -PassThru
    $tiltPendingSetup = $null
    try {
        Start-Sleep -Seconds 2
        $tiltPendingSetup = Start-Process -FilePath $tiltSetup -ArgumentList "/S /ACCEPTEULA=1 /WAITPID=$($tiltLive.Id) /D=$tiltInstall" -WindowStyle Hidden -PassThru
        Start-Sleep -Seconds 2
        $tiltPendingSetup.Refresh()
        if ($tiltLive.HasExited -or $tiltPendingSetup.HasExited -or (Test-Path -LiteralPath $tiltLicense)) { throw 'Installer did not wait for application exit.' }
        # Diagnostic timer closes the real Qt app normally, even with no visible
        # desktop (CI). Do not depend on Process.MainWindowHandle for hidden UI.
        if (-not $tiltLive.WaitForExit(15000)) { throw 'Test application did not exit.' }
        if (-not $tiltPendingSetup.WaitForExit(60000)) { throw 'Installer did not resume after application exit.' }
        $tiltPendingSetup.Refresh()
        $tiltResults.reinstall = $tiltPendingSetup.ExitCode
        $tiltResults.waitpid = 'waited for live application and resumed'
    } finally {
        if (-not $tiltLive.HasExited) { $tiltLive.Kill() }
        if ($tiltPendingSetup -and -not $tiltPendingSetup.HasExited) { $tiltPendingSetup.Kill() }
    }
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
