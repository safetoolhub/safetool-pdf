; SafeTool PDF Inno Setup Script
; Copyright (C) 2026 safetoolhub.org
; License: GPL-3.0-or-later
;
; Build with:
;   iscc packaging\windows\safetool-pdf.iss
;
; Environment variables used (set by build.py / GitHub Actions):
;   APP_VERSION       - e.g. "0.1.0"
;   APP_FULL_VERSION  - e.g. "0.1.0-beta"

#ifndef APP_VERSION
  #define APP_VERSION GetEnv("APP_VERSION")
#endif
#ifndef APP_FULL_VERSION
  #define APP_FULL_VERSION GetEnv("APP_FULL_VERSION")
#endif
; Fallback to APP_VERSION when FULL_VERSION is not set
#if APP_FULL_VERSION == ""
  #define APP_FULL_VERSION APP_VERSION
#endif

#define AppName    "SafeTool PDF"
#define AppPublisher "SafeToolHub"
#define AppURL     "https://safetoolhub.org"
#define AppExeName "safetool-pdf-desktop.exe"

; Paths relative to this script (which lives in packaging/windows/)
#define RootDir    "..\.."
#define SourceDir  "..\..\dist\safetool-pdf"
#define OutputDir  "..\..\dist"
#define OutputFile "SafeToolPDF-" + APP_FULL_VERSION + "-windows-setup"

[Setup]
AppId={{A7E1F3B2-4D6C-4E8A-9F0B-1C2D3E4F5A6B}
AppName={#AppName}
AppVersion={#APP_VERSION}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
LicenseFile={#RootDir}\LICENSE
OutputDir={#OutputDir}
OutputBaseFilename={#OutputFile}
SetupIconFile={#RootDir}\assets\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\{#AppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "fileassoc"; Description: "Associate with .pdf files"; GroupDescription: "File associations:"; Flags: unchecked

[Files]
; Bundle all PyInstaller output (exe + _internal/ with libs, data, and vendored GS)
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Registry]
; Optional PDF file association
Root: HKA; Subkey: "Software\Classes\.pdf\OpenWithProgids"; ValueType: string; ValueName: "SafeToolPDF.pdf"; ValueData: ""; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\SafeToolPDF.pdf"; ValueType: string; ValueName: ""; ValueData: "PDF Document"; Flags: uninsdeletekey; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\SafeToolPDF.pdf\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#AppExeName},0"; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\SafeToolPDF.pdf\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExeName}"" ""%1"""; Tasks: fileassoc

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName,'&','&&')}}"; Flags: nowait postinstall skipifsilent
