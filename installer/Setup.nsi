; -*- coding: utf-8 -*-
Unicode true
RequestExecutionLevel user
ManifestSupportedOS all
ManifestDPIAware true
SetCompressor /SOLID lzma
SetCompressorDictSize 32
AllowSkipFiles off
Name "EFTX Tilt ${VERSION}"
OutFile "${OUTPUT}"
InstallDir "$LOCALAPPDATA\Programs\EFTX\Tilt-Desktop"
InstallDirRegKey HKCU "Software\EFTX\TiltSetup" "InstallLocation"
BrandingText "EFTX ANTENNAS"
VIProductVersion "${VERSION}.0"
VIAddVersionKey /LANG=1046 "ProductName" "EFTX Tilt"
VIAddVersionKey /LANG=1046 "FileDescription" "Instalador offline EFTX Tilt"
VIAddVersionKey /LANG=1046 "FileVersion" "${VERSION}"
VIAddVersionKey /LANG=1046 "LegalCopyright" "Copyright EFTX ANTENNAS"

!include MUI2.nsh
!include x64.nsh
!include LogicLib.nsh
!include FileFunc.nsh
!define MUI_ICON "${ASSETS}\eftx.ico"
!define MUI_UNICON "${ASSETS}\eftx.ico"
!define MUI_ABORTWARNING
!define MUI_LICENSEPAGE_CHECKBOX
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "${ASSETS}\license.rtf"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "PortugueseBR"

Function .onInit
  SetShellVarContext current
  SetRegView 64
  ${IfNot} ${RunningX64}
    MessageBox MB_OK|MB_ICONSTOP "Este aplicativo requer Windows 10/11 de 64 bits." /SD IDOK
    SetErrorLevel 1633
    Quit
  ${EndIf}
  ReadRegStr $0 HKLM "SOFTWARE\Microsoft\Windows NT\CurrentVersion" "CurrentBuildNumber"
  ${If} $0 < 17763
    MessageBox MB_OK|MB_ICONSTOP "Requer Windows 10 versão 1809 ou posterior (64 bits), ou Windows 11." /SD IDOK
    SetErrorLevel 1633
    Quit
  ${EndIf}
  ; The updater starts this wizard, saves its project and exits. Wait for the
  ; application process to release its executable and Qt DLLs before copying.
  ${GetParameters} $0
  ${GetOptions} $0 "/WAITPID=" $1
  ClearErrors ; An absent optional switch is not a failed installation.
  ${If} $1 != ""
    System::Call 'kernel32::OpenProcess(i 0x00100000, i 0, i r1) p .r2'
    ${If} $2 P<> 0
      System::Call 'kernel32::WaitForSingleObject(p r2, i 60000) i .r3'
      System::Call 'kernel32::CloseHandle(p r2)'
      ${If} $3 != 0
        MessageBox MB_OK|MB_ICONSTOP "Feche o EFTX Tilt antes de atualizar e execute o instalador novamente." /SD IDOK
        SetErrorLevel 1618
        Quit
      ${EndIf}
    ${Else}
      System::Call 'kernel32::GetLastError() i .r3'
      ${If} $3 != 87
        MessageBox MB_OK|MB_ICONSTOP "Não foi possível confirmar o fechamento do EFTX Tilt. Feche o aplicativo e tente novamente." /SD IDOK
        SetErrorLevel 1618
        Quit
      ${EndIf}
    ${EndIf}
  ${EndIf}
  ${If} ${Silent}
    ${GetParameters} $0
    ${GetOptions} $0 "/ACCEPTEULA=" $1
    ${If} $1 != "1"
      SetErrorLevel 1603
      Quit
    ${EndIf}
  ${EndIf}
FunctionEnd

Function .onVerifyInstDir
  ${GetRoot} "$INSTDIR" $0
  ${If} $INSTDIR == $0
  ${OrIf} $INSTDIR == "$WINDIR"
  ${OrIf} $INSTDIR == "$LOCALAPPDATA\EFTX\EFTX Tilt"
    Abort
  ${EndIf}
FunctionEnd

Section "EFTX Tilt" Main
  SetShellVarContext current
  SetRegView 64
  SetOverwrite on
  ClearErrors
  !include "${ASSETS}\InstallFiles.nsh"
  WriteUninstaller "$INSTDIR\Desinstalar.exe"
  IfErrors install_failed
  WriteINIStr "$INSTDIR\.eftx-install.ini" "EFTX" "Product" "EFTX-TILT-SETUP-01"
  WriteINIStr "$INSTDIR\.eftx-install.ini" "EFTX" "Version" "${VERSION}"
  WriteRegStr HKCU "Software\EFTX\TiltSetup" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "Software\EFTX\TiltSetup" "Version" "${VERSION}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\EFTXTiltDesktop" "DisplayName" "EFTX Tilt Desktop"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\EFTXTiltDesktop" "DisplayVersion" "${VERSION}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\EFTXTiltDesktop" "Publisher" "EFTX ANTENNAS"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\EFTXTiltDesktop" "UninstallString" '$\"$INSTDIR\Desinstalar.exe$\"'
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\EFTXTiltDesktop" "QuietUninstallString" '$\"$INSTDIR\Desinstalar.exe$\" /S'
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\EFTXTiltDesktop" "DisplayIcon" "$INSTDIR\EFTX_Tilt.exe"
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\EFTXTiltDesktop" "NoModify" 1
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\EFTXTiltDesktop" "NoRepair" 1
  CreateDirectory "$SMPROGRAMS\EFTX Tilt Desktop"
  CreateShortcut "$SMPROGRAMS\EFTX Tilt Desktop\EFTX Tilt.lnk" "$INSTDIR\EFTX_Tilt.exe"
  CreateShortcut "$SMPROGRAMS\EFTX Tilt Desktop\Desinstalar.lnk" "$INSTDIR\Desinstalar.exe"
  CreateShortcut "$DESKTOP\EFTX Tilt Desktop.lnk" "$INSTDIR\EFTX_Tilt.exe"
  IfErrors install_failed
  SetErrorLevel 0
  Goto install_done
install_failed:
  MessageBox MB_OK|MB_ICONSTOP "Não foi possível copiar todos os arquivos. Feche o EFTX Tilt e execute o instalador novamente." /SD IDOK
  SetErrorLevel 1
  Abort
install_done:
SectionEnd

Function un.onInit
  SetShellVarContext current
  SetRegView 64
  ReadINIStr $0 "$INSTDIR\.eftx-install.ini" "EFTX" "Product"
  ReadRegStr $1 HKCU "Software\EFTX\TiltSetup" "InstallLocation"
  ${If} $0 != "EFTX-TILT-SETUP-01"
  ${OrIf} $1 != $INSTDIR
    MessageBox MB_OK|MB_ICONSTOP "Pasta de instalação não reconhecida. Nenhum arquivo foi removido." /SD IDOK
    SetErrorLevel 1
    Quit
  ${EndIf}
FunctionEnd

Section "Uninstall"
  SetShellVarContext current
  SetRegView 64
  !include "${ASSETS}\UninstallFiles.nsh"
  Delete "$INSTDIR\.eftx-install.ini"
  Delete "$INSTDIR\Desinstalar.exe"
  Delete "$SMPROGRAMS\EFTX Tilt Desktop\EFTX Tilt.lnk"
  Delete "$SMPROGRAMS\EFTX Tilt Desktop\Desinstalar.lnk"
  Delete "$DESKTOP\EFTX Tilt Desktop.lnk"
  RMDir "$SMPROGRAMS\EFTX Tilt Desktop"
  RMDir "$INSTDIR"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\EFTXTiltDesktop"
  DeleteRegKey HKCU "Software\EFTX\TiltSetup"
  SetErrorLevel 0
  Goto uninstall_done
uninstall_failed:
  MessageBox MB_OK|MB_ICONSTOP "Não foi possível remover todos os arquivos. Feche o EFTX Tilt e tente desinstalar novamente." /SD IDOK
  SetErrorLevel 1
  Abort
uninstall_done:
SectionEnd
