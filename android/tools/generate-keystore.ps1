# Generate Android Keystore for Release Signing
# Run this script to create a new keystore for signing release APKs

param(
    [Parameter(Mandatory=$true)]
    [string]$KeystorePassword,

    [Parameter(Mandatory=$true)]
    [string]$KeyPassword,

    [string]$Alias = "mia-key-release",
    [string]$KeystorePath = "$PSScriptRoot\..\keystore\mia-release.jks",
    [string]$ValidityDays = "10000"
)

$ErrorActionPreference = "Stop"

Write-Host "🔐 Generating Android Keystore for Release Signing" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# Create keystore directory if it doesn't exist
$keystoreDir = Split-Path $KeystorePath -Parent
if (!(Test-Path $keystoreDir)) {
    New-Item -ItemType Directory -Path $keystoreDir -Force | Out-Null
    Write-Host "📁 Created keystore directory: $keystoreDir" -ForegroundColor Green
}

# Check if keystore already exists
if (Test-Path $KeystorePath) {
    Write-Host "⚠️  Keystore already exists at: $KeystorePath" -ForegroundColor Yellow
    $overwrite = Read-Host "Do you want to overwrite it? (y/N)"
    if ($overwrite -ne "y" -and $overwrite -ne "Y") {
        Write-Host "❌ Keystore generation cancelled" -ForegroundColor Red
        exit 1
    }
}

Write-Host "🔑 Generating keystore with the following parameters:" -ForegroundColor Yellow
Write-Host "   • Alias: $Alias" -ForegroundColor White
Write-Host "   • Validity: $ValidityDays days" -ForegroundColor White
Write-Host "   • Path: $KeystorePath" -ForegroundColor White
Write-Host ""

# Generate keystore using keytool
$keytoolArgs = @(
    "-genkeypair",
    "-v",
    "-keystore", $KeystorePath,
    "-keyalg", "RSA",
    "-keysize", "4096",
    "-validity", $ValidityDays,
    "-alias", $Alias,
    "-storepass", $KeystorePassword,
    "-keypass", $KeyPassword,
    "-dname", "CN=MIA Universal, OU=Development, O=MIA, L=Prague, ST=Czech Republic, C=CZ"
)

try {
    & keytool @keytoolArgs 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Keystore generated successfully!" -ForegroundColor Green
        Write-Host "📍 Location: $KeystorePath" -ForegroundColor Green
        Write-Host ""
        Write-Host "🔒 IMPORTANT: Store these passwords securely!" -ForegroundColor Red
        Write-Host "   Store Password: $KeystorePassword" -ForegroundColor Red
        Write-Host "   Key Password: $KeyPassword" -ForegroundColor Red
        Write-Host ""
        Write-Host "📝 Update your keystore.properties file with these values:" -ForegroundColor Yellow
        Write-Host "   storePassword=$KeystorePassword" -ForegroundColor White
        Write-Host "   keyPassword=$KeyPassword" -ForegroundColor White
    } else {
        Write-Host "❌ Failed to generate keystore" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Error generating keystore: $_" -ForegroundColor Red
    exit 1
}
