param([string]$Version = '1.4.1', [string]$UpgradeFrom = '', [string]$FromExe = '', [switch]$UseBridge, [switch]$CheckUpdates)
$ErrorActionPreference = 'Stop'
$tiltRoot = Split-Path -Parent $PSScriptRoot
$tiltMsi = Join-Path $tiltRoot "dist\EFTX_Tilt-$Version-Windows-x64.msi"
$tiltManifestPath = Join-Path $tiltRoot "build\installer\$Version\payload-manifest.json"
$tiltManifest = Get-Content -LiteralPath $tiltManifestPath -Raw | ConvertFrom-Json
$tiltRun = Join-Path $tiltRoot ('.artifacts\msi-test-' + [Guid]::NewGuid().ToString('N'))
$tiltInstall = Join-Path $tiltRun 'installed'
New-Item -ItemType Directory -Path $tiltRun | Out-Null
$tiltInstaller = New-Object -ComObject WindowsInstaller.Installer
$tiltOldInstall = if ($UpgradeFrom -and $FromExe) { Join-Path $tiltRun 'previous-msi' } else { $tiltInstall }
if ($UseBridge -and -not $FromExe) { throw 'Bridge test requires a legacy EXE installation in the test directory.' }
if (Test-Path 'HKCU:\Software\EFTX\TiltSetup') { throw 'An EXE installation already exists. Use a test account.' }
foreach ($tiltRelated in $tiltInstaller.RelatedProducts('{69BB6A93-58DF-488F-B5C8-5D88112A3E6D}')) {
    if ($tiltInstaller.ProductState($tiltRelated) -ne -1) { throw 'An EFTX MSI already exists. Use a test account.' }
}
$tiltDatabase = $tiltInstaller.OpenDatabase($tiltMsi, 0)
$tiltView = $tiltDatabase.OpenView('SELECT `Value` FROM `Property` WHERE `Property` = ''ProductCode''')
$tiltView.Execute()
$tiltProduct = $tiltView.Fetch().StringData(1)
$tiltView.Close()
if ($tiltInstaller.ProductState($tiltProduct) -ne -1) { throw 'Produto já registrado. Teste deve começar sem esta instalação MSI.' }
$tiltOldProduct = $null
if ($UpgradeFrom) {
    $tiltOldMsi = Join-Path $tiltRoot "dist\EFTX_Tilt-$UpgradeFrom-Windows-x64.msi"
    $tiltOldDb = $tiltInstaller.OpenDatabase($tiltOldMsi, 0)
    $tiltOldView = $tiltOldDb.OpenView('SELECT `Value` FROM `Property` WHERE `Property` = ''ProductCode''')
    $tiltOldView.Execute()
    $tiltOldProduct = $tiltOldView.Fetch().StringData(1)
    $tiltOldView.Close()
    if ($tiltOldProduct -eq $tiltProduct -or $tiltInstaller.ProductState($tiltOldProduct) -ne -1) { throw 'Versao anterior invalida ou ja instalada.' }
}
foreach ($tiltShortcut in @(
    "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\EFTX\EFTX Tilt.lnk",
    "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\EFTX\Licen$([char]0x00e7)a EFTX Tilt.lnk",
    (Join-Path ([Environment]::GetFolderPath('Desktop')) 'EFTX Tilt.lnk'),
    (Join-Path ([Environment]::GetFolderPath('Desktop')) 'EFTX Tilt Desktop.lnk'),
    "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\EFTX Tilt Desktop\EFTX Tilt.lnk"
)) {
    if (Test-Path -LiteralPath $tiltShortcut) { throw "Atalho preexistente: $tiltShortcut. Use um usuário de teste." }
}
function Get-PreservedFiles {
    $tiltMap = @{}
    foreach ($tiltFolder in @("$env:LOCALAPPDATA\EFTX\EFTX Tilt", "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\EFTX")) {
        if (Test-Path -LiteralPath $tiltFolder) {
            Get-ChildItem -LiteralPath $tiltFolder -File -Recurse | ForEach-Object {
                $tiltMap[$_.FullName] = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
            }
        }
    }
    return $tiltMap
}
function Invoke-Msi([string]$Action, [string]$Target, [string]$Extra, [string]$LogName) {
    $tiltLog = Join-Path $tiltRun $LogName
    $tiltProcess = Start-Process msiexec.exe -ArgumentList "$Action `"$Target`" /qn /norestart $Extra /L*v `"$tiltLog`"" -WindowStyle Hidden -PassThru -Wait
    return $tiltProcess.ExitCode
}
function Invoke-Exe([string]$File, [string]$Arguments) {
    $tiltProcess = Start-Process -FilePath $File -ArgumentList $Arguments -WindowStyle Hidden -PassThru
    if (-not $tiltProcess.WaitForExit(90000)) { $tiltProcess.Kill(); throw 'EXE test timed out.' }
    $tiltProcess.Refresh()
    return $tiltProcess.ExitCode
}
$tiltBefore = Get-PreservedFiles
$tiltBefore | ConvertTo-Json | Set-Content -LiteralPath "$tiltRun\preserved-before.json" -Encoding UTF8
$tiltResults = [ordered]@{version=$Version; product=$tiltProduct; run=$tiltRun; started_utc=[DateTime]::UtcNow.ToString('o')}
$tiltOldPlatform = $env:QT_QPA_PLATFORM
$tiltSavedEnv = @{}
foreach ($tiltKey in @('PATH','PYTHONHOME','PYTHONPATH','QT_PLUGIN_PATH','QT_QPA_PLATFORM_PLUGIN_PATH','QML2_IMPORT_PATH')) {
    $tiltSavedEnv[$tiltKey] = [Environment]::GetEnvironmentVariable($tiltKey,'Process')
}
try {
    $tiltResults.license_rejection = Invoke-Msi '/i' $tiltMsi "INSTALLFOLDER=`"$tiltInstall`"" 'license-rejected.log'
    if ($tiltResults.license_rejection -ne 1603 -or (Test-Path -LiteralPath "$tiltInstall\EFTX_Tilt.exe")) { throw 'Instalação sem aceite não foi bloqueada.' }
    if (-not (Select-String -LiteralPath "$tiltRun\license-rejected.log" -Pattern 'EFTX_ACCEPT_LICENSE=1' -Quiet)) { throw 'Falha não identificada como falta de aceite.' }
    $tiltInstallExtra = "EFTX_ACCEPT_LICENSE=1 INSTALLFOLDER=`"$tiltInstall`""
    if ($UpgradeFrom) {
        $tiltResults.upgrade_from = $UpgradeFrom
        $tiltResults.install_previous = Invoke-Msi '/i' $tiltOldMsi "EFTX_ACCEPT_LICENSE=1 INSTALLFOLDER=`"$tiltOldInstall`"" 'install-previous.log'
        if ($tiltResults.install_previous -notin @(0,3010)) { throw 'Falha ao instalar versao anterior.' }
        'user-owned fixture' | Set-Content -LiteralPath "$tiltOldInstall\user-added.txt"
        # Exercise remembered custom location; no INSTALLFOLDER on upgrade.
        $tiltInstallExtra = 'EFTX_ACCEPT_LICENSE=1'
    }
    if ($FromExe) {
        $tiltOldExe = Join-Path $tiltRoot "dist\EFTX_Tilt-$FromExe-Setup-x64.exe"
        $tiltResults.from_exe = $FromExe
        $tiltResults.previous_exe_sha256 = (Get-FileHash -LiteralPath $tiltOldExe).Hash
        $tiltResults.install_previous = Invoke-Exe $tiltOldExe "/S /ACCEPTEULA=1 /D=$tiltInstall"
        if ($tiltResults.install_previous -ne 0) { throw 'Legacy EXE install failed.' }
        $tiltLegacy = Get-ItemProperty 'HKCU:\Software\EFTX\TiltSetup'
        if ($tiltLegacy.Version -ne $FromExe -or $tiltLegacy.InstallLocation -ne $tiltInstall) { throw 'Legacy EXE registration is not ready.' }
        'preserve this user file' | Set-Content -LiteralPath "$tiltInstall\migration-user-file.txt"
        # Reproduce partial/unversioned old files; MSI must replace these bytes.
        [System.IO.File]::AppendAllText("$tiltInstall\LICENSE.txt", 'modified before migration')
        $tiltInstallExtra = 'EFTX_ACCEPT_LICENSE=1'
    }
    if ($UseBridge) {
        # Exercise the exact EXE-only updater contract with the old app alive.
        $env:QT_QPA_PLATFORM = 'offscreen'
        $tiltLive = Start-Process -FilePath "$tiltInstall\EFTX_Tilt.exe" -ArgumentList "--smoke-test --smoke-delay-ms 8000 --database `"$tiltRun\waitpid.sqlite3`"" -WindowStyle Hidden -PassThru
        $tiltPendingSetup = $null
        try {
            Start-Sleep -Seconds 2
            $tiltPendingSetup = Start-Process -FilePath (Join-Path $tiltRoot "dist\EFTX_Tilt-$Version-Setup-x64.exe") -ArgumentList "/S /ACCEPTEULA=1 /WAITPID=$($tiltLive.Id)" -WindowStyle Hidden -PassThru
            Start-Sleep -Seconds 2
            $tiltPendingSetup.Refresh()
            if ($tiltLive.HasExited -or $tiltPendingSetup.HasExited -or $tiltInstaller.ProductState($tiltProduct) -eq 5) { throw 'Bridge did not wait for old app exit.' }
            if (-not $tiltLive.WaitForExit(15000)) { throw 'Test app did not exit.' }
            if (-not $tiltPendingSetup.WaitForExit(90000)) { throw 'Bridge did not finish.' }
            $tiltPendingSetup.Refresh()
            $tiltResults.install = $tiltPendingSetup.ExitCode
            $tiltResults.waitpid = 'waited for old application and resumed'
        } finally {
            if (-not $tiltLive.HasExited) { $tiltLive.Kill() }
            if ($tiltPendingSetup -and -not $tiltPendingSetup.HasExited) { $tiltPendingSetup.Kill() }
            $env:QT_QPA_PLATFORM = $tiltOldPlatform
        }
    } else {
        $tiltResults.install = Invoke-Msi '/i' $tiltMsi $tiltInstallExtra 'install.log'
    }
    if ($tiltResults.install -notin @(0,3010)) { throw "Falha de instalação: $($tiltResults.install)" }
    if ($UpgradeFrom) {
        if ($tiltInstaller.ProductState($tiltOldProduct) -ne -1) { throw 'Versao anterior ainda registrada.' }
        if ((Get-Content -LiteralPath "$tiltOldInstall\user-added.txt" -Raw).Trim() -ne 'user-owned fixture') { throw 'Arquivo extra perdido no upgrade.' }
        if ($FromExe -and (Test-Path -LiteralPath "$tiltOldInstall\EFTX_Tilt.exe")) { throw 'Old MSI payload remains after migration to EXE folder.' }
        foreach ($tiltObsolete in @('ucrtbase.dll','api-ms-win-core-file-l1-1-0.dll','libssl-3-x64.dll')) {
            if (Test-Path -LiteralPath "$tiltInstall\_internal\$tiltObsolete") { throw "DLL obsoleta preservada: $tiltObsolete" }
        }
        $tiltResults.upgrade_preserved_custom_path_and_extra_file = $true
    }
    if ($FromExe) {
        if ((Test-Path 'HKCU:\Software\EFTX\TiltSetup') -or (Test-Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\EFTXTiltDesktop')) { throw 'Legacy EXE registration remains active.' }
        if ((Test-Path -LiteralPath "$tiltInstall\Desinstalar.exe") -or (Test-Path -LiteralPath "$tiltInstall\.eftx-install.ini")) { throw 'Legacy uninstaller could remove the new MSI files.' }
        if (-not (Test-Path -LiteralPath "$tiltInstall\migration-user-file.txt")) { throw 'Migration lost a user file.' }
        $tiltResults.migrated_exe = $true
    }
    $tiltRegistration = Get-ItemProperty 'HKCU:\Software\EFTX\Tilt'
    if ($tiltRegistration.Version -ne $Version -or $tiltRegistration.InstallLocation.TrimEnd('\') -ne $tiltInstall -or $tiltRegistration.InstallerType -ne 'MSI') { throw 'MSI registration or reused path is wrong.' }
    if ($UpgradeFrom) {
        $tiltResults.downgrade_rejected = Invoke-Msi '/i' $tiltOldMsi 'EFTX_ACCEPT_LICENSE=1' 'downgrade-rejected.log'
        if ($tiltResults.downgrade_rejected -ne 1603) { throw 'Older MSI was not rejected.' }
    }
    foreach ($tiltItem in $tiltManifest.files) {
        $tiltFile = Join-Path $tiltInstall $tiltItem.path
        if ((Get-FileHash -LiteralPath $tiltFile -Algorithm SHA256).Hash -ne $tiltItem.sha256) { throw "Hash instalado divergente: $tiltFile" }
    }
    $tiltResults.verified_files = $tiltManifest.files.Count
    'user-owned fixture' | Set-Content -LiteralPath "$tiltInstall\user-added.txt"
    $env:PATH = "$env:WINDIR\System32;$env:WINDIR"
    foreach ($tiltKey in @('PYTHONHOME','PYTHONPATH','QT_PLUGIN_PATH','QT_QPA_PLATFORM_PLUGIN_PATH','QML2_IMPORT_PATH')) { [Environment]::SetEnvironmentVariable($tiltKey, $null, 'Process') }
    foreach ($tiltPlatform in @('offscreen', 'windows')) {
        $env:QT_QPA_PLATFORM = $tiltPlatform
        $tiltSmoke = Start-Process -FilePath "$tiltInstall\EFTX_Tilt.exe" -ArgumentList "--smoke-test --smoke-center --database `"$tiltRun\$tiltPlatform.sqlite3`" --smoke-pdf `"$tiltRun\$tiltPlatform.pdf`" --smoke-diagnostics `"$tiltRun\$tiltPlatform.json`"" -WindowStyle Hidden -PassThru -Wait
        $tiltResults["smoke_$tiltPlatform"] = $tiltSmoke.ExitCode
        if ($tiltSmoke.ExitCode -ne 0 -or -not (Test-Path -LiteralPath "$tiltRun\$tiltPlatform.pdf")) { throw "Falha no aplicativo instalado: $tiltPlatform" }
        $tiltDiagnostic = Get-Content -LiteralPath "$tiltRun\$tiltPlatform.json" -Raw | ConvertFrom-Json
        if ($tiltDiagnostic.application -ne $Version -or $tiltDiagnostic.external_runtime_modules.Count -ne 0) { throw 'Runtime loaded outside the MSI package.' }
    }
    if ($CheckUpdates) {
        $tiltResults.update_https = Invoke-Exe "$tiltInstall\EFTX_Tilt.exe" "--smoke-test --database `"$tiltRun\updates.sqlite3`" --smoke-updates `"$tiltRun\updates.json`" --smoke-update-download"
        if ($tiltResults.update_https -ne 0) { throw 'MSI installed updater failed.' }
    }
    # Exercise repair of one owned test file; never touch real user data.
    $tiltLicense = (Resolve-Path -LiteralPath "$tiltInstall\LICENSE.txt").Path
    if (-not $tiltLicense.StartsWith($tiltRun + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Caminho de teste inválido.' }
    Remove-Item -LiteralPath $tiltLicense
    $tiltResults.repair = Invoke-Msi '/fa' $tiltProduct '' 'repair.log'
    if ($tiltResults.repair -notin @(0,3010) -or -not (Test-Path -LiteralPath $tiltLicense)) { throw 'Reparação não restaurou a licença.' }
} catch {
    $tiltResults.failure = $_.Exception.Message
    $tiltResults | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath "$tiltRun\results.json" -Encoding UTF8
    throw
} finally {
    $env:QT_QPA_PLATFORM = $tiltOldPlatform
    foreach ($tiltKey in $tiltSavedEnv.Keys) { [Environment]::SetEnvironmentVariable($tiltKey,$tiltSavedEnv[$tiltKey],'Process') }
    if ($tiltInstaller.ProductState($tiltProduct) -eq 5) {
        $tiltRegisteredPath = (Get-ItemProperty 'HKCU:\Software\EFTX\Tilt').InstallLocation
        if ($tiltRegisteredPath.TrimEnd('\') -ne $tiltInstall) { throw 'Local registrado mudou; desinstalação automática cancelada.' }
        $tiltResults.uninstall = Invoke-Msi '/x' $tiltProduct '' 'uninstall.log'
    }
    if ($tiltOldProduct -and $tiltInstaller.ProductState($tiltOldProduct) -eq 5) {
        $tiltRegisteredPath = (Get-ItemProperty 'HKCU:\Software\EFTX\Tilt').InstallLocation
        if ($tiltRegisteredPath.TrimEnd('\') -ne $tiltOldInstall) { throw 'Local da versao anterior mudou; limpeza cancelada.' }
        $tiltResults.uninstall_previous = Invoke-Msi '/x' $tiltOldProduct '' 'uninstall-previous.log'
    }
    if (Test-Path 'HKCU:\Software\EFTX\TiltSetup') {
        if ((Get-ItemProperty 'HKCU:\Software\EFTX\TiltSetup').InstallLocation -ne $tiltInstall) { throw 'Legacy EXE path changed; cleanup cancelled.' }
        $tiltResults.uninstall_legacy = Invoke-Exe "$tiltInstall\Desinstalar.exe" '/S'
    }
    $tiltResults.finished_utc = [DateTime]::UtcNow.ToString('o')
    $tiltResults | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath "$tiltRun\results.json" -Encoding UTF8
}
if ($tiltResults.uninstall -notin @(0,3010) -or $tiltInstaller.ProductState($tiltProduct) -ne -1 -or (Test-Path -LiteralPath "$tiltInstall\EFTX_Tilt.exe")) { throw 'Desinstalação incompleta.' }
if (-not (Test-Path -LiteralPath "$tiltInstall\user-added.txt")) { throw 'Arquivo extra do usuário foi removido.' }
$tiltAfter = Get-PreservedFiles
foreach ($tiltPath in $tiltBefore.Keys) {
    if ($tiltBefore[$tiltPath] -ne $tiltAfter[$tiltPath]) { throw "Arquivo preexistente alterado: $tiltPath" }
}
$tiltResults.preserved_files = $tiltBefore.Count
$tiltResults.extra_file_preserved = $true
$tiltResults | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath "$tiltRun\results.json" -Encoding UTF8
$tiltResults | ConvertTo-Json -Depth 5
