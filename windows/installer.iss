; Windows installer (Inno Setup 6.3 or later). Built by windows\build.bat when Inno Setup is
; installed, and by the release workflow (.github/workflows/release.yml):
;     iscc /DAppVersion=1.2.3 windows\installer.iss
; Needs the PyInstaller build in dist\DCS Mission Maker\ and build\icon.ico (both made by
; windows\dcs-mission-maker.spec). Output: dist\DCS-Mission-Maker-Setup-<version>.exe
;
; The app goes to Program Files; missions and settings stay in C:\ProgramData\DCS Mission Maker,
; which upgrades leave alone and uninstalling only deletes if you say so.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#define AppName "DCS Mission Maker"
#define AppExe "DCS Mission Maker.exe"

[Setup]
; Never change the AppId: Windows recognises upgrades of this app by it.
AppId={{64D71E33-33FF-4B69-B07C-E53D91C42C38}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=DCS Mission Maker contributors
VersionInfoVersion={#AppVersion}
DefaultDirName={autopf}\{#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist
OutputBaseFilename=DCS-Mission-Maker-Setup-{#AppVersion}
SetupIconFile=..\build\icon.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
WizardStyle=modern
Compression=lzma2/max
SolidCompression=yes
; The running app is stopped in PrepareToInstall below, not by Restart Manager.
CloseApplications=no

[Tasks]
Name: firewall; Description: "Let other PCs reach it (allow it through Windows Firewall)"
Name: autostart; Description: "Start it when I log on to Windows"
Name: desktopicon; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[InstallDelete]
; An upgrade replaces the bundled files completely, so no old modules linger.
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "..\dist\DCS Mission Maker\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
; The firewall rule allows the program, not a port, so it still works if the port changes.
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""{#AppName}"""; Flags: runhidden
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall add rule name=""{#AppName}"" dir=in action=allow program=""{app}\{#AppExe}"" enable=yes profile=any"; Flags: runhidden; Tasks: firewall; StatusMsg: "Allowing it through Windows Firewall..."
; Start with Windows is per user: set it for the user who ran Setup, not the admin account.
Filename: "{app}\{#AppExe}"; Parameters: "--set-autostart"; Flags: runasoriginaluser waituntilterminated; Tasks: autostart
Filename: "{app}\{#AppExe}"; Parameters: "--unset-autostart"; Flags: runasoriginaluser waituntilterminated; Tasks: not autostart
Filename: "{app}\{#AppExe}"; Description: "Start {#AppName} now"; Flags: postinstall nowait runasoriginaluser skipifsilent

[UninstallRun]
Filename: "{sys}\taskkill.exe"; Parameters: "/F /IM ""{#AppExe}"""; Flags: runhidden; RunOnceId: "StopApp"
Filename: "{app}\{#AppExe}"; Parameters: "--unset-autostart"; Flags: runhidden waituntilterminated; RunOnceId: "Autostart"
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""{#AppName}"""; Flags: runhidden; RunOnceId: "Firewall"

[Code]
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  Code: Integer;
begin
  { An upgrade can't replace the files while the app runs: stop it (it starts again at the end). }
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /IM "{#AppExe}"', '', SW_HIDE, ewWaitUntilTerminated, Code);
  if Code = 0 then
    Sleep(1500);
  Result := '';
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Data: String;
begin
  if CurUninstallStep <> usPostUninstall then
    Exit;
  Data := ExpandConstant('{commonappdata}\{#AppName}');
  if DirExists(Data) and not UninstallSilent and
     (MsgBox('Also delete your missions, settings and sign-ups?' + #13#10#13#10 + Data,
             mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES) then
    DelTree(Data, True, True, True);
end;
