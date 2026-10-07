param([string]$Version = '1.3.0')
$ErrorActionPreference = 'Stop'
$tiltRoot = Split-Path -Parent $PSScriptRoot
$tiltMsi = Join-Path $tiltRoot "dist\EFTX_Tilt-$Version-Windows-x64.msi"
$tiltManifestPath = Join-Path $tiltRoot "build\installer\$Version\payload-manifest.json"
$tiltManifest = Get-Content -LiteralPath $tiltManifestPath -Raw | ConvertFrom-Json
$tiltRun = Join-Path $tiltRoot ('.artifacts\msi-test-' + [Guid]::NewGuid().ToString('N'))
$tiltInstall = Join-Path $tiltRun 'installed'
New-Item -ItemType Directory -Path $tiltRun | Out-Null
$tiltInstaller = New-Object -ComObject WindowsInstaller.Installer
$tiltDatabase = $tiltInstaller.OpenDatabase($tiltMsi, 0)
$tiltView = $tiltDatabase.OpenView('SELECT `Value` FROM `Property` WHERE `Property` = ''ProductCode''')
$tiltView.Execute()
$tiltProduct = $tiltView.Fetch().StringData(1)
$tiltView.Close()
if ($tiltInstaller.ProductState($tiltProduct) -ne -1) { throw 'Produto já registrado. Teste deve começar sem esta instalação MSI.' }
foreach ($tiltShortcut in @(
    "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\EFTX\EFTX Tilt.lnk",
    "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\EFTX\Licen$([char]0x00e7)a EFTX Tilt.lnk",
    (Join-Path ([Environment]::GetFolderPath('Desktop')) 'EFTX Tilt.lnk')
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
$tiltBefore = Get-PreservedFiles
$tiltBefore | ConvertTo-Json | Set-Content -LiteralPath "$tiltRun\preserved-before.json" -Encoding UTF8
$tiltResults = [ordered]@{version=$Version; product=$tiltProduct; run=$tiltRun; started_utc=[DateTime]::UtcNow.ToString('o')}
$tiltOldPlatform = $env:QT_QPA_PLATFORM
try {
    $tiltResults.license_rejection = Invoke-Msi '/i' $tiltMsi "INSTALLFOLDER=`"$tiltInstall`"" 'license-rejected.log'
    if ($tiltResults.license_rejection -ne 1603 -or (Test-Path -LiteralPath "$tiltInstall\EFTX_Tilt.exe")) { throw 'Instalação sem aceite não foi bloqueada.' }
    if (-not (Select-String -LiteralPath "$tiltRun\license-rejected.log" -Pattern 'EFTX_ACCEPT_LICENSE=1' -Quiet)) { throw 'Falha não identificada como falta de aceite.' }
    $tiltResults.install = Invoke-Msi '/i' $tiltMsi "EFTX_ACCEPT_LICENSE=1 INSTALLFOLDER=`"$tiltInstall`"" 'install.log'
    if ($tiltResults.install -notin @(0,3010)) { throw "Falha de instalação: $($tiltResults.install)" }
    foreach ($tiltItem in $tiltManifest.files) {
        $tiltFile = Join-Path $tiltInstall $tiltItem.path
        if ((Get-FileHash -LiteralPath $tiltFile -Algorithm SHA256).Hash -ne $tiltItem.sha256) { throw "Hash instalado divergente: $tiltFile" }
    }
    $tiltResults.verified_files = $tiltManifest.files.Count
    'user-owned fixture' | Set-Content -LiteralPath "$tiltInstall\user-added.txt"
    foreach ($tiltPlatform in @('offscreen', 'windows')) {
        $env:QT_QPA_PLATFORM = $tiltPlatform
        $tiltSmoke = Start-Process -FilePath "$tiltInstall\EFTX_Tilt.exe" -ArgumentList "--smoke-test --database `"$tiltRun\$tiltPlatform.sqlite3`" --smoke-pdf `"$tiltRun\$tiltPlatform.pdf`"" -WindowStyle Hidden -PassThru -Wait
        $tiltResults["smoke_$tiltPlatform"] = $tiltSmoke.ExitCode
        if ($tiltSmoke.ExitCode -ne 0 -or -not (Test-Path -LiteralPath "$tiltRun\$tiltPlatform.pdf")) { throw "Falha no aplicativo instalado: $tiltPlatform" }
    }
    # Exercise repair of one owned test file; never touch real user data.
    $tiltLicense = (Resolve-Path -LiteralPath "$tiltInstall\LICENSE.txt").Path
    if (-not $tiltLicense.StartsWith($tiltRun + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Caminho de teste inválido.' }
    Remove-Item -LiteralPath $tiltLicense
    $tiltResults.repair = Invoke-Msi '/fa' $tiltProduct '' 'repair.log'
    if ($tiltResults.repair -notin @(0,3010) -or -not (Test-Path -LiteralPath $tiltLicense)) { throw 'Reparação não restaurou a licença.' }
} finally {
    $env:QT_QPA_PLATFORM = $tiltOldPlatform
    if ($tiltInstaller.ProductState($tiltProduct) -eq 5) {
        $tiltRegisteredPath = (Get-ItemProperty 'HKCU:\Software\EFTX\Tilt').InstallLocation
        if ($tiltRegisteredPath.TrimEnd('\') -ne $tiltInstall) { throw 'Local registrado mudou; desinstalação automática cancelada.' }
        $tiltResults.uninstall = Invoke-Msi '/x' $tiltProduct '' 'uninstall.log'
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
