# Android Development Environment Setup for Windows
# This script configures ANDROID_HOME and ensures SDK availability

param(
    [string]$AndroidSdkPath = "$env:LOCALAPPDATA\Android\Sdk"
)

Write-Host "🔧 Setting up Android Development Environment" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan


# Check if Android SDK exists
$sdkExists = Test-Path $AndroidSdkPath
if (-not $sdkExists) {
    Write-Host "❌ Android SDK not found at: $AndroidSdkPath" -ForegroundColor Red
    Write-Host ""
    Write-Host "📦 Please install Android Studio or Android SDK:" -ForegroundColor Yellow
    Write-Host "   1. Download from: https://developer.android.com/studio" -ForegroundColor White
    Write-Host "   2. Install Android SDK via SDK Manager" -ForegroundColor White
    Write-Host "   3. Or install command-line tools only" -ForegroundColor White
    Write-Host ""
    Write-Host "💡 Alternative SDK locations:" -ForegroundColor Yellow
    Write-Host "   • $env:ProgramFiles\Android\android-sdk" -ForegroundColor White
    Write-Host "   • $env:USERPROFILE\android-sdk" -ForegroundColor White
    exit 1
}

Write-Host "✅ Android SDK found at: $AndroidSdkPath" -ForegroundColor Green

# Set ANDROID_HOME environment variable
$env:ANDROID_HOME = $AndroidSdkPath
[Environment]::SetEnvironmentVariable("ANDROID_HOME", $AndroidSdkPath, "User")

Write-Host "✅ ANDROID_HOME set to: $env:ANDROID_HOME" -ForegroundColor Green

# Add Android tools to PATH
$androidTools = @(
    "$AndroidSdkPath\platform-tools",
    "$AndroidSdkPath\tools",
    "$AndroidSdkPath\tools\bin",
    "$AndroidSdkPath\cmdline-tools\latest\bin"
)

$currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
$toolsToAdd = @()

foreach ($tool in $androidTools) {
    if (Test-Path $tool) {
        if ($currentPath -notlike "*$tool*") {
            $toolsToAdd += $tool
        }
    }
}

if ($toolsToAdd.Count -gt 0) {
    $newPath = $currentPath + ";" + ($toolsToAdd -join ";")
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    Write-Host "✅ Added Android tools to PATH:" -ForegroundColor Green
    foreach ($tool in $toolsToAdd) {
        Write-Host "   • $tool" -ForegroundColor White
    }
} else {
    Write-Host "ℹ️  Android tools already in PATH" -ForegroundColor Yellow
}

# Verify ADB availability
try {
    $adbVersion = & adb version 2>$null | Select-Object -First 1
    Write-Host "✅ ADB available: $adbVersion" -ForegroundColor Green
} catch {
    Write-Host "⚠️  ADB not found in PATH (may need to restart terminal)" -ForegroundColor Yellow
}

# Check for required SDK components
$sdkManager = "$AndroidSdkPath\cmdline-tools\latest\bin\sdkmanager.bat"
if (Test-Path $sdkManager) {
    Write-Host "✅ SDK Manager available" -ForegroundColor Green

    # Check if required components are installed
    $requiredComponents = @(
        "platform-tools",
        "platforms;android-34",
        "build-tools;34.0.0"
    )

    Write-Host "🔍 Checking required SDK components..." -ForegroundColor Yellow
    foreach ($component in $requiredComponents) {
        $componentPath = if ($component -match "platforms") {
            "$AndroidSdkPath\$component"
        } elseif ($component -match "build-tools") {
            "$AndroidSdkPath\$component"
        } else {
            "$AndroidSdkPath\$component"
        }

        if (Test-Path $componentPath) {
            Write-Host "   ✅ $component" -ForegroundColor Green
        } else {
            Write-Host "   ❌ $component missing" -ForegroundColor Red
        }
    }
} else {
    Write-Host "⚠️  SDK Manager not found (command-line tools may not be installed)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🎉 Environment setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "📝 Next steps:" -ForegroundColor Cyan
Write-Host "   1. Restart your terminal/command prompt" -ForegroundColor White
Write-Host "   2. Run: cd android && .\build.ps1 -BuildType Debug" -ForegroundColor White
Write-Host "   3. Or: cd android && .\gradlew.bat assembleDebug" -ForegroundColor White
Write-Host ""
Write-Host "💡 If build still fails, check:" -ForegroundColor Yellow
Write-Host "   • Android SDK installation" -ForegroundColor White
Write-Host "   • Required SDK components" -ForegroundColor White
Write-Host "   • Environment variables (restart terminal)" -ForegroundColor White
