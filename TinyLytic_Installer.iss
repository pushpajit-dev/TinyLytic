; Inno Setup Script for TinyLytic Studio
; Builds a professional standalone Windows setup installer with runtime dependency checks
; Developed by: NoishiXzen & Aivory (https://aivorygen.netlify.app | noishixzen@gmail.com)

#define MyAppName "TinyLytic Studio"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "NoishiXzen & Aivory"
#define MyAppBrand "Aivory"
#define MyAppURL "https://aivorygen.netlify.app"
#define MyAppSupport "https://aivorygen.netlify.app"
#define MyAppContact "noishixzen@gmail.com"
#define MyAppExeName "Launch_TinyLytic.bat"

[Setup]
AppId={{E58E971B-A795-4BD9-9BCE-DF6B8E5F7E81}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppSupport}
AppUpdatesURL={#MyAppURL}
AppContact={#MyAppContact}
DefaultDirName={localappdata}\TinyLytic_Studio
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=Installers_Output
OutputBaseFilename=TinyLytic_Setup_v2.0
SetupIconFile=app_icon.ico
Compression=lzma2/fast
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\app_icon.ico
UninstallDisplayName={#MyAppName} (by {#MyAppPublisher})

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "Tinylytic.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "core_engine.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "vision_engine.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "chat_engine.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "workers.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "video_caption_studio.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "more2.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "app_icon.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "icon.ico"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "activated.flag"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "Activation Key.txt"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "installer_wizard.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "uninstaller.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "uninstall.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "install.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "test_and_run.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "llama.dll"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "llama.lib"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "merges.txt"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "models\tiny.pt"; DestDir: "{app}\models"; Flags: ignoreversion skipifsourcedoesntexist
Source: "models\whisper-medium.pt"; DestDir: "{app}\models"; Flags: ignoreversion skipifsourcedoesntexist
Source: "models\tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"; DestDir: "{app}\models"; Flags: ignoreversion skipifsourcedoesntexist
Source: "assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist
Source: "lang_models\*"; DestDir: "{app}\lang_models"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\Launch_TinyLytic.bat"; IconFilename: "{app}\app_icon.ico"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"; IconFilename: "{app}\app_icon.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\Launch_TinyLytic.bat"; IconFilename: "{app}\app_icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\Launch_TinyLytic.bat"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: shellexec postinstall nowait skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
Type: filesandordirs; Name: "{localappdata}\TinyLytic"
Type: filesandordirs; Name: "{localappdata}\TinyLytic_Studio"
Type: filesandordirs; Name: "{localappdata}\Temp\TinyLytic_Temp"

[Code]
// Check if Python 3.10+ is available
function IsPythonInstalled(): Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec('python.exe', '--version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
  if not Result then
    Result := Exec('py.exe', '-3 --version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
end;

// Check if all Python core libraries are installed
function AreLibrariesInstalled(): Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec('python.exe', '-c "import PyQt6, whisper, torch, sounddevice, soundfile, cv2, requests"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
end;

// Pre-install check for existing installation & runtime dependencies
function InitializeSetup(): Boolean;
var
  InstalledDir: String;
  UninstallerPath: String;
  ResultCode: Integer;
begin
  Result := True;

  // 1. Check if TinyLytic is already installed
  if not RegQueryStringValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#SetupSetting("AppId")}_is1', 'InstallLocation', InstalledDir) then
    InstalledDir := ExpandConstant('{localappdata}\TinyLytic_Studio');

  if FileExists(InstalledDir + '\Tinylytic.py') or FileExists(InstalledDir + '\unins000.exe') then
  begin
    case MsgBox('TinyLytic Studio is already installed on your system at:' + #13#10 +
                InstalledDir + #13#10#13#10 +
                'Choose an option:' + #13#10 +
                '• Click YES to Update / Reinstall TinyLytic Studio.' + #13#10 +
                '• Click NO to launch the Uninstaller to remove TinyLytic Studio.' + #13#10 +
                '• Click CANCEL to exit setup.', mbConfirmation, MB_YESNOCANCEL) of
      IDYES:
        begin
          // Update / Reinstall in-place
          Result := True;
        end;
      IDNO:
        begin
          // Launch uninstaller and exit setup
          UninstallerPath := InstalledDir + '\unins000.exe';
          if not FileExists(UninstallerPath) then
            UninstallerPath := ExpandConstant('{localappdata}\TinyLytic_Studio\unins000.exe');
          if FileExists(UninstallerPath) then
            Exec(UninstallerPath, '', '', SW_SHOW, ewNoWait, ResultCode)
          else if FileExists(InstalledDir + '\uninstall.bat') then
            Exec(InstalledDir + '\uninstall.bat', '', '', SW_SHOW, ewNoWait, ResultCode);
          Result := False;
          Exit;
        end;
      IDCANCEL:
        begin
          Result := False;
          Exit;
        end;
    end;
  end;

  // 2. Check Python installation
  if not IsPythonInstalled() then
  begin
    if MsgBox('Python 3.10+ was not detected on your system.' + #13#10 +
              'TinyLytic Studio requires Python to execute AI models and speech processing.' + #13#10#13#10 +
              'Download Python from https://www.python.org/downloads/' + #13#10#13#10 +
              'Would you like to continue anyway?', mbConfirmation, MB_YESNO) = IDNO then
    begin
      Result := False;
    end;
  end;
end;

// Post-installation step: check and install missing dependencies if needed
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  AppDir: String;
begin
  if CurStep = ssPostInstall then
  begin
    AppDir := ExpandConstant('{app}');
    // Create launcher batch file if missing
    if not FileExists(AppDir + '\Launch_TinyLytic.bat') then
    begin
      SaveStringToFile(AppDir + '\Launch_TinyLytic.bat',
        '@echo off' + #13#10 +
        'cd /d "%~dp0"' + #13#10 +
        'start "" pythonw "Tinylytic.py" %*' + #13#10, False);
    end;

    // Check runtime dependencies: install only if missing
    if not AreLibrariesInstalled() then
    begin
      Exec('python.exe', '-m pip install -r "' + AppDir + '\requirements.txt"', AppDir, SW_SHOW, ewWaitUntilTerminated, ResultCode);
    end;
  end;
end;
