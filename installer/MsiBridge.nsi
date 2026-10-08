; Compatibility entry point for the 1.4.0 EXE-only updater. The MSI owns every
; installed file, shortcut, registration and rollback. This bridge only stages
; the exact embedded MSI and runs Windows Installer.
Unicode true
RequestExecutionLevel user
ManifestSupportedOS all
SilentInstall silent
SetCompressor /SOLID lzma
Name "EFTX Tilt ${VERSION}"
OutFile "${OUTPUT}"
VIProductVersion "${VERSION}.0"
VIAddVersionKey /LANG=1046 "ProductName" "EFTX Tilt"
VIAddVersionKey /LANG=1046 "FileDescription" "Instalador MSI EFTX Tilt"
VIAddVersionKey /LANG=1046 "FileVersion" "${VERSION}"
VIAddVersionKey /LANG=1046 "LegalCopyright" "Copyright EFTX ANTENNAS"
!include LogicLib.nsh
!include FileFunc.nsh
!include x64.nsh
Icon "${ASSETS}\eftx.ico"
Var Unattended

Function .onInit
  ${IfNot} ${RunningX64}
    MessageBox MB_OK|MB_ICONSTOP "Requer Windows 10/11 de 64 bits." /SD IDOK
    SetErrorLevel 1633
    Quit
  ${EndIf}
  ${GetParameters} $0
  StrCpy $Unattended "0"
  ${GetOptions} $0 "/S" $3
  ${IfNot} ${Errors}
    StrCpy $Unattended "1"
  ${EndIf}
  ClearErrors
  ${GetOptions} $0 "/WAITPID=" $1
  ClearErrors
  ${If} $1 != ""
    System::Call 'kernel32::OpenProcess(i 0x00100000, i 0, i r1) p .r2'
    ${If} $2 P<> 0
      System::Call 'kernel32::WaitForSingleObject(p r2, i 60000) i .r3'
      System::Call 'kernel32::CloseHandle(p r2)'
      ${If} $3 != 0
        MessageBox MB_OK|MB_ICONSTOP "Salve seu cálculo e feche o EFTX Tilt antes de atualizar." /SD IDOK
        SetErrorLevel 1618
        Quit
      ${EndIf}
    ${EndIf}
  ${EndIf}
FunctionEnd

Section
  ; Keep the MSI available to Windows Installer for later repair.
  SetOutPath "$LOCALAPPDATA\EFTX\Installers\${VERSION}"
  ClearErrors
  File /oname=EFTX_Tilt-${VERSION}-Windows-x64.msi "${MSI}"
  IfErrors staging_failed
  ${GetParameters} $0
  ${GetOptions} $0 "/ACCEPTEULA=" $1
  ClearErrors
  ${If} $1 == "1"
    ; Explicit unattended authorization; preserve the old updater's CLI.
    ExecWait '"$WINDIR\System32\msiexec.exe" /i "$OUTDIR\EFTX_Tilt-${VERSION}-Windows-x64.msi" /qn /norestart EFTX_ACCEPT_LICENSE=1 /L*v "$TEMP\EFTX_Tilt-${VERSION}-install.log"' $2
  ${Else}
    ${If} $Unattended == "1"
      SetErrorLevel 1603
      Goto done
    ${EndIf}
    ; Default is the full MSI license/installation wizard, even though the
    ; bridge itself has no redundant NSIS pages.
    ExecWait '"$WINDIR\System32\msiexec.exe" /i "$OUTDIR\EFTX_Tilt-${VERSION}-Windows-x64.msi" /norestart /L*v "$TEMP\EFTX_Tilt-${VERSION}-install.log"' $2
  ${EndIf}
  IfErrors staging_failed
  SetErrorLevel $2
  ${If} $2 != 0
  ${AndIf} $2 != 3010
  ${AndIf} $2 != 1602
    MessageBox MB_OK|MB_ICONSTOP "A instalação MSI não foi concluída. Código: $2. Detalhes: $TEMP\EFTX_Tilt-${VERSION}-install.log" /SD IDOK
  ${EndIf}
  Goto done
staging_failed:
  MessageBox MB_OK|MB_ICONSTOP "Não foi possível preparar ou iniciar o MSI. Verifique o espaço livre e execute o arquivo MSI da release." /SD IDOK
  SetErrorLevel 1603
done:
SectionEnd
