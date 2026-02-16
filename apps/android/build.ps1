# Android Build Script (PowerShell 5+ compatible)
#Requires -Version 5

param(
    [ValidateSet("Debug", "Release")]
    [string]$BuildType = "Debug",
    [switch]$Clean,
    [switch]$Install,
    [string]$DeviceId
)

#region agent log
function Write-AgentLog {
    param(
        [string]$HypothesisId,
        [string]$Location,
        [string]$Message,
        [hashtable]$Data
    )
    $logPath = Join-Path -Path (Resolve-Path "$PSScriptRoot\..") -ChildPath ".cursor\debug.log"
    $payload = [pscustomobject]@{
        sessionId   = "debug-session"
        runId       = "pre-fix"
        hypothesisId= $HypothesisId
        location    = $Location
        message     = $Message
        data        = $Data
        timestamp   = [int64]([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds())
    } | ConvertTo-Json -Compress
    Add-Content -Path $logPath -Value $payload
}
#endregion agent log

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot


#region agent log
Write-AgentLog -HypothesisId "H1" -Location "build.ps1:entry" -Message "env snapshot" -Data @{
    psVersion = $PSVersionTable.PSVersion.ToString()
    javaHome  = $env:JAVA_HOME
    cwd       = (Get-Location).Path
    shell     = $env:ComSpec
}
#endregion agent log

# region agent log
$localPropsCheck = @{
    sessionId = "debug-session"
    runId = "gradle-prep-check"
    hypothesisId = "H3"
    location = "android/build.ps1:40"
    message = "Local properties and SDK check before Gradle"
    data = @{
        localPropsExists = Test-Path "$PSScriptRoot\local.properties"
        localPropsContent = if (Test-Path "$PSScriptRoot\local.properties") {
            try { Get-Content "$PSScriptRoot\local.properties" -Raw } catch { "read_error" }
        } else { $null }
        androidSdkExists = Test-Path "$PSScriptRoot\..\sdk"
        gradlewExists = Test-Path "$PSScriptRoot\gradlew.bat"
        javaHomeExists = Test-Path $env:JAVA_HOME
        androidHomeExists = Test-Path $env:ANDROID_HOME
    }
    timestamp = [long]((Get-Date).ToUniversalTime() - [DateTime]'1970-01-01').TotalMilliseconds
}
try {
    $jsonBody = $localPropsCheck | ConvertTo-Json -Depth 3 -Compress
    Invoke-WebRequest -Uri 'http://127.0.0.1:7242/ingest/ce46ab37-4f15-4303-9d97-ec0e91bd7cb2' -Method POST -ContentType 'application/json' -Body $jsonBody -TimeoutSec 5 | Out-Null
} catch { }
# endregion agent log

if ($Clean) {
    Write-Host "Cleaning build directory..." -ForegroundColor Yellow
    & "$PSScriptRoot\\gradlew.bat" clean
}

$task = if ($BuildType -eq "Release") { "assembleRelease" } else { "assembleDebug" }
Write-Host "Building $BuildType APK..." -ForegroundColor Green
#region agent log
$gradlePath = Join-Path $PSScriptRoot "gradlew.bat"
Write-AgentLog -HypothesisId "H3" -Location "build.ps1:before-gradle" -Message "gradle invocation" -Data @{
    task = $task
    gradleExists = Test-Path $gradlePath
    gradlePath = $gradlePath
    buildType = $BuildType
}
#endregion agent log
& "$PSScriptRoot\\gradlew.bat" $task --info

if ($Install) {
    $apkName = if ($BuildType -eq "Release") { "app-release.apk" } else { "app-debug.apk" }
    $apkPath = Join-Path $PSScriptRoot "app\\build\\outputs\\apk\\$($BuildType.ToLower())\\$apkName"

    if (Test-Path $apkPath) {
        Write-Host "Installing APK to device..." -ForegroundColor Cyan
        $adbArgs = @("install", "-r", $apkPath)
        if ($DeviceId) {
            $adbArgs = @("-s", $DeviceId) + $adbArgs
        }
        & adb @adbArgs
        Write-Host "Launch app with: adb shell am start -n cz.mia.app/.MainActivity" -ForegroundColor Green
    } else {
        Write-Error "APK not found at $apkPath"
    }
}

