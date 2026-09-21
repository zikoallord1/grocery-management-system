param(
    [string]$Package = "com.zikoallord.grocerymobile",
    [string]$Output = "android-crash-log.txt"
)

$adb = Get-Command adb -ErrorAction SilentlyContinue
if (-not $adb) {
    throw "adb غير متوفر. ثبّت Android SDK Platform-Tools ثم أعد المحاولة."
}

$devices = @(adb devices | Select-String "\sdevice$")
if ($devices.Count -eq 0) {
    throw "لم يتم العثور على جهاز Android مصرح به. فعّل USB debugging واقبل رسالة RSA."
}

adb logcat -c
Write-Host "افتح التطبيق الآن، ثم اضغط Ctrl+C بعد ظهور رسالة التوقف."
try {
    adb logcat -v threadtime "AndroidRuntime:E" "*:S" | Tee-Object -FilePath $Output
} finally {
    Write-Host "تم حفظ سجل crash في $Output"
}
