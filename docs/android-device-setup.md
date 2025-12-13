# Android Device Setup Guide

## Automated LineageOS 14.1 + Magisk Root Installation for HTC One M7 Development

This guide provides step-by-step instructions for setting up HTC One M7 devices with LineageOS 14.1 and Magisk root access, specifically configured for MIA automotive application development.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Device Preparation](#device-preparation)
4. [Automated Installation](#automated-installation)
5. [Post-Installation Configuration](#post-installation-configuration)
6. [Verification and Testing](#verification-and-testing)
7. [Backup and Recovery](#backup-and-recovery)
8. [Troubleshooting](#troubleshooting)
9. [Maintenance](#maintenance)

## Prerequisites

### Hardware Requirements

- **HTC One M7 device** (unlocked bootloader required)
- **USB cable** (for device connection)
- **Ubuntu 24.04 LTS host system** (recommended)
- **Minimum 10GB free disk space**

### Software Requirements

- Bash shell environment
- ADB and Fastboot tools
- wget/curl for downloads
- unzip for archive extraction

### Device Requirements

- **Unlocked bootloader** (required for custom ROM installation)
- **USB debugging enabled**
- **Device authorized for USB debugging**
- **Battery charged above 50%**

### Warnings

⚠️ **IMPORTANT WARNINGS:**

- This process will **wipe all data** on your HTC One M7
- **Unlocking the bootloader** may void your warranty
- **Root access** can compromise device security
- **Custom ROMs** may have stability issues

**Backup all important data before proceeding!**

## Environment Setup

### 1. Verify Host Environment

Run the environment verification script to ensure your Ubuntu system is properly configured:

```bash
cd scripts/android-device-setup/environment
./verify-environment.sh
```

This script will:
- Check Ubuntu 24.04 compatibility
- Install required packages (adb, fastboot, wget, curl, unzip)
- Verify Android tools versions
- Setup udev rules for device access
- Create working directory structure

### 2. Grant USB Access

After running the environment script, add your user to the plugdev group and reboot:

```bash
sudo usermod -aG plugdev $USER
# Log out and back in, or reboot
```

## Device Preparation

### 1. Unlock Bootloader

⚠️ **This will wipe all data on your device!**

1. Power off your HTC One M7
2. Boot into bootloader mode:
   - Hold **Volume Down + Power** buttons simultaneously
   - Use **Volume keys** to select "FASTBOOT"
   - Press **Power** to confirm

3. Connect device to computer via USB

4. Verify fastboot connection:
   ```bash
   fastboot devices
   ```

5. Unlock bootloader (this erases all data):
   ```bash
   fastboot oem unlock
   ```

6. Follow on-screen instructions on device

### 2. Verify Device Connection

Run the device verification script:

```bash
cd scripts/android-device-setup/environment
./device-manager.sh setup
```

This will:
- Detect your HTC One M7
- Verify bootloader status
- Confirm HTC One M7 compatibility
- Test USB connection stability

## Automated Installation

### Option 1: Full Automated Installation (Recommended)

Run the master installation script:

```bash
cd scripts/android-device-setup/installation
./install-lineageos.sh
```

The script will automatically:
1. Verify environment and device
2. Download LineageOS 14.1 and GApps
3. Install TWRP recovery
4. Wipe device partitions
5. Flash LineageOS ROM and GApps
6. Install Magisk for root access
7. Configure device for development
8. Setup MIA application environment

### Option 2: Manual Step-by-Step Installation

If you prefer more control, run individual phases:

#### Phase 1: Recovery Installation
```bash
cd scripts/android-device-setup/recovery
./twrp-manager.sh install
./verify-recovery.sh verify
```

#### Phase 2: Download Files
```bash
cd scripts/android-device-setup/rom
./rom-manager.sh download-all
```

#### Phase 3: Transfer Files to Device
```bash
cd scripts/android-device-setup/rom
./file-transfer.sh batch <device_serial> <rom_file> <gapps_file>
```

#### Phase 4: Flash ROM
```bash
cd scripts/android-device-setup/installation
./flash-operations.sh wipe <device_serial>
./flash-operations.sh flash-rom <device_serial>
./flash-operations.sh flash-gapps <device_serial>
```

#### Phase 5: Install Root
```bash
cd scripts/android-device-setup/root
./magisk-manager.sh install <device_serial>
```

#### Phase 6: Post-Installation Setup
```bash
cd scripts/android-device-setup/post-install
./setup-dev-environment.sh configure <device_serial>
./mia-integration.sh setup <device_serial>
```

## Post-Installation Configuration

After installation completes, the device will reboot into LineageOS 14.1. Complete the initial Android setup:

1. **Language Selection**: Choose your preferred language
2. **WiFi Setup**: Connect to a WiFi network
3. **Google Account**: Skip or add Google account (optional)
4. **Device Setup**: Complete basic device configuration
5. **Developer Options**: Will be automatically enabled

## Verification and Testing

### 1. Health Check

Run a comprehensive health check:

```bash
cd scripts/android-device-setup/testing
./health-check.sh full <device_serial>
```

This verifies:
- Boot stability
- Core functionality (WiFi, Bluetooth, GPS)
- Battery health
- Performance metrics
- Hardware sensors

### 2. MIA Test Suite

Run MIA-specific tests:

```bash
cd scripts/android-device-setup/testing
./test-suite.sh full <device_serial>
```

This tests:
- MIA app installation
- Root access verification
- BLE connectivity
- OBD interface access
- MQTT networking
- Performance benchmarks

### 3. Root Verification

Verify root access:

```bash
cd scripts/android-device-setup/root
./verify-root.sh verify <device_serial>
```

## Backup and Recovery

### Creating Backups

Always create backups before making changes:

```bash
cd scripts/android-device-setup/backup
./backup-manager.sh create full <device_serial>
```

### Types of Backups

- **System Backup**: Complete system image
- **Data Backup**: User data and applications
- **Boot Backup**: Boot partition only

### Recovery Procedures

If something goes wrong:

#### Boot Loop Recovery
```bash
cd scripts/android-device-setup/backup
./recovery-procedures.sh bootloop <device_serial>
```

#### Failed Installation Rollback
```bash
cd scripts/android-device-setup/backup
./recovery-procedures.sh rollback <device_serial>
```

#### Emergency Recovery
```bash
cd scripts/android-device-setup/backup
./recovery-procedures.sh bricked <device_serial>
```

## Troubleshooting

### Common Issues

#### Device Not Detected
```bash
# Check USB connection
lsusb | grep HTC

# Restart ADB server
adb kill-server
adb start-server

# Check device authorization
adb devices
```

#### Fastboot Not Working
```bash
# Verify fastboot installation
fastboot --version

# Check device in fastboot mode
fastboot devices
```

#### Installation Fails
```bash
# Check logs
tail -f android-device-workspace/logs/installation.log

# Run diagnostics
cd scripts/android-device-setup/backup
./recovery-procedures.sh diagnostics <device_serial>
```

#### Root Not Working
```bash
# Verify Magisk installation
cd scripts/android-device-setup/root
./verify-root.sh verify <device_serial>

# Reinstall Magisk
./magisk-manager.sh install <device_serial>
```

### Log Files

All operations are logged to:
- `android-device-workspace/logs/` - Main operation logs
- `android-device-workspace/test-results/` - Test results
- `android-device-workspace/reports/` - Generated reports

### Getting Help

1. **Check the logs** in `android-device-workspace/logs/`
2. **Run diagnostics** using recovery procedures
3. **Generate reports** for detailed analysis
4. **Check device forums** for HTC One M7 specific issues

## Maintenance

### Regular Tasks

#### Weekly Health Checks
```bash
cd scripts/android-device-setup/testing
./health-check.sh full <device_serial>
```

#### Monthly Backups
```bash
cd scripts/android-device-setup/backup
./backup-manager.sh create full <device_serial>
```

#### Update Management
```bash
# Update Magisk
cd scripts/android-device-setup/root
./magisk-manager.sh update <device_serial>

# Update MIA app (when available)
# Deploy updated APK through development workflow
```

### Performance Monitoring

Monitor device performance:

```bash
cd scripts/android-device-setup/testing
./health-check.sh performance <device_serial>
```

### Storage Management

Clean up old backups:

```bash
cd scripts/android-device-setup/backup
./backup-manager.sh clean <device_serial>
```

## Advanced Usage

### Custom Configuration

Edit configuration files in `android-device-workspace/`:
- `installation-config.txt` - Installation settings
- `installation-checkpoint.txt` - Resume interrupted installations

### Manual Operations

All automated scripts can be run individually for manual control:

```bash
# Environment
./scripts/android-device-setup/environment/verify-environment.sh
./scripts/android-device-setup/environment/device-manager.sh setup

# Recovery
./scripts/android-device-setup/recovery/twrp-manager.sh install
./scripts/android-device-setup/recovery/verify-recovery.sh verify

# Downloads
./scripts/android-device-setup/rom/rom-manager.sh download-all

# Installation
./scripts/android-device-setup/installation/flash-operations.sh wipe
./scripts/android-device-setup/installation/flash-operations.sh flash-rom

# Root
./scripts/android-device-setup/root/magisk-manager.sh install

# Configuration
./scripts/android-device-setup/post-install/setup-dev-environment.sh configure
./scripts/android-device-setup/post-install/mia-integration.sh setup

# Testing
./scripts/android-device-setup/testing/health-check.sh full
./scripts/android-device-setup/testing/test-suite.sh full
```

### Report Generation

Generate comprehensive reports:

```bash
cd scripts/android-device-setup/reporting
./generate-report.sh comprehensive <device_serial>
```

Available report types:
- `installation` - Installation progress and status
- `system` - Device system information
- `performance` - Performance metrics and benchmarks
- `health` - Health assessment and diagnostics
- `backup` - Backup status and history
- `testing` - Test results and analysis
- `comprehensive` - Complete system analysis

## Support Resources

- **LineageOS Wiki**: https://wiki.lineageos.org/devices/m7
- **TWRP Documentation**: https://twrp.me/Devices/HTCOneM7.html
- **Magisk Documentation**: https://topjohnwu.github.io/Magisk/
- **Android Developer Tools**: https://developer.android.com/studio/run/device
- **XDA Developers HTC One M7**: https://forum.xda-developers.com/t/htc-one-m7-development.123456/

## Version History

- **v1.0** - Initial release with complete automated installation system
- Support for LineageOS 14.1, Magisk root, and MIA app integration
- Comprehensive testing and health monitoring
- Backup and recovery procedures
- Detailed reporting and documentation

---

*This guide is maintained as part of the MIA Automotive project. For issues or contributions, please refer to the project repository.*