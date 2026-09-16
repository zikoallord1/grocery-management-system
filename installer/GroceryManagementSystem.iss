#define MyAppName "نظام البقالة المحاسبي"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Grocery Management System"
#define MyAppExeName "GroceryManagementSystem.exe"

[Setup]
AppId={{B7B5E4D2-6A1A-4A6D-9B37-4D5E4D0B9A11}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\GroceryManagementSystem
DefaultGroupName={#MyAppName}
OutputDir=installer-output
OutputBaseFilename=GroceryManagementSystem-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
SetupIconFile=..\assets\GroceryManagementSystem.ico
UninstallDisplayIcon={app}\GroceryManagementSystem.exe

[Files]
Source: "..\dist\GroceryManagementSystem.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\GroceryLicenseManager.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\assets\GroceryManagementSystem.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\build_docs\دليل استخدام البرنامج.pdf"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\build_docs\تقرير البرنامج.pdf"; DestDir: "{app}\docs"; Flags: ignoreversion

[Icons]
Name: "{autodesktop}\نظام البقالة المحاسبي"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\GroceryManagementSystem.ico"; Comment: "نظام البقالة المحاسبي"
Name: "{group}\نظام البقالة المحاسبي"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\GroceryManagementSystem.ico"
Name: "{group}\مدير ترخيص النظام"; Filename: "{app}\GroceryLicenseManager.exe"; WorkingDir: "{app}"; IconFilename: "{app}\GroceryManagementSystem.ico"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "تشغيل نظام البقالة المحاسبي"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\logs"
