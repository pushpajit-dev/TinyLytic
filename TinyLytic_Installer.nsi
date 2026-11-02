; NSIS (Nullsoft Scriptable Install System) Script for TinyLytic Studio
; Generates standalone Windows installer with runtime checks and clean uninstaller

!define PRODUCT_NAME "TinyLytic Studio"
!define PRODUCT_VERSION "3.0"
!define PRODUCT_PUBLISHER "Aivory Products"
!define PRODUCT_WEB_SITE "https://github.com/pushpajit-dev/timelytic"
!define PRODUCT_DIR_REGKEY "Software\Microsoft\Windows\CurrentVersion\App Paths\Launch_TinyLytic.bat"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"

SetCompressor /SOLID lzma
Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "TinyLytic_Setup_v3.0.exe"
InstallDir "$LOCALAPPDATA\TinyLytic_Studio"
InstallDirRegKey HKCU "${PRODUCT_DIR_REGKEY}" ""
ShowInstDetails show
ShowUnInstDetails show

; Interface Settings
!include "MUI2.nsh"
!define MUI_ABORTWARNING
!define MUI_ICON "app_icon.ico"
!define MUI_UNICON "app_icon.ico"

; Installer Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN "$INSTDIR\Launch_TinyLytic.bat"
!insertmacro MUI_PAGE_FINISH

; Uninstaller Pages
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

Section "MainSection" SEC01
  SetOutPath "$INSTDIR"
  SetOverwrite ifnewer

  ; Copy Python Sources & Modules
  File "Tinylytic.py"
  File "core_engine.py"
  File "vision_engine.py"
  File "chat_engine.py"
  File "workers.py"
  File "more2.py"
  File "requirements.txt"
  File "app_icon.ico"
  File "activated.flag"
  File "installer_wizard.py"
  File "install.bat"
  File "test_and_run.bat"

  ; Copy Directories
  File /r "assets"
  File /r "models"
  File /r "lang_models"

  ; Create Launcher Batch
  FileOpen $0 "$INSTDIR\Launch_TinyLytic.bat" w
  FileWrite $0 "@echo off$\r$\n"
  FileWrite $0 "cd /d $\"$INSTDIR$\"$\r$\n"
  FileWrite $0 "start $\"$\" python $\"Tinylytic.py$\" %*$\r$\n"
  FileClose $0

  ; Create Shortcuts
  CreateDirectory "$SMPROGRAMS\TinyLytic"
  CreateShortcut "$SMPROGRAMS\TinyLytic\TinyLytic Studio.lnk" "$INSTDIR\Launch_TinyLytic.bat" "" "$INSTDIR\app_icon.ico"
  CreateShortcut "$SMPROGRAMS\TinyLytic\Uninstall TinyLytic.lnk" "$INSTDIR\uninstaller.exe"
  CreateShortcut "$DESKTOP\TinyLytic Studio.lnk" "$INSTDIR\Launch_TinyLytic.bat" "" "$INSTDIR\app_icon.ico"

  ; Create Uninstaller
  WriteUninstaller "$INSTDIR\uninstaller.exe"

  ; Registry Keys
  WriteRegStr HKCU "${PRODUCT_DIR_REGKEY}" "" "$INSTDIR\Launch_TinyLytic.bat"
  WriteRegStr HKCU "${PRODUCT_UNINST_KEY}" "DisplayName" "${PRODUCT_NAME}"
  WriteRegStr HKCU "${PRODUCT_UNINST_KEY}" "UninstallString" "$INSTDIR\uninstaller.exe"
  WriteRegStr HKCU "${PRODUCT_UNINST_KEY}" "DisplayIcon" "$INSTDIR\app_icon.ico"
  WriteRegStr HKCU "${PRODUCT_UNINST_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
  WriteRegStr HKCU "${PRODUCT_UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
SectionEnd

; Check for Python runtime on installation start
Function .onInit
  nsExec::ExecToStack 'python.exe --version'
  Pop $0
  Pop $1
  StrCmp $0 "0" python_found

  nsExec::ExecToStack 'py.exe -3 --version'
  Pop $0
  Pop $1
  StrCmp $0 "0" python_found

  MessageBox MB_YESNO|MB_ICONEXCLAMATION "Python 3 was not detected on your system.$\r$\nTinyLytic requires Python 3.10+ to run AI models and speech processing.$\r$\n$\r$\nDo you want to continue installation anyway?" IDYES continue_install
  Abort

python_found:
continue_install:
FunctionEnd

; Uninstaller Section
Section Uninstall
  Delete "$DESKTOP\TinyLytic Studio.lnk"
  Delete "$SMPROGRAMS\TinyLytic\TinyLytic Studio.lnk"
  Delete "$SMPROGRAMS\TinyLytic\Uninstall TinyLytic.lnk"
  RMDir "$SMPROGRAMS\TinyLytic"

  ; Clean cache
  RMDir /r "$LOCALAPPDATA\TinyLytic"
  RMDir /r "$TEMP\TinyLytic_Temp"

  ; Clean App Dir
  RMDir /r "$INSTDIR"

  DeleteRegKey HKCU "${PRODUCT_UNINST_KEY}"
  DeleteRegKey HKCU "${PRODUCT_DIR_REGKEY}"

  SetAutoClose true
SectionEnd
