; Inno Setup script for Release Tool.
; Not meant to be compiled by hand - build.ps1 invokes ISCC.exe with
; AppVersion / SourceDir / OutputDir passed in via /D defines, from the
; PyInstaller --onedir output it just produced.

#define MyAppName "Release Tool"
#define MyAppExeName "ReleaseTool.exe"

[Setup]
; Fixed and must never change across versions - it's how Windows recognizes
; a new installer as an upgrade of this app rather than a separate, parallel
; install. The doubled "{{" is Inno Setup's escape for a literal "{" (curly
; braces are otherwise its constant-reference syntax, e.g. {app}, {tmp}).
AppId={{FD383A83-B885-4B32-AF83-65F91408BD36}
AppName={#MyAppName}
AppVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; Per-user install under %LOCALAPPDATA% needs no admin rights, so this
; installer never triggers a UAC elevation prompt.
PrivilegesRequired=lowest
OutputDir={#OutputDir}
OutputBaseFilename=ReleaseTool-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesInstallIn64BitMode=x64compatible

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
; settings.json is handled separately below (onlyifdoesntexist) so an
; upgrade install never overwrites a returning user's live settings.
Source: "{#SourceDir}\*"; DestDir: "{app}"; Excludes: "settings.json"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "{#SourceDir}\settings.json"; DestDir: "{app}"; Flags: onlyifdoesntexist

[UninstallDelete]
; Written by the app at runtime (core/cache_manager.py), not by [Files] above,
; so the uninstaller has no record of it and won't remove it on its own.
Type: files; Name: "{app}\connection_checks_cache.json"

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{autoprograms}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
