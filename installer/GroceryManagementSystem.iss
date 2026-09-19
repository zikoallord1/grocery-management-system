#define MyAppName "نظام الماركت المحاسبي"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "المهندس : زكريا الحاج"
#define MyAppExeName "GroceryManagementSystem.exe"

[Setup]
AppId={{B7B5EAD2-6A1A-4A6D-9B37-4D5E4D8B9A11}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\GroceryManagementSystem
DefaultGroupName={#MyAppName}
OutputDir=Output
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
Source: "..\assets\GroceryManagementSystem.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\GroceryManagementSystem.ico"
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\GroceryManagementSystem.ico"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "تشغيل نظام الماركت المحاسبي"; Flags: nowait postinstall skipifsilent
