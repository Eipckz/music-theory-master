; Inno Setup script for Music Theory Master.
; Wraps the PyInstaller onefile exe (dist\MusicTheoryMaster.exe) into a
; per-user installer with Start-menu shortcut and uninstaller.
; Build:  ISCC.exe /DMyAppVersion=1.0.0 installer\MusicTheoryMaster.iss

#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif
#define MyAppName "Music Theory Master"
#define MyAppExeName "MusicTheoryMaster.exe"
#define MyAppPublisher "Eipckz"
#define MyAppURL "https://github.com/Eipckz/music-theory-master"

[Setup]
AppId={{B1E6C3D4-7A52-4E0B-9C1D-2F84A35D9E61}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; per-user install: no admin prompt, lands under %LocalAppData%\Programs
PrivilegesRequired=lowest
OutputDir=Output
OutputBaseFilename=MusicTheoryMaster-Setup
SetupIconFile=..\music_theory\resources\icons\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
