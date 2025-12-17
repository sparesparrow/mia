# Conan Package Management Analysis

## Executive Summary

This document provides a comprehensive analysis of the Conan C++ package management setup in the `ai-servis` project, including configuration, dependencies, build processes, and CI/CD integration.

## 1. Conan Version and Configuration

### Version
- **Conan Version**: 2.21.0 (latest stable)
- **Status**: ✅ Properly installed and functional

### Remotes Configuration
Two remotes are configured:

1. **conancenter** (Deprecated)
   - URL: `https://center.conan.io`
   - Status: ⚠️ **DEPRECATED** - Should be updated to `center2.conan.io`
   - Contains: 8,441+ packages (standard ConanCenter repository)
   - Action Required: Update to `https://center2.conan.io`

2. **sparesparrow-conan** (Custom Remote)
   - URL: `https://conan.cloudsmith.io/sparesparrow-conan/openssl-conan/`
   - Status: ✅ Active
   - Contains: 37 packages (custom OpenSSL and related packages)
   - Purpose: Custom packages for the project

### Profiles

#### Default Profile
- **OS**: Linux
- **Architecture**: armv8 (Raspberry Pi)
- **Compiler**: GCC 14
- **C++ Standard**: gnu17
- **Standard Library**: libstdc++11
- **Build Type**: Release

#### Custom Profiles Available
Located in `profiles/` directory:

1. **linux-arm64** (Raspberry Pi)
   - GCC 11, armv8, Release
   - Static linking for all dependencies
   - Ninja generator
   - System package manager enabled

2. **linux-release** (x86_64)
   - GCC 13, x86_64, Release
   - C++17 standard
   - Static linking
   - Unix Makefiles generator

3. **linux-simulation** (for testing)
4. **macos-release** (macOS builds)
5. **windows-release** (Windows builds)

## 2. Main Package Configuration (`conanfile.py`)

### Package Metadata
- **Name**: `mia`
- **Version**: 1.0
- **Description**: AI Service with MCP and Hardware Control

### Options
- `shared`: False (static linking)
- `fPIC`: True (Position Independent Code)
- `with_hardware`: True (GPIO, MQTT support)
- `with_mcp`: True (Model Context Protocol support)

### Core Dependencies (Always Required)
1. **jsoncpp/1.9.5** - JSON handling
2. **flatbuffers/23.5.26** - Serialization
3. **libcurl/8.5.0** - HTTP client
4. **openssl/3.0.8** - SSL/TLS support
5. **zlib/1.2.13** - Compression

### Conditional Dependencies

#### Hardware Support (`with_hardware=True`)
- **libgpiod/2.0.1** - GPIO control for Raspberry Pi
- **mosquitto/2.0.18** - MQTT communication

#### Build Tools (tool_requires)
- **flatbuffers/23.5.26** - For `flatc` compiler
- **sparetools-obd-sim/2.0.0** - OBD simulator for testing

### Build Process Features
- **FlatBuffers Generation**: Automatically generates C++ headers from `.fbs` schemas
- **Python Bindings**: Generates Python bindings for Vehicle schema
- **CMake Integration**: Full CMake toolchain and dependency generation
- **Virtual Environment**: Runtime environment generation

## 3. Custom Conan Recipes

### 3.1 kernun-mcp-tools (`conan-recipes/kernun-mcp-tools/`)

**Purpose**: Proxy MCP integration for network security analysis

**Version**: 0.1.0

**Dependencies**:
- jsoncpp/1.9.5
- openssl/3.3.2
- libcurl/8.10.1
- spdlog/1.13.0 (optional, for logging)

**Features**:
- Dynamically generates C++ wrapper sources
- Provides MCP tools for:
  - Network traffic analysis
  - Session inspection
  - TLS policy management
  - Proxy rules management
  - Clearweb database updates
- Supports both static and shared library builds
- Optional demo and test builds

### 3.2 tinymcp (`conan-recipes/tinymcp/`)

**Purpose**: Lightweight C++ SDK for MCP servers and clients

**Version**: 0.2.0

**Dependencies**:
- jsoncpp/1.9.5 (or system JSON)
- spdlog/1.13.0 (optional, for logging)

**Features**:
- Minimalistic, high-performance MCP implementation
- Supports system JSON library option
- Optional examples and tests
- CMake-based build system

## 4. Dependency Graph Analysis

### Current Dependency Resolution
All dependencies are **successfully resolved** and **cached**:

```
Requirements (7 packages):
  ✓ flatbuffers/23.5.26 - Cache
  ✓ jsoncpp/1.9.5 - Cache
  ✓ libcurl/8.5.0 - Cache
  ✓ libgpiod/2.0.1 - Cache
  ✓ mosquitto/2.0.18 - Cache
  ✓ openssl/3.0.8 - Cache
  ✓ zlib/1.2.13 - Cache

Build Requirements (12 packages):
  ✓ flatbuffers/23.5.26 - Cache
  ✓ sparetools-obd-sim/2.0.0 - Cache
  ✓ autoconf, automake, libtool, m4, meson, ninja, pkgconf - Cache

Python Requires:
  ✓ sparetools-base/2.0.0 - Cache
```

### Local Cache Status
**26 packages** are cached locally:
- Multiple versions of some packages (e.g., flatbuffers 23.5.26 and 24.3.25)
- All dependencies are pre-built and ready for use
- No missing binaries detected

## 5. Build Process

### Installation Command
```bash
conan install . --build=missing --profile=profiles/linux-arm64
```

### Generated Artifacts
1. **CMake Toolchain**: `build-release/conan/conan_toolchain.cmake`
2. **CMake Presets**: `build-release/conan/CMakePresets.json`
3. **CMake Dependencies**: All `find_package()` configurations
4. **Environment Scripts**: `conanrun.sh`, `conanbuild.sh`

### CMake Integration
The generated files enable seamless CMake integration:

```cmake
find_package(jsoncpp)
find_package(flatbuffers)
find_package(CURL)
find_package(libgpiod)
find_package(mosquitto)
find_package(OpenSSL)
find_package(ZLIB)

target_link_libraries(... 
    JsonCpp::JsonCpp 
    flatbuffers::flatbuffers 
    CURL::libcurl 
    libgpiod::libgpiod 
    mosquitto::mosquitto 
    openssl::openssl 
    ZLIB::ZLIB
)
```

## 6. CI/CD Integration

### GitHub Actions Workflows

#### C++ Build Workflow (`.github/workflows/cpp.yml`)
- **Triggers**: Changes to `platforms/cpp/**`, `conanfile.py`, `profiles/**`
- **Matrix Strategy**: 
  - Ubuntu x86_64 (linux-release profile)
  - Ubuntu ARM64 (linux-arm64 profile)
- **Steps**:
  1. Install Conan
  2. Cache Conan packages (`~/.conan`)
  3. Install dependencies: `conan install ../.. --profile profiles/${{ matrix.profile }} --build missing`
  4. Configure CMake with Conan toolchain
  5. Build with CMake
  6. Upload artifacts

#### RPI Python Conan Workflow (`ci/github-actions/rpi-python-conan.yml`)
- Similar structure for Raspberry Pi Python services

### Build Orchestrator
- `build_orchestrator.py` contains `ConanOrchestrator` class
- Manages complex build matrices and dependency resolution

## 7. Issues and Recommendations

### ⚠️ Critical Issues

1. **Deprecated Remote**
   - **Issue**: `conancenter` remote uses deprecated URL
   - **Impact**: May stop working in future Conan versions
   - **Fix**: 
     ```bash
     conan remote update conancenter --url="https://center2.conan.io"
     ```

2. **Deprecated Conan 1.X Features**
   - **Issue**: Some dependencies use deprecated `env_info`, `cpp_info.names`, `cpp_info.build_modules`
   - **Impact**: Compatibility warnings, may break in Conan 2.X
   - **Affected Packages**: autoconf, libtool, openssl, flatbuffers, jsoncpp, libcurl, zlib
   - **Action**: Monitor for updates to these packages

### ✅ Best Practices Observed

1. **Profile Management**: Well-organized custom profiles for different platforms
2. **Static Linking**: Consistent use of static libraries for deployment
3. **Version Pinning**: Specific versions for all dependencies (no wildcards)
4. **Conditional Dependencies**: Proper use of options for optional features
5. **Build Tools**: Separate `tool_requires` for build-time tools
6. **CMake Integration**: Proper use of CMakeToolchain and CMakeDeps
7. **Cache Strategy**: Effective caching in CI/CD workflows

### 📋 Recommendations

1. **Update Remote URL** (High Priority)
   ```bash
   conan remote update conancenter --url="https://center2.conan.io"
   ```

2. **Version Management**
   - Consider using version ranges for minor updates (e.g., `flatbuffers/[>=23.5 <24]`)
   - Document version update policy

3. **Lock Files**
   - Consider using `conan lock` for reproducible builds
   - Generate lock files for CI/CD pipelines

4. **Custom Package Testing**
   - Add tests for `kernun-mcp-tools` and `tinymcp` recipes
   - Validate builds on multiple platforms

5. **Documentation**
   - Document custom recipe build requirements
   - Add troubleshooting guide for common Conan issues

6. **Dependency Updates**
   - Regularly update dependencies for security patches
   - Test updates in isolated branches

## 8. Package Statistics

### Local Cache
- **Total Packages**: 26 unique package/version combinations
- **Total Size**: (Not measured, but significant given compiled binaries)
- **Cache Location**: `~/.conan2/`

### Remote Availability
- **ConanCenter**: 8,441+ packages
- **sparesparrow-conan**: 37 packages (custom)

## 9. Build Performance

### Installation Time
- **Dependencies**: All cached, instant resolution
- **Build Time**: Depends on `--build=missing` flag
  - Cached packages: < 1 second
  - Building from source: 5-30 minutes (especially for large packages like OpenSSL)

### CI/CD Optimization
- Effective caching strategy reduces build times
- Matrix builds allow parallel execution
- Artifact uploads preserve build outputs

## 10. Conclusion

The Conan setup in `ai-servis` is **well-configured and functional**. The project demonstrates:

✅ Proper use of Conan 2.x features  
✅ Well-organized profile management  
✅ Effective CI/CD integration  
✅ Custom recipe development  
✅ Comprehensive dependency management  

**Immediate Action Required**: Update the deprecated `conancenter` remote URL to `center2.conan.io`.

**Overall Assessment**: ⭐⭐⭐⭐ (4/5) - Excellent setup with minor improvements needed.

---

*Analysis Date: December 17, 2025*  
*Conan Version: 2.21.0*  
*Project: ai-servis*
