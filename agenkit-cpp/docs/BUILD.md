# Building Agenkit C++

This document describes how to build agenkit-cpp from source.

---

## Prerequisites

### Compiler

C++17 compatible compiler:
- **GCC**: 7.0 or later
- **Clang**: 5.0 or later
- **MSVC**: Visual Studio 2017 or later

### Build Tools

- **CMake**: 3.16 or later
- **Ninja** (optional, but recommended for faster builds)

### Dependencies

Required:
- **nlohmann/json**: 3.11.0 or later (JSON library)
- **cpp-httplib**: 0.14.0 or later (HTTP client/server)

Optional:
- **Google Test**: 1.12.1 or later (for testing, auto-downloaded via FetchContent)
- **spdlog**: Latest (for logging, optional)

---

## Dependency Installation

### Option 1: vcpkg (Recommended)

```bash
# Install vcpkg
git clone https://github.com/microsoft/vcpkg.git
cd vcpkg
./bootstrap-vcpkg.sh  # or bootstrap-vcpkg.bat on Windows

# Install dependencies
./vcpkg install nlohmann-json cpp-httplib

# Use with CMake
cmake -B build -DCMAKE_TOOLCHAIN_FILE=path/to/vcpkg/scripts/buildsystems/vcpkg.cmake
```

### Option 2: Conan

Create `conanfile.txt`:

```ini
[requires]
nlohmann_json/3.11.3
cpp-httplib/0.14.0

[generators]
cmake_find_package
```

Install and build:

```bash
conan install . --install-folder=build --build=missing
cmake -B build -DCMAKE_PREFIX_PATH=build
cmake --build build
```

### Option 3: System Package Manager

**Ubuntu/Debian**:
```bash
sudo apt-get update
sudo apt-get install nlohmann-json3-dev
# cpp-httplib may need manual installation or vcpkg
```

**macOS (Homebrew)**:
```bash
brew install nlohmann-json
# cpp-httplib: brew install cpp-httplib (if available) or use vcpkg
```

**Windows (vcpkg recommended)**:
See Option 1 above.

---

## Building

### Quick Build

```bash
# Configure
cmake -B build

# Build
cmake --build build

# Test
ctest --test-dir build

# Install (optional)
cmake --install build --prefix /usr/local
```

### Build Types

**Debug** (default):
```bash
cmake -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build
```

**Release** (optimized):
```bash
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
```

**RelWithDebInfo** (optimized + debug symbols):
```bash
cmake -B build -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build build
```

### Build Options

**Disable examples**:
```bash
cmake -B build -DAGENKIT_BUILD_EXAMPLES=OFF
```

**Disable tests**:
```bash
cmake -B build -DAGENKIT_BUILD_TESTS=OFF
```

**Build static library** (instead of shared):
```bash
cmake -B build -DAGENKIT_BUILD_SHARED=OFF
```

**Use Ninja**:
```bash
cmake -B build -G Ninja
ninja -C build
```

---

## Running Examples

After building:

```bash
# Echo agent
./build/examples/echo_agent

# HTTP transport
./build/examples/http_transport
```

---

## Running Tests

Run all tests:

```bash
ctest --test-dir build --output-on-failure
```

Run specific test:

```bash
./build/tests/test_message
./build/tests/test_agent
./build/tests/test_http_transport
```

Run with verbose output:

```bash
ctest --test-dir build --verbose
```

---

## Platform-Specific Instructions

### Linux

```bash
# Install dependencies (Ubuntu/Debian)
sudo apt-get install build-essential cmake ninja-build nlohmann-json3-dev

# Install vcpkg for cpp-httplib
git clone https://github.com/microsoft/vcpkg.git
./vcpkg/bootstrap-vcpkg.sh
./vcpkg/vcpkg install cpp-httplib

# Build
cmake -B build -DCMAKE_TOOLCHAIN_FILE=vcpkg/scripts/buildsystems/vcpkg.cmake
cmake --build build -j$(nproc)
```

### macOS

```bash
# Install dependencies
brew install cmake ninja nlohmann-json

# Install cpp-httplib via vcpkg
git clone https://github.com/microsoft/vcpkg.git
./vcpkg/bootstrap-vcpkg.sh
./vcpkg/vcpkg install cpp-httplib

# Build
cmake -B build -DCMAKE_TOOLCHAIN_FILE=vcpkg/scripts/buildsystems/vcpkg.cmake
cmake --build build -j$(sysctl -n hw.ncpu)
```

### Windows

Using Visual Studio:

```bash
# Install vcpkg
git clone https://github.com/microsoft/vcpkg.git
cd vcpkg
.\bootstrap-vcpkg.bat
.\vcpkg install nlohmann-json:x64-windows cpp-httplib:x64-windows

# Open Visual Studio
cmake -B build -DCMAKE_TOOLCHAIN_FILE=vcpkg\scripts\buildsystems\vcpkg.cmake -A x64
cmake --build build --config Release
```

Using MinGW:

```bash
# Install MSYS2 and MinGW
# Then follow Linux instructions with mingw-w64 toolchain
```

---

## Development Build

For active development with fast rebuilds:

```bash
# Use Ninja for parallel builds
cmake -B build -G Ninja -DCMAKE_BUILD_TYPE=Debug

# Build with all CPU cores
ninja -C build

# Rebuild only changed files
ninja -C build

# Clean and rebuild
ninja -C build clean
ninja -C build
```

---

## Static Analysis

### clang-tidy

```bash
# Generate compile_commands.json
cmake -B build -DCMAKE_EXPORT_COMPILE_COMMANDS=ON

# Run clang-tidy
clang-tidy -p build src/**/*.cpp include/**/*.hpp
```

### cppcheck

```bash
cppcheck --enable=all --std=c++17 src/ include/
```

---

## Memory Checking

### Valgrind (Linux/macOS)

```bash
# Build with debug symbols
cmake -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build

# Run with valgrind
valgrind --leak-check=full ./build/examples/echo_agent
```

### AddressSanitizer

```bash
# Build with sanitizer
cmake -B build -DCMAKE_BUILD_TYPE=Debug \
  -DCMAKE_CXX_FLAGS="-fsanitize=address -fno-omit-frame-pointer"
cmake --build build

# Run (will detect memory errors)
./build/examples/echo_agent
```

---

## Troubleshooting

### CMake can't find dependencies

**Problem**: `Could not find nlohmann_json`

**Solution**: Use vcpkg toolchain file:
```bash
cmake -B build -DCMAKE_TOOLCHAIN_FILE=path/to/vcpkg/scripts/buildsystems/vcpkg.cmake
```

### Compiler errors about C++17

**Problem**: Compiler doesn't support C++17

**Solution**: Update compiler:
- GCC: `sudo apt-get install gcc-9 g++-9`
- Clang: `sudo apt-get install clang-10`
- MSVC: Update to Visual Studio 2017 or later

### Linker errors

**Problem**: `undefined reference to...`

**Solution**: Check that all dependencies are linked in CMakeLists.txt:
```cmake
target_link_libraries(agenkit
    PUBLIC nlohmann_json::nlohmann_json
    PRIVATE httplib::httplib Threads::Threads
)
```

### Tests fail to build

**Problem**: Google Test not found

**Solution**: Google Test is auto-downloaded via FetchContent. Ensure you have internet access during configuration:
```bash
cmake -B build -DAGENKIT_BUILD_TESTS=ON
```

---

## Installation

System-wide install (requires root/admin):

```bash
cmake --install build --prefix /usr/local
```

User install:

```bash
cmake --install build --prefix ~/.local
```

Custom location:

```bash
cmake --install build --prefix /path/to/install
```

---

## IDE Integration

### Visual Studio Code

1. Install CMake Tools extension
2. Configure CMake:
   ```json
   {
     "cmake.configureSettings": {
       "CMAKE_TOOLCHAIN_FILE": "path/to/vcpkg/scripts/buildsystems/vcpkg.cmake"
     }
   }
   ```
3. Select kit (compiler)
4. Build with Ctrl+Shift+B

### CLion

1. Open agenkit-cpp directory
2. CLion auto-detects CMakeLists.txt
3. Configure CMake settings in Settings → Build, Execution, Deployment → CMake
4. Build with Ctrl+F9

### Visual Studio

1. Open agenkit-cpp folder
2. Visual Studio auto-detects CMakeLists.txt
3. Configure CMake settings in CMakeSettings.json
4. Build with Ctrl+Shift+B

---

## Next Steps

After successful build:

1. Run examples to verify installation
2. Run tests to ensure everything works
3. Start implementing core components!

---

**Last Updated**: November 26, 2025
