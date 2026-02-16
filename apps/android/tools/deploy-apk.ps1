# Deploy Android APK to Device/Emulator
# This script handles APK installation and app launching

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("Debug", "Release")]
    [string]$BuildType,

    [string]$DeviceId,
    [switch]$Launch,
    [switch]$UninstallFirst
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

Write-Host "📱 Deploying MIA Universal Android APK" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan

# Determine APK path
$apkName = if ($BuildType -eq "Release") { "app-release.apk" } else { "app-debug.apk" }
$apkPath = Join-Path $PSScriptRoot "..\app\build\outputs\apk\$($BuildType.ToLower())\$apkName"

Write-Host "🔍 Build Type: $BuildType" -ForegroundColor White
Write-Host "📦 APK Path: $apkPath" -ForegroundColor White
if ($DeviceId) {
    Write-Host "📱 Target Device: $DeviceId" -ForegroundColor White
} else {
    Write-Host "📱 Target Device: Auto-detect" -ForegroundColor White
}
Write-Host ""

# Check if APK exists
if (!(Test-Path $apkPath)) {
    Write-Host "❌ APK not found at: $apkPath" -ForegroundColor Red
    Write-Host "💡 Make sure to build the APK first using:" -ForegroundColor Yellow
    Write-Host "   .\build.ps1 -BuildType $BuildType" -ForegroundColor White
    exit 1
}

Write-Host "✅ APK found: $(Get-Item $apkPath | Select-Object -ExpandProperty Length) bytes" -ForegroundColor Green

# Check for ADB
try {
    $adbVersion = & adb version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ ADB available: $($adbVersion[0])" -ForegroundColor Green
    } else {
        throw "ADB not found"
    }
} catch {
    Write-Host "❌ ADB not found. Please install Android SDK Platform Tools." -ForegroundColor Red
    Write-Host "💡 Download from: https://developer.android.com/studio/releases/platform-tools" -ForegroundColor Yellow
    exit 1
}

# List connected devices
Write-Host "🔍 Checking connected devices..." -ForegroundColor Yellow
$devices = & adb devices 2>$null
$deviceLines = $devices | Where-Object { $_ -match "\s+device$" }

if ($deviceLines.Count -eq 0) {
    Write-Host "❌ No Android devices/emulators found!" -ForegroundColor Red
    Write-Host "" -ForegroundColor White
    Write-Host "📱 Connect an Android device or start an emulator:" -ForegroundColor Yellow
    Write-Host "   • Enable USB Debugging in Developer Options" -ForegroundColor White
    Write-Host "   • Or start Android Studio emulator" -ForegroundColor White
    Write-Host "   • Or use wireless ADB: adb connect <ip>:5555" -ForegroundColor White
    exit 1
}

Write-Host "📱 Connected devices:" -ForegroundColor Green
$deviceLines | ForEach-Object {
    $deviceId = $_.Split()[0]
    if ($DeviceId -and $deviceId -eq $DeviceId) {
        Write-Host "   • $deviceId (selected)" -ForegroundColor Cyan
    } else {
        Write-Host "   • $deviceId" -ForegroundColor White
    }
}
Write-Host ""

# Select device
$targetDevice = $DeviceId
if (!$targetDevice) {
    if ($deviceLines.Count -eq 1) {
        $targetDevice = $deviceLines[0].Split()[0]
        Write-Host "🎯 Auto-selected device: $targetDevice" -ForegroundColor Green
    } else {
        Write-Host "❌ Multiple devices found. Please specify -DeviceId parameter." -ForegroundColor Red
        exit 1
    }
}

# Verify device is accessible
Write-Host "🔍 Verifying device access..." -ForegroundColor Yellow
try {
    $deviceInfo = & adb -s $targetDevice shell getprop ro.product.model 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Device accessible: $($deviceInfo.Trim())" -ForegroundColor Green
    } else {
        throw "Device not accessible"
    }
} catch {
    Write-Host "❌ Cannot access device: $targetDevice" -ForegroundColor Red
    exit 1
}

# Uninstall existing app if requested
if ($UninstallFirst) {
    Write-Host "🗑️  Uninstalling existing app..." -ForegroundColor Yellow
    & adb -s $targetDevice uninstall cz.mia.app 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ App uninstalled successfully" -ForegroundColor Green
    } else {
        Write-Host "⚠️  App was not installed or uninstall failed" -ForegroundColor Yellow
    }
}

# Install APK
Write-Host "📦 Installing APK..." -ForegroundColor Yellow
$installArgs = @("-s", $targetDevice, "install", "-r", $apkPath)
$installResult = & adb @installArgs 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ APK installed successfully!" -ForegroundColor Green
} else {
    Write-Host "❌ APK installation failed:" -ForegroundColor Red
    Write-Host $installResult -ForegroundColor Red
    exit 1
}

# Launch app if requested
if ($Launch) {
    Write-Host "🚀 Launching app..." -ForegroundColor Yellow
    $launchArgs = @("-s", $targetDevice, "shell", "am", "start", "-n", "cz.mia.app/.MainActivity")
    $launchResult = & adb @launchArgs 2>&1

    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ App launched successfully!" -ForegroundColor Green
    } else {
        Write-Host "❌ App launch failed:" -ForegroundColor Red
        Write-Host $launchResult -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "🎉 Deployment completed!" -ForegroundColor Green
Write-Host ""
Write-Host "📊 Summary:" -ForegroundColor Cyan
Write-Host "   • APK: $apkName" -ForegroundColor White
Write-Host "   • Device: $targetDevice" -ForegroundColor White
Write-Host "   • Package: cz.mia.app" -ForegroundColor White
if ($Launch) {
    Write-Host "   • Status: Installed and launched" -ForegroundColor White
} else {
    Write-Host "   • Status: Installed (launch manually)" -ForegroundColor White
}
Write-Host ""
Write-Host "💡 Manual launch command:" -ForegroundColor Yellow
Write-Host "   adb -s $targetDevice shell am start -n cz.mia.app/.MainActivity" -ForegroundColor White
