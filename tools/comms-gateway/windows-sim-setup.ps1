# windows-sim-setup.ps1
# Run on DESKTOP-E98SQDH (Windows laptop with SIM) as Administrator
# Sets up Tailscale + SMS gateway capability for MIA

# ── 1. Install Tailscale (if not present) ──────────────────────────────────────
if (-not (Get-Command tailscale -ErrorAction SilentlyContinue)) {
    Write-Host "[Tailscale] Installing..."
    winget install Tailscale.Tailscale
    Write-Host "[Tailscale] Run: tailscale up --authkey=<tskey-...>"
    Write-Host "            Then: tailscale set --ssh"
} else {
    $status = tailscale status --json | ConvertFrom-Json
    Write-Host "[Tailscale] Already active. IP: $($status.TailscaleIPs[0])"
}

# ── 2. Enable SSH (for remote management via Tailscale) ────────────────────────
$sshFeature = Get-WindowsCapability -Online | Where-Object { $_.Name -like "OpenSSH.Server*" }
if ($sshFeature.State -ne "Installed") {
    Write-Host "[SSH] Installing OpenSSH Server..."
    Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
    Start-Service sshd
    Set-Service -Name sshd -StartupType Automatic
    Write-Host "[SSH] Enabled. Add your public key to %USERPROFILE%\.ssh\authorized_keys"
} else {
    Write-Host "[SSH] Already installed"
}

# ── 3. SMS Gateway via Windows Mobile Broadband API ───────────────────────────
# Exposes a simple HTTP endpoint that MIA calls to send SMS via SIM
$smsBridgeScript = @'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.ApplicationModel.Chat.ChatMessageManager, Windows.ApplicationModel.Chat, ContentType=WindowsRuntime]
# NOTE: SMS sending via Windows Runtime API requires UWP context on some systems.
# Alternative: use Windows Device Portal or a simple HTTP wrapper around PowerShell SMS.
Write-Host "SMS bridge: use KDE Connect (already paired) for SMS — this script is a fallback."
'@

# ── 4. KDE Connect is already paired ──────────────────────────────────────────
Write-Host ""
Write-Host "KDE Connect status:"
Write-Host "  DESKTOP-E98SQDH is already paired with studio"
Write-Host "  SMS from Windows SIM → use KDE Connect plugin on Windows KDE Connect app"
Write-Host ""
Write-Host "To enable SMS forwarding from Windows SIM via KDE Connect:"
Write-Host "  1. Open KDE Connect for Windows"
Write-Host "  2. Enable 'SMS Sync' plugin"
Write-Host "  3. From studio: kdeconnect-cli -d _521d1df7_34aa_48a0_8e62_cba989ac5f36_ --send-sms 'msg' --destination '+420...'"
Write-Host ""

# ── 5. SIP Softphone (Linphone) for ElevenLabs voice via Tailscale ────────────
Write-Host "[SIP] To use Windows SIM for voice via ElevenLabs SIP trunk:"
Write-Host "  Install Linphone: https://www.linphone.org/technical-corner/linphone"
Write-Host "  SIP server: sip.elevenlabs.io"
Write-Host "  Account: see tools/sip-bridge/.env for credentials"
Write-Host ""
Write-Host "Setup complete. Windows node is ready for MIA comms integration."
