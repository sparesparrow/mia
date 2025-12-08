# PowerShell equivalent of dashboard ADB testing
param(
    [string]$DeviceId = "HT36TW903516",
    [switch]$Screenshots,
    [switch]$Logs
)

$ErrorActionPreference = "Stop"

Write-Host "🔧 Testing MIA Universal Dashboard via ADB" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan

$packageName = "cz.mia.app.debug"
$activityName = ".MainActivity"
$outputDir = "debug-output"

# Create output directory
if (!(Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}

Write-Host "📱 Device: $DeviceId" -ForegroundColor White
Write-Host "📦 Package: $packageName" -ForegroundColor White
Write-Host "📁 Output: $outputDir" -ForegroundColor White
Write-Host ""

# Function to run ADB command
function Invoke-Adb {
    param([string]$Command)
    $result = & adb -s $DeviceId shell $Command 2>&1
    return $result
}

# Function to capture screenshot
function Capture-Screenshot {
    param([string]$Name)
    if ($Screenshots) {
        Write-Host "📸 Capturing screenshot: $Name" -ForegroundColor Yellow
        Invoke-Adb "screencap -p /sdcard/$Name.png" | Out-Null
        & adb -s $DeviceId pull "/sdcard/$Name.png" "$outputDir/$Name.png" 2>$null | Out-Null
    }
}

# Function to capture logs
function Capture-Logs {
    param([string]$Name)
    if ($Logs) {
        Write-Host "📋 Capturing logs: $Name" -ForegroundColor Yellow
        & adb -s $DeviceId logcat -d > "$outputDir/$Name.txt" 2>$null
    }
}

# Check if app is installed
Write-Host "🔍 Checking app installation..." -ForegroundColor Yellow
$appInstalled = Invoke-Adb "pm list packages $packageName"
if ($appInstalled -notlike "*$packageName*") {
    Write-Host "❌ App not installed. Please install first:" -ForegroundColor Red
    Write-Host "   .\tools\deploy-apk.ps1 -BuildType Debug -DeviceId $DeviceId" -ForegroundColor White
    exit 1
}
Write-Host "✅ App installed" -ForegroundColor Green

# Check if app is running
Write-Host "🔍 Checking app status..." -ForegroundColor Yellow
$appProcesses = Invoke-Adb "ps | grep $packageName"
if ($appProcesses) {
    Write-Host "✅ App is running" -ForegroundColor Green
} else {
    Write-Host "⚠️  App not running, launching..." -ForegroundColor Yellow
    & adb -s $DeviceId shell am start -n "$packageName/$activityName" 2>$null | Out-Null
    Start-Sleep -Seconds 3
}

# Capture initial state
Capture-Screenshot "dashboard_initial"
Capture-Logs "dashboard_initial"

Write-Host "🎯 Starting dashboard interaction tests..." -ForegroundColor Green

# Test 1: Dashboard tab (should already be selected)
Write-Host "📊 Test 1: Dashboard tab navigation" -ForegroundColor White
# Dashboard is tab 0, should already be selected
Start-Sleep -Milliseconds 500
Capture-Screenshot "dashboard_tab"

# Test 2: Alerts tab
Write-Host "🚨 Test 2: Alerts tab navigation" -ForegroundColor White
Invoke-Adb "input tap 270 1800" # Alerts tab (bottom navigation)
Start-Sleep -Milliseconds 1000
Capture-Screenshot "alerts_tab"
Capture-Logs "alerts_tab"

# Test 3: Camera tab
Write-Host "📷 Test 3: Camera tab navigation" -ForegroundColor White
Invoke-Adb "input tap 540 1800" # Camera tab
Start-Sleep -Milliseconds 1000
Capture-Screenshot "camera_tab"

# Test 4: OBD tab
Write-Host "🔧 Test 4: OBD tab navigation" -ForegroundColor White
Invoke-Adb "input tap 810 1800" # OBD tab
Start-Sleep -Milliseconds 1000
Capture-Screenshot "obd_tab"

# Test 5: Settings tab
Write-Host "⚙️  Test 5: Settings tab navigation" -ForegroundColor White
Invoke-Adb "input tap 1080 1800" # Settings tab (assuming 1080 width)
Start-Sleep -Milliseconds 1000
Capture-Screenshot "settings_tab"

# Test 6: Back to Dashboard
Write-Host "📊 Test 6: Return to Dashboard" -ForegroundColor White
Invoke-Adb "input tap 135 1800" # Dashboard tab (first tab)
Start-Sleep -Milliseconds 1000
Capture-Screenshot "dashboard_return"

# Test 7: Try Start Service button
Write-Host "▶️  Test 7: Start Service button" -ForegroundColor White
Invoke-Adb "input tap 270 1700" # Start service button (left side)
Start-Sleep -Milliseconds 2000
Capture-Screenshot "after_start_service"
Capture-Logs "after_start_service"

# Test 8: Check if service started (look for notifications or logs)
Write-Host "🔍 Test 8: Check service status" -ForegroundColor White
$runningServices = Invoke-Adb "dumpsys activity services | grep -i mia"
if ($runningServices) {
    Write-Host "✅ MIA services detected:" -ForegroundColor Green
    Write-Host $runningServices -ForegroundColor White
} else {
    Write-Host "⚠️  No MIA services detected" -ForegroundColor Yellow
}

# Final captures
Capture-Screenshot "dashboard_final"
Capture-Logs "dashboard_final"

Write-Host ""
Write-Host "🎉 Dashboard testing completed!" -ForegroundColor Green
Write-Host ""
Write-Host "📊 Results:" -ForegroundColor Cyan
if ($Screenshots) {
    Write-Host "   📸 Screenshots saved to: $outputDir" -ForegroundColor White
}
if ($Logs) {
    Write-Host "   📋 Logs saved to: $outputDir" -ForegroundColor White
}
Write-Host ""
Write-Host "📱 Next steps:" -ForegroundColor Yellow
Write-Host "   • Review screenshots in $outputDir" -ForegroundColor White
Write-Host "   • Check logs for service activity" -ForegroundColor White
Write-Host "   • Run other test scenarios if needed" -ForegroundColor White