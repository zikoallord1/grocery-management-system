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

if (-not (Test-Path -LiteralPath $AppPath)) {
    throw "لم يتم العثور على ملف البرنامج: $AppPath"
}

# Create a dedicated standard Windows account for the grocery workstation.
$user = Get-LocalUser -Name $KioskUser -ErrorAction SilentlyContinue
if (-not $user) {
    $bytes = New-Object byte[] 32
    [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $passwordText = ([Convert]::ToBase64String($bytes) + "Gk!7").Substring(0, 24)
    $securePassword = ConvertTo-SecureString $passwordText -AsPlainText -Force
    New-LocalUser -Name $KioskUser -Password $securePassword -FullName "تشغيل نظام البقالة" -Description "حساب Windows مقيد لتشغيل نظام إدارة البقالات" -PasswordNeverExpires:$true -UserMayNotChangePassword:$false | Out-Null
} else {
    $passwordText = $null
}

# Make sure the account is not an administrator.
Remove-LocalGroupMember -Group "Administrators" -Member $KioskUser -ErrorAction SilentlyContinue
Add-LocalGroupMember -Group "Users" -Member $KioskUser -ErrorAction SilentlyContinue

$sid = (Get-LocalUser -Name $KioskUser).SID.Value
$hku = "Registry::HKEY_USERS\$sid"

# Load the user's registry hive if necessary.
$profile = (Get-CimInstance Win32_UserProfile | Where-Object { $_.SID -eq $sid }).LocalPath
$ntuser = Join-Path $profile "NTUSER.DAT"
$loaded = Test-Path $hku
if (-not $loaded) {
    & reg.exe load "HKU\$sid" "$ntuser" | Out-Null
}

try {
    # Replace Explorer with the application for this account. The secure Windows desktop
    # remains available to an administrator, while the kiosk account starts directly in the app.
    New-Item -Path "$hku\Software\Microsoft\Windows NT\CurrentVersion\Winlogon" -Force | Out-Null
    Set-ItemProperty -Path "$hku\Software\Microsoft\Windows NT\CurrentVersion\Winlogon" -Name Shell -Type String -Value "`"$AppPath`""

    $pol = "$hku\Software\Microsoft\Windows\CurrentVersion\Policies"
    New-Item -Path "$pol\Explorer" -Force | Out-Null
    New-Item -Path "$pol\System" -Force | Out-Null
    New-Item -Path "$pol\Uninstall" -Force | Out-Null

    # Common escape routes are disabled for the kiosk user.
    Set-ItemProperty -Path "$pol\Explorer" -Name NoControlPanel -Type DWord -Value 1
    Set-ItemProperty -Path "$pol\Explorer" -Name NoRun -Type DWord -Value 1
    Set-ItemProperty -Path "$pol\Explorer" -Name NoViewContextMenu -Type DWord -Value 1
    Set-ItemProperty -Path "$pol\Explorer" -Name NoWinKeys -Type DWord -Value 1
    Set-ItemProperty -Path "$pol\System" -Name DisableCMD -Type DWord -Value 1
    Set-ItemProperty -Path "$pol\System" -Name DisableRegistryTools -Type DWord -Value 1

    # Hide the normal Windows desktop surface for this user.
    New-Item -Path "$hku\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" -Force | Out-Null
    Set-ItemProperty -Path "$hku\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" -Name HideIcons -Type DWord -Value 1
} finally {
    if (-not $loaded) {
        & reg.exe unload "HKU\$sid" | Out-Null
    }
}

# Hide local non-admin accounts from the Windows sign-in user list. Administrators remain visible.
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

# Record non-secret setup information for the administrator.
$stateDir = "C:\ProgramData\GroceryManagementSystem"
New-Item -ItemType Directory -Path $stateDir -Force | Out-Null
@{
    kiosk_user = $KioskUser
    app_path = $AppPath
    configured_utc = (Get-Date).ToUniversalTime().ToString("o")
    recovery = "سجّل الدخول بحساب Windows المسؤول للصيانة. لا يتم حفظ كلمة مرور حساب التشغيل هنا."
} | ConvertTo-Json | Set-Content -Encoding UTF8 (Join-Path $stateDir "kiosk-state.json")

Write-Host "تم إعداد حساب التشغيل المقيد: $KioskUser"
Write-Host "بعد تسجيل الدخول بهذا الحساب سيبدأ النظام كواجهة الجهاز المقيد."
