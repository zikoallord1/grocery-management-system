param([string] $KioskUser = "GroceryKiosk")
$ErrorActionPreference = "SilentlyContinue"

$run = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon"
Remove-ItemProperty -Path $run -Name AutoAdminLogon -ErrorAction SilentlyContinue
Remove-ItemProperty -Path $run -Name DefaultUserName -ErrorAction SilentlyContinue
Remove-ItemProperty -Path $run -Name DefaultPassword -ErrorAction SilentlyContinue

$userList = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon\SpecialAccounts\UserList"
if (Test-Path $userList) {
    Get-ItemProperty -Path $userList | Get-Member -MemberType NoteProperty | ForEach-Object {
        if ($_.Name -notlike "PS*") {
            Remove-ItemProperty -Path $userList -Name $_.Name -ErrorAction SilentlyContinue
        }
    }
}

$user = Get-LocalUser -Name $KioskUser -ErrorAction SilentlyContinue
if ($user) {
    Remove-LocalUser -Name $KioskUser -ErrorAction SilentlyContinue
}

Remove-Item -LiteralPath "C:\ProgramData\GroceryManagementSystem\kiosk-state.json" -Force -ErrorAction SilentlyContinue
