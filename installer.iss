; Inno Setup script for File Extension Converter
; Build:  "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
; Produces: installer_output\FileExtensionConverter-Setup-<version>.exe
;
; Packages the PyInstaller onedir output (dist\File Extension Converter\).
; Build that first:  python -m PyInstaller --noconfirm --clean FileExtensionConverter.spec

#define MyAppName "File Extension Converter"
#define MyAppVersion "0.2.0"
#define MyAppPublisher "File Extension Converter"
#define MyAppExeName "File Extension Converter.exe"

[Setup]
AppId={{8F3A6C2E-4B7D-4E1A-9C5F-FEC0CONVERTER}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
; Per-user install: no administrator rights / UAC prompt required.
PrivilegesRequired=lowest
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename=FileExtensionConverter-Setup-{#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Bundle the entire PyInstaller onedir output.
Source: "dist\{#MyAppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
