# Windows Android Development Setup

This guide helps you set up the Android development environment on Windows to build the MIA Universal app.

## 🔍 Common Issues & Solutions

### Issue: "SDK location not found"

**Symptoms:**
```
FAILURE: Build failed with an exception.
* What went wrong:
Could not determine the dependencies of task ':app:compileDebugJavaWithJavac'.
> Could not determine the dependencies of null.
   > SDK location not found. Define a valid SDK location with an ANDROID_HOME environment variable or by setting the sdk.dir path in your project's local properties file
```

**Solutions:**

#### Solution 1: Install Android Studio (Recommended)
1. Download Android Studio: https://developer.android.com/studio
2. Install with default settings
3. Launch Android Studio and complete SDK setup
4. The SDK will be installed to: `C:\Users\%USERNAME%\AppData\Local\Android\Sdk`

#### Solution 2: Install Android SDK Command-Line Tools Only
1. Download command-line tools: https://developer.android.com/studio#command-tools
2. Extract to: `C:\Users\%USERNAME%\android-sdk\cmdline-tools\latest`
3. Run setup script: `.\tools\setup-android-env.ps1`

#### Solution 3: Use Existing SDK
If you have Android SDK installed elsewhere:
1. Update `android/local.properties`:
   ```
   sdk.dir=C:\\Path\\To\\Your\\Android\\Sdk
   ```
2. Or set environment variable:
   ```cmd
   setx ANDROID_HOME "C:\Path\To\Your\Android\Sdk"
   ```

### Issue: "PowerShell version not supported"

**Symptoms:**
```
build.ps1 : The script 'build.ps1' cannot be run because it contains a "#requires" statement for PowerShell 7+ but the currently running version of Windows PowerShell 5.1.xxxx.
```

**Solutions:**

#### Solution 1: Use PowerShell 7
1. Download PowerShell 7: https://github.com/PowerShell/PowerShell/releases
2. Install and use `pwsh.exe` instead of `powershell.exe`

#### Solution 2: The build scripts are now compatible with PowerShell 5.1

### Issue: Gradle Build Fails

**Check these first:**
1. **Java Version**: Run `java -version` (should be Java 17+)
2. **Android SDK**: Run `.\tools\setup-android-env.ps1`
3. **Environment Variables**: Restart terminal after setting `ANDROID_HOME`

## 🚀 Quick Setup

### Prerequisites
- Windows 10/11
- Java 17+ (Temurin recommended)
- 8GB+ RAM
- 10GB+ free disk space

### Step 1: Install Android SDK
```powershell
# Run setup script
cd android
.\tools\setup-android-env.ps1
```

### Step 2: Verify Environment
```powershell
# Check Java
java -version

# Check Android SDK
echo $env:ANDROID_HOME

# Check ADB
adb version
```

### Step 3: Build the App
```powershell
# Build debug APK
.\build.ps1 -BuildType Debug

# Build release APK
.\build.ps1 -BuildType Release
```

## 📁 Project Structure

```
android/
├── local.properties          # Android SDK location (created)
├── build.gradle             # Root build configuration
├── app/
│   ├── build.gradle         # App-specific configuration
│   └── src/main/
│       ├── AndroidManifest.xml
│       └── java/cz/mia/app/  # Source code
├── tools/
│   ├── build-in-docker.sh   # Docker build script
│   ├── build.ps1            # Windows build script
│   ├── setup-android-env.ps1 # Environment setup
│   └── deploy-apk.ps1       # Deployment script
└── keystore/                # Release signing keys
```

## 🔧 Build Scripts

### Windows Native Build
```powershell
# Debug build
.\build.ps1 -BuildType Debug

# Clean and build
.\build.ps1 -BuildType Debug -Clean

# Build and install to device
.\build.ps1 -BuildType Debug -Install
```

### Docker Build (Alternative)
```bash
# Using WSL or Git Bash
./tools/build-in-docker.sh --task assembleDebug
```

## 📱 Testing & Deployment

### Unit Tests
```powershell
.\gradlew.bat test
```

### Instrumented Tests
```powershell
.\gradlew.bat connectedAndroidTest
```

### Deploy to Device
```powershell
.\tools\deploy-apk.ps1 -BuildType Debug -Launch
```

## 🐛 Troubleshooting

### Build Still Fails?

1. **Check Environment**:
   ```powershell
   .\tools\diagnose-build.ps1
   ```

2. **Clear Gradle Cache**:
   ```powershell
   Remove-Item -Recurse -Force ~/.gradle/caches
   cd android
   .\gradlew.bat clean
   ```

3. **Check Logs**:
   - Gradle logs: `android/app/build/reports/`
   - System logs: Event Viewer → Windows Logs → Application

### SDK Component Issues?

Run SDK Manager:
```cmd
"%ANDROID_HOME%\cmdline-tools\latest\bin\sdkmanager.bat" --list
```

Install missing components:
```cmd
sdkmanager "platform-tools" "platforms;android-34" "build-tools;34.0.0"
```

## 📚 Additional Resources

- [Android Developer Documentation](https://developer.android.com/)
- [Gradle Build Tools](https://developer.android.com/studio/build)
- [Android Studio Setup](https://developer.android.com/studio/install)

## 🎯 Success Checklist

- [ ] Java 17+ installed
- [ ] Android SDK installed and `ANDROID_HOME` set
- [ ] ADB available in PATH
- [ ] Gradle wrapper works: `.\gradlew.bat --version`
- [ ] Debug build succeeds: `.\build.ps1 -BuildType Debug`
- [ ] APK generated in `app/build/outputs/apk/debug/`
- [ ] App installs and runs on device/emulator

---

**Need Help?** Check the debug logs at `../../../.cursor/debug.log` for detailed diagnostics.
