[Setup]
AppId={{8C045D22-8472-4AC2-9AFE-5917E6C3D0D0}
AppName=AI Product Toolkit
AppVersion={#AppVersion}
AppPublisher=AI Product Toolkit
DefaultDirName={localappdata}\Programs\AI Product Toolkit
DefaultGroupName=AI Product Toolkit
PrivilegesRequired=lowest
ArchitecturesAllowed={#TargetArch}
ArchitecturesInstallIn64BitMode={#TargetArch}
OutputDir={#ReleaseDir}
OutputBaseFilename={#OutputName}
Compression=lzma2
SolidCompression=yes
UninstallDisplayIcon={app}\AIProductToolkit.exe

[Files]
Source: "{#BundleDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{userprograms}\AI Product Toolkit"; Filename: "{app}\AIProductToolkit.exe"
Name: "{userdesktop}\AI Product Toolkit"; Filename: "{app}\AIProductToolkit.exe"; Tasks: desktopicon

[Tasks]
Name: desktopicon; Description: "Create a desktop shortcut"; Flags: unchecked

[Run]
Filename: "{app}\AIProductToolkit.exe"; Description: "Open AI Product Toolkit"; Flags: nowait postinstall skipifsilent
