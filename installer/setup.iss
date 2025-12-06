; YouTube Downloader Pro Installer Script
; Inno Setup Script for creating Windows installer

#define MyAppName "YouTube Downloader Pro"
#define MyAppVersion GetEnv('AppVersion')
#if MyAppVersion == ""
  #define MyAppVersion "2.0.0"
#endif
#define MyAppPublisher "YouTube Downloader Pro"
#define MyAppURL "https://github.com/mahmoodhamdi/youtube-downloader-gui"
#define MyAppExeName "YouTubeDownloaderPro.exe"

[Setup]
; Application information
AppId={{8F4E2C1A-5B3D-4E7F-9A1B-2C3D4E5F6A7B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; Installation directories
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; Output settings
OutputDir=Output
OutputBaseFilename=YouTubeDownloaderPro-Setup
SetupIconFile=..\assets\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes

; Privileges
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Visual settings
WizardStyle=modern
WizardResizable=no

; Minimum Windows version (Windows 10)
MinVersion=10.0

; Uninstaller
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; Main application files
Source: "..\dist\YouTubeDownloaderPro\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Documentation
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion; DestName: "README.txt"
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
// Check if FFmpeg is installed
function FFmpegInstalled(): Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec('cmd.exe', '/c ffmpeg -version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
end;

// Show FFmpeg recommendation after installation
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    if not FFmpegInstalled() then
    begin
      MsgBox('FFmpeg is not installed on your system.' + #13#10 + #13#10 +
             'For best video quality and format support, we recommend installing FFmpeg.' + #13#10 + #13#10 +
             'Download from: https://ffmpeg.org/download.html', mbInformation, MB_OK);
    end;
  end;
end;
