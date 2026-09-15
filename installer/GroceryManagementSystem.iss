#define MyAppName "نظام إدارة البقالات"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "نظام إدارة البقالات"
#define MyAppExeName "GroceryManagementSystem.exe"

[Setup]
AppId={{9C6D8E77-0B7E-4C9E-9A8C-4F4A1B0C9D21}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\GroceryManagementSystem
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=GroceryManagementSystem-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
UninstallDisplayIcon={app}\{#MyAppExeName}

[Tasks]
Name: "desktopicon"; Description: "إنشاء اختصار على سطح المكتب"; GroupDescription: "اختصارات البرنامج:"
Name: "kiosk"; Description: "تفعيل وضع جهاز البقالة المقيد (اختياري)"; GroupDescription: "أمان جهاز التشغيل:"; Flags: unchecked

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\GroceryLicenseManager.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\tools\setup_kiosk.ps1"; DestDir: "{app}\tools"; Flags: ignoreversion
Source: "..\tools\remove_kiosk.ps1"; DestDir: "{app}\tools"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}\docs"; Flags: ignoreversion

[Dirs]
Name: "{app}\data"
Name: "{app}\backups"

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\tools\setup_kiosk.ps1"" -AppPath ""{app}\{#MyAppExeName}"" -KioskUser ""GroceryKiosk"""; WorkingDir: "{app}"; Flags: runhidden waituntilterminated; Tasks: kiosk
Filename: "{app}\{#MyAppExeName}"; Description: "تشغيل نظام إدارة البقالات"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\tools\remove_kiosk.ps1"" -KioskUser ""GroceryKiosk"""; Flags: runhidden waituntilterminated

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
  if not IsAdminInstallMode then
  begin
    MsgBox('يجب تشغيل برنامج التثبيت بصلاحيات المسؤول حتى يتمكن من تثبيت جميع مكونات النظام.', mbError, MB_OK);
    Result := False;
  end;
end;
