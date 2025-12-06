; YouTube Downloader Pro Installer Script
; Inno Setup Script for creating Windows installer
; With automatic FFmpeg download support

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
; SetupIconFile=..\assets\icon.ico  ; Uncomment if you have an icon file
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
Name: "installffmpeg"; Description: "Download and install FFmpeg (recommended for best quality)"; GroupDescription: "Additional Components:"; Flags: unchecked

[Files]
; Main application files
Source: "..\dist\YouTubeDownloaderPro\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; FFmpeg installer script
Source: "scripts\install_ffmpeg.ps1"; DestDir: "{app}\scripts"; Flags: ignoreversion

; Documentation
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion; DestName: "README.txt"
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Install FFmpeg"; Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{app}\scripts\install_ffmpeg.ps1"""; WorkingDir: "{app}\scripts"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Install FFmpeg if selected
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{app}\scripts\install_ffmpeg.ps1"""; StatusMsg: "Installing FFmpeg..."; Flags: runhidden; Tasks: installffmpeg
; Launch application
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
var
  FFmpegPage: TWizardPage;
  FFmpegStatusLabel: TLabel;
  FFmpegInstallButton: TButton;
  FFmpegSkipButton: TButton;
  FFmpegFound: Boolean;

// Check if FFmpeg is installed
function IsFFmpegInstalled(): Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec('cmd.exe', '/c ffmpeg -version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
end;

// Check if internet is available
function IsInternetAvailable(): Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec('cmd.exe', '/c ping -n 1 github.com', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
end;

// Initialize wizard
procedure InitializeWizard();
begin
  FFmpegFound := IsFFmpegInstalled();
end;

// Check dependencies after installation
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  Msg: String;
begin
  if CurStep = ssPostInstall then
  begin
    // Check FFmpeg again after installation
    if not IsFFmpegInstalled() then
    begin
      if not WizardIsTaskSelected('installffmpeg') then
      begin
        Msg := 'FFmpeg is not installed on your system.' + #13#10 + #13#10 +
               'FFmpeg is recommended for:' + #13#10 +
               '  - Best video/audio quality' + #13#10 +
               '  - Format conversion' + #13#10 +
               '  - Merging video and audio streams' + #13#10 + #13#10 +
               'Would you like to install FFmpeg now?' + #13#10 + #13#10 +
               '(Requires internet connection, ~130 MB download)';

        if MsgBox(Msg, mbConfirmation, MB_YESNO) = IDYES then
        begin
          // Run FFmpeg installer
          if IsInternetAvailable() then
          begin
            Exec('powershell.exe',
                 '-ExecutionPolicy Bypass -File "' + ExpandConstant('{app}') + '\scripts\install_ffmpeg.ps1"',
                 '', SW_SHOW, ewWaitUntilTerminated, ResultCode);

            if ResultCode = 0 then
              MsgBox('FFmpeg installed successfully!' + #13#10 + #13#10 +
                     'You may need to restart the application for changes to take effect.',
                     mbInformation, MB_OK)
            else
              MsgBox('FFmpeg installation failed.' + #13#10 + #13#10 +
                     'You can install it later from:' + #13#10 +
                     'Start Menu > YouTube Downloader Pro > Install FFmpeg' + #13#10 + #13#10 +
                     'Or download manually from: https://ffmpeg.org/download.html',
                     mbInformation, MB_OK);
          end
          else
          begin
            MsgBox('No internet connection detected.' + #13#10 + #13#10 +
                   'You can install FFmpeg later when connected:' + #13#10 +
                   'Start Menu > YouTube Downloader Pro > Install FFmpeg' + #13#10 + #13#10 +
                   'Or download manually from: https://ffmpeg.org/download.html',
                   mbInformation, MB_OK);
          end;
        end
        else
        begin
          MsgBox('You can install FFmpeg later from:' + #13#10 +
                 'Start Menu > YouTube Downloader Pro > Install FFmpeg' + #13#10 + #13#10 +
                 'The application will work without FFmpeg, but some features ' +
                 'like format conversion and best quality downloads may be limited.',
                 mbInformation, MB_OK);
        end;
      end;
    end
    else
    begin
      // FFmpeg is installed
      if not WizardSilent() then
      begin
        MsgBox('FFmpeg detected!' + #13#10 + #13#10 +
               'Your system is ready for the best video downloading experience.',
               mbInformation, MB_OK);
      end;
    end;
  end;
end;

// Custom pre-install check
function InitializeSetup(): Boolean;
begin
  Result := True;
end;

// Show warning if FFmpeg not found during task selection
function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;
end;
