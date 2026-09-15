param(
    [Parameter(Mandatory=$true)] [string] $AppPath,
    [string] $KioskUser = "GroceryKiosk"
)

$ErrorActionPreference = "Stop"

function Require-Admin {
    $principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "يجب تشغيل إعداد وضع الجهاز المقيد بصلاحيات المسؤول."
    }
}

Require-Admin
if (-not (Test-Path -LiteralPath $AppPath)) { throw "لم يتم العثور على ملف البرنامج: $AppPath" }

# A dedicated standard account is created for the workstation. The generated credential
# is kept only in an administrator-readable file because Windows AutoLogon requires it.
$bytes = New-Object byte[] 32
[Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
$passwordText = ([Convert]::ToBase64String($bytes) + "Gk!7").Substring(0, 24)
$securePassword = ConvertTo-SecureString $passwordText -AsPlainText -Force
$user = Get-LocalUser -Name $KioskUser -ErrorAction SilentlyContinue
if (-not $user) {
    New-LocalUser -Name $KioskUser -Password $securePassword -FullName "تشغيل نظام البقالة" -Description "حساب Windows مقيد لتشغيل نظام إدارة البقالات" -PasswordNeverExpires:$true -UserMayNotChangePassword:$false | Out-Null
} else {
    Set-LocalUser -Name $KioskUser -Password $securePassword -PasswordNeverExpires:$true
}

Remove-LocalGroupMember -Group "Administrators" -Member $KioskUser -ErrorAction SilentlyContinue
Add-LocalGroupMember -Group "Users" -Member $KioskUser -ErrorAction SilentlyContinue

$sid = (Get-LocalUser -Name $KioskUser).SID.Value
$hku = "Registry::HKEY_USERS\$sid"
$profile = (Get-CimInstance Win32_UserProfile | Where-Object { $_.SID -eq $sid }).LocalPath
$ntuser = Join-Path $profile "NTUSER.DAT"
$loaded = Test-Path $hku
if (-not $loaded) { & reg.exe load "HKU\$sid" "$ntuser" | Out-Null }

try {
    # Replace Explorer with the grocery application for this account.
    New-Item -Path "$hku\Software\Microsoft\Windows NT\CurrentVersion\Winlogon" -Force | Out-Null
    Set-ItemProperty -Path "$hku\Software\Microsoft\Windows NT\CurrentVersion\Winlogon" -Name Shell -Type String -Value "`"$AppPath`""

    $pol = "$hku\Software\Microsoft\Windows\CurrentVersion\Policies"
    New-Item -Path "$pol\Explorer" -Force | Out-Null
    New-Item -Path "$pol\System" -Force | Out-Null
    Set-ItemProperty -Path "$pol\Explorer" -Name NoControlPanel -Type DWord -Value 1
    Set-ItemProperty -Path "$pol\Explorer" -Name NoRun -Type DWord -Value 1
    Set-ItemProperty -Path "$pol\Explorer" -Name NoViewContextMenu -Type DWord -Value 1
    Set-ItemProperty -Path "$pol\Explorer" -Name NoWinKeys -Type DWord -Value 1
    Set-ItemProperty -Path "$pol\System" -Name DisableCMD -Type DWord -Value 1
    Set-ItemProperty -Path "$pol\System" -Name DisableRegistryTools -Type DWord -Value 1
    New-Item -Path "$hku\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" -Force | Out-Null
    Set-ItemProperty -Path "$hku\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" -Name HideIcons -Type DWord -Value 1
} finally {
    if (-not $loaded) { & reg.exe unload "HKU\$sid" | Out-Null }
}

# Keep administrator accounts visible while hiding ordinary Windows accounts at sign-in.
$userList = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon\SpecialAccounts\UserList"
New-Item -Path $userList -Force | Out-Null
$adminNames = @()
try { $adminNames = @(Get-LocalGroupMember -Group "Administrators" | ForEach-Object { ($_.Name -split '\\')[-1] }) } catch {}
Get-LocalUser | ForEach-Object {
    if ($_.Name -ne $KioskUser -and ($adminNames -notcontains $_.Name)) {
        New-ItemProperty -Path $userList -Name $_.Name -PropertyType DWord -Value 0 -Force | Out-Null
    }
}
New-ItemProperty -Path $userList -Name $KioskUser -PropertyType DWord -Value 1 -Force | Out-Null

# Auto-logon is optional at the product level, but the kiosk installer enables it so a dedicated
# sales terminal can boot directly into the application. Windows stores the credential in its
# Winlogon configuration; the admin recovery file is protected to administrators only.
$winlogon = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon"
Set-ItemProperty -Path $winlogon -Name AutoAdminLogon -Type String -Value "1"
Set-ItemProperty -Path $winlogon -Name DefaultUserName -Type String -Value $KioskUser
Set-ItemProperty -Path $winlogon -Name DefaultPassword -Type String -Value $passwordText
Set-ItemProperty -Path $winlogon -Name DefaultDomainName -Type String -Value $env:COMPUTERNAME

$stateDir = "C:\ProgramData\GroceryManagementSystem"
New-Item -ItemType Directory -Path $stateDir -Force | Out-Null
$stateFile = Join-Path $stateDir "kiosk-state.json"
@{
    kiosk_user = $KioskUser
    app_path = $AppPath
    configured_utc = (Get-Date).ToUniversalTime().ToString("o")
    recovery = "للدخول إلى بيئة الصيانة استخدم حساب Windows المسؤول."
} | ConvertTo-Json | Set-Content -Encoding UTF8 $stateFile
$credentialFile = Join-Path $stateDir "kiosk-credentials.txt"
@("حساب التشغيل: $KioskUser", "كلمة المرور: $passwordText", "هذا الملف مخصص للمسؤول فقط.") | Set-Content -Encoding UTF8 $credentialFile
$acl = Get-Acl $credentialFile
$acl.SetAccessRuleProtection($true, $false)
$acl.Access | ForEach-Object { $acl.RemoveAccessRule($_) | Out-Null }
$admins = New-Object System.Security.Principal.NTAccount("Administrators")
$rule = New-Object System.Security.AccessControl.FileSystemAccessRule($admins, "FullControl", "Allow")
$acl.AddAccessRule($rule)
Set-Acl -Path $credentialFile -AclObject $acl

Write-Host "تم إعداد حساب التشغيل المقيد: $KioskUser"
Write-Host "سيبدأ النظام تلقائيًا عند تسجيل الدخول إلى حساب التشغيل."
Write-Host "لصيانة الجهاز استخدم حساب Windows المسؤول."
