; Open Deck for MSFS — установщик (NSIS 3, Unicode).
;
; Ставится в профиль пользователя (%LOCALAPPDATA%), права администратора
; не нужны. Внутри — самодостаточный .exe (Python + шлюз), статика клиента,
; профили, манифест целостности и деинсталлятор.
;
; Сборка: makensis /DPRODUCT_VERSION=0.1.0 installer.nsi
; (обычно вызывается из scripts/build-installer.ps1)

Unicode true
!include "MUI2.nsh"
!include "FileFunc.nsh"

!ifndef PRODUCT_VERSION
  !define PRODUCT_VERSION "0.1.0"
!endif

!define PRODUCT_NAME "Open Deck for MSFS"
!define PRODUCT_PUBLISHER "Viktor Krasnikov"
!define PRODUCT_EXE "OpenDeck.exe"
!define UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\OpenDeck"
!define APP_SRC "..\..\build\pyinstaller\dist\OpenDeck"
!define ROOT_SRC "..\.."

Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
!ifndef OUTFILE
  !define OUTFILE "..\..\dist\OpenDeck-Setup-${PRODUCT_VERSION}.exe"
!endif
OutFile "${OUTFILE}"
InstallDir "$LOCALAPPDATA\OpenDeck"
InstallDirRegKey HKCU "Software\OpenDeck" "InstallDir"
RequestExecutionLevel user
SetCompressor /SOLID lzma
SetCompressorDictSize 32
BrandingText "${PRODUCT_NAME}"

VIProductVersion "${PRODUCT_VERSION}.0"
VIAddVersionKey "ProductName" "${PRODUCT_NAME}"
VIAddVersionKey "ProductVersion" "${PRODUCT_VERSION}"
VIAddVersionKey "FileDescription" "Локальный шлюз приборных панелей MSFS"
VIAddVersionKey "FileVersion" "${PRODUCT_VERSION}"
VIAddVersionKey "LegalCopyright" "${PRODUCT_PUBLISHER}"

!define MUI_ICON "open-deck.ico"
!define MUI_UNICON "open-deck.ico"
Icon "open-deck.ico"
UninstallIcon "open-deck.ico"
!define MUI_ABORTWARNING
!define MUI_FINISHPAGE_RUN "$INSTDIR\${PRODUCT_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT "Запустить ${PRODUCT_NAME}"
!define MUI_FINISHPAGE_SHOWREADME "$INSTDIR\README.md"
!define MUI_FINISHPAGE_SHOWREADME_TEXT "Открыть README (как подключить клиентов)"
!define MUI_FINISHPAGE_SHOWREADME_NOTCHECKED

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "Russian"
!insertmacro MUI_LANGUAGE "English"

; ---------------------------------------------------------------- установка
Section "Приложение" SecMain
  SetShellVarContext current
  SetOutPath "$INSTDIR"

  ; Сам exe и встроенный Python (_internal).
  File /r "${APP_SRC}\*.*"

  ; Данные рядом с exe: статика клиента, профили, реквизиты, манифест.
  SetOutPath "$INSTDIR\web"
  File /r "${ROOT_SRC}\web\*.*"
  SetOutPath "$INSTDIR\profiles"
  File /r "${ROOT_SRC}\profiles\*.*"
  SetOutPath "$INSTDIR\config"
  File /r "${ROOT_SRC}\config\*.*"
  SetOutPath "$INSTDIR\integrity"
  File /r "${ROOT_SRC}\integrity\*.*"

  ; Android-проект и готовый APK: можно собрать свой APK из дистрибутива
  ; (нужны JDK 17, Android SDK и Gradle) или установить готовый.
  SetOutPath "$INSTDIR\android"
  File /r /x build /x .gradle /x local.properties /x "app\build" "${ROOT_SRC}\android\*.*"

  SetOutPath "$INSTDIR"
  File /r "${ROOT_SRC}\docs"
  File "${ROOT_SRC}\LICENSE"
  File "${ROOT_SRC}\README.md"

  WriteUninstaller "$INSTDIR\Uninstall.exe"

  ; Ярлыки: запуск приложения и быстрый доступ к панели в браузере.
  CreateShortcut "$DESKTOP\${PRODUCT_NAME}.lnk" "$INSTDIR\${PRODUCT_EXE}" "" "$INSTDIR\${PRODUCT_EXE}" 0
  CreateDirectory "$SMPROGRAMS\${PRODUCT_NAME}"
  CreateShortcut "$SMPROGRAMS\${PRODUCT_NAME}\${PRODUCT_NAME}.lnk" "$INSTDIR\${PRODUCT_EXE}"
  CreateShortcut "$SMPROGRAMS\${PRODUCT_NAME}\Задать пароль.lnk" "$INSTDIR\${PRODUCT_EXE}" "--set-password" "$INSTDIR\${PRODUCT_EXE}" 0
  WriteINIStr "$SMPROGRAMS\${PRODUCT_NAME}\Панель в браузере.url" "InternetShortcut" "URL" "http://127.0.0.1:8760/"
  WriteINIStr "$SMPROGRAMS\${PRODUCT_NAME}\Собрать Android APK.url" "InternetShortcut" "URL" "http://127.0.0.1:8760/android.html"
  CreateShortcut "$SMPROGRAMS\${PRODUCT_NAME}\Удалить ${PRODUCT_NAME}.lnk" "$INSTDIR\Uninstall.exe"

  WriteRegStr HKCU "Software\OpenDeck" "InstallDir" "$INSTDIR"
  WriteRegStr HKCU "${UNINST_KEY}" "DisplayName" "${PRODUCT_NAME}"
  WriteRegStr HKCU "${UNINST_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
  WriteRegStr HKCU "${UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
  WriteRegStr HKCU "${UNINST_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${UNINST_KEY}" "DisplayIcon" "$INSTDIR\${PRODUCT_EXE}"
  WriteRegStr HKCU "${UNINST_KEY}" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegStr HKCU "${UNINST_KEY}" "QuietUninstallString" '"$INSTDIR\Uninstall.exe" /S'
  WriteRegDWORD HKCU "${UNINST_KEY}" "NoModify" 1
  WriteRegDWORD HKCU "${UNINST_KEY}" "NoRepair" 1

  ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
  IntFmt $0 "0x%08X" $0
  WriteRegDWORD HKCU "${UNINST_KEY}" "EstimatedSize" "$0"
SectionEnd

; -------------------------------------------------------------- удаление
Section "Uninstall"
  SetShellVarContext current

  ; Если приложение запущено, файлы заняты — закрываем.
  ExecWait '"$SYSDIR\taskkill.exe" /IM ${PRODUCT_EXE} /F'

  Delete "$DESKTOP\${PRODUCT_NAME}.lnk"
  Delete "$SMPROGRAMS\${PRODUCT_NAME}\${PRODUCT_NAME}.lnk"
  Delete "$SMPROGRAMS\${PRODUCT_NAME}\Задать пароль.lnk"
  Delete "$SMPROGRAMS\${PRODUCT_NAME}\Панель в браузере.url"
  Delete "$SMPROGRAMS\${PRODUCT_NAME}\Собрать Android APK.url"
  Delete "$SMPROGRAMS\${PRODUCT_NAME}\Удалить ${PRODUCT_NAME}.lnk"
  RMDir "$SMPROGRAMS\${PRODUCT_NAME}"

  DeleteRegKey HKCU "${UNINST_KEY}"
  DeleteRegKey HKCU "Software\OpenDeck"

  RMDir /r "$INSTDIR"
SectionEnd
