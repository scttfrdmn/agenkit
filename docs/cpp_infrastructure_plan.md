# C++ Infrastructure Plan (v0.29.0)

**Target**: December 2025 (4 weeks)
**Issue**: #143
**Goal**: Complete C++ infrastructure ready for pattern implementation

---

## Overview

Implement core C++ infrastructure matching Python/Go/TypeScript/Rust architecture:
- Core Agent interface (virtual base class)
- HTTP transport with modern C++ HTTP library
- Message protocol with JSON serialization
- CMake build system
- Google Test framework
- 2 working examples
- 25 infrastructure tests
- Documentation

---

## Architecture Design

### Directory Structure

```
agenkit-cpp/
├── CMakeLists.txt              # Root build configuration
├── README.md                    # C++ documentation
├── .github/
│   └── workflows/
│       └── cpp-ci.yml          # CI/CD pipeline
├── include/                     # Public headers
│   └── agenkit/
│       ├── core/
│       │   ├── agent.hpp       # Agent interface
│       │   ├── message.hpp     # Message types
│       │   └── errors.hpp      # Error types
│       ├── adapters/
│       │   └── echo_agent.hpp  # Simple echo agent
│       └── transports/
│           ├── http_agent.hpp  # HTTP client
│           └── http_server.hpp # HTTP server
├── src/                         # Implementation files
│   ├── core/
│   │   ├── message.cpp
│   │   └── errors.cpp
│   ├── adapters/
│   │   └── echo_agent.cpp
│   └── transports/
│       ├── http_agent.cpp
│       └── http_server.cpp
├── examples/                    # Working examples
│   ├── echo_agent.cpp
│   ├── http_transport.cpp
│   └── CMakeLists.txt
├── tests/                       # Unit tests
│   ├── test_message.cpp
│   ├── test_agent.cpp
│   ├── test_http_transport.cpp
│   └── CMakeLists.txt
├── cmake/                       # CMake modules
│   ├── FindCppHttpLib.cmake
│   └── Dependencies.cmake
└── docs/                        # Additional documentation
    └── BUILD.md                 # Build instructions
```

---

## Core Components

### 1. Agent Interface (~300 LOC)

**File**: `include/agenkit/core/agent.hpp`

**Design**:
```cpp
// Modern C++17 interface following Rust/Go patterns
namespace agenkit {
namespace core {

// Forward declarations
class Message;
class AgentError;

// Agent interface - minimal contract
class Agent {
public:
    virtual ~Agent() = default;

    // Agent identifier
    virtual std::string name() const = 0;

    // Process message (async via std::future or callback)
    virtual std::future<Result<Message, AgentError>>
        process(Message message) = 0;

    // Optional capabilities
    virtual std::vector<std::string> capabilities() const {
        return {};
    }
};

// Result type for error handling (std::expected in C++23, custom otherwise)
template<typename T, typename E>
class Result {
    // Similar to Rust Result<T, E>
    // Uses std::variant<T, E> internally
};

} // namespace core
} // namespace agenkit
```

**Key Decisions**:
- Use C++17 standard (widely supported)
- Virtual interface for polymorphism
- `std::future` for async operations (or custom async if needed)
- Custom `Result<T, E>` type for error handling (until C++23 `std::expected`)
- Header-only option for some utilities
- Move semantics for efficiency
- Smart pointers (`shared_ptr`, `unique_ptr`) for memory safety

**Error Handling**:
```cpp
// include/agenkit/core/errors.hpp
namespace agenkit {
namespace core {

enum class AgentErrorType {
    ProcessingError,
    Timeout,
    NotFound,
    Transport,
    Serialization,
    Http,
    Internal,
    InvalidInput
};

class AgentError : public std::exception {
public:
    AgentError(AgentErrorType type, std::string message);

    const char* what() const noexcept override;
    AgentErrorType type() const noexcept;
    const std::string& message() const noexcept;

private:
    AgentErrorType type_;
    std::string message_;
};

} // namespace core
} // namespace agenkit
```

---

### 2. Message Protocol (~150 LOC)

**File**: `include/agenkit/core/message.hpp`

**Design**:
```cpp
// Modern C++ message type with move semantics
namespace agenkit {
namespace core {

// Message content (variant: text, tool_use, tool_result)
class MessageContent {
public:
    enum class Type { Text, ToolUse, ToolResult };

    // Factory methods
    static MessageContent text(std::string text);
    static MessageContent tool_use(std::string tool_name, nlohmann::json args);
    static MessageContent tool_result(std::string tool_use_id, nlohmann::json result);

    // Accessors
    Type type() const;
    const std::string& as_text() const;
    const std::string& tool_name() const;
    const nlohmann::json& tool_args() const;

    // JSON serialization
    nlohmann::json to_json() const;
    static MessageContent from_json(const nlohmann::json& j);

private:
    Type type_;
    std::variant<std::string, /* tool_use */, /* tool_result */> content_;
};

// Message with role and optional metadata
class Message {
public:
    // Constructors
    Message(std::string role, MessageContent content);

    // Factory methods
    static Message with_text(std::string role, std::string text);

    // Accessors
    const std::string& role() const;
    const MessageContent& content() const;
    const nlohmann::json& metadata() const;

    // Builders (fluent interface)
    Message& with_metadata(std::string key, nlohmann::json value);

    // JSON serialization
    nlohmann::json to_json() const;
    static Message from_json(const nlohmann::json& j);

private:
    std::string role_;
    MessageContent content_;
    nlohmann::json metadata_;
};

// ToolResult type
class ToolResult {
public:
    ToolResult(std::string tool_use_id, nlohmann::json result, bool is_error = false);

    const std::string& tool_use_id() const;
    const nlohmann::json& result() const;
    bool is_error() const;

    nlohmann::json to_json() const;
    static ToolResult from_json(const nlohmann::json& j);

private:
    std::string tool_use_id_;
    nlohmann::json result_;
    bool is_error_;
};

} // namespace core
} // namespace agenkit
```

**Key Decisions**:
- Use `nlohmann::json` for JSON (most popular C++ JSON library)
- Move semantics for zero-copy when possible
- Fluent builder interface for metadata
- `std::variant` for content types
- Value semantics by default, move when needed

---

### 3. HTTP Transport (~250 LOC)

**File**: `include/agenkit/transports/http_agent.hpp`

**Design**:
```cpp
// HTTP client using cpp-httplib
namespace agenkit {
namespace transports {

struct HttpTransportConfig {
    std::string base_url;
    int timeout_secs = 30;
    std::optional<std::string> api_key;
};

// HTTP client agent
class HttpAgent : public core::Agent {
public:
    HttpAgent(std::string name, HttpTransportConfig config);
    ~HttpAgent() override;

    // Agent interface
    std::string name() const override;
    std::future<core::Result<core::Message, core::AgentError>>
        process(core::Message message) override;

private:
    std::string name_;
    HttpTransportConfig config_;
    std::unique_ptr<httplib::Client> client_;
};

// HTTP server
class HttpServer {
public:
    HttpServer(std::shared_ptr<core::Agent> agent, std::string address);
    ~HttpServer();

    // Start server (blocking)
    void serve();

    // Stop server (call from another thread)
    void stop();

private:
    std::shared_ptr<core::Agent> agent_;
    std::string address_;
    std::unique_ptr<httplib::Server> server_;

    // Handlers
    void handle_process(const httplib::Request& req, httplib::Response& res);
    void handle_health(const httplib::Request& req, httplib::Response& res);
};

} // namespace transports
} // namespace agenkit
```

**Key Decisions**:
- Use `cpp-httplib` (header-only, modern, easy to integrate)
- Alternative: libcurl (more mature but more complex)
- `std::shared_ptr` for agent ownership in server
- Thread-safe server stop mechanism
- JSON request/response bodies
- RESTful endpoints: POST /process, GET /health

---

### 4. Build System (CMake)

**File**: `CMakeLists.txt`

**Design**:
```cmake
cmake_minimum_required(VERSION 3.16)
project(agenkit VERSION 0.29.0 LANGUAGES CXX)

# C++17 standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Options
option(AGENKIT_BUILD_EXAMPLES "Build examples" ON)
option(AGENKIT_BUILD_TESTS "Build tests" ON)
option(AGENKIT_BUILD_SHARED "Build shared library" ON)

# Dependencies
find_package(nlohmann_json 3.11.0 REQUIRED)
find_package(Threads REQUIRED)

# cpp-httplib (header-only, vendored or system)
add_subdirectory(third_party/cpp-httplib EXCLUDE_FROM_ALL)

# Library target
add_library(agenkit
    src/core/message.cpp
    src/core/errors.cpp
    src/adapters/echo_agent.cpp
    src/transports/http_agent.cpp
    src/transports/http_server.cpp
)

target_include_directories(agenkit
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/src
)

target_link_libraries(agenkit
    PUBLIC
        nlohmann_json::nlohmann_json
    PRIVATE
        httplib::httplib
        Threads::Threads
)

# Compiler warnings
if(MSVC)
    target_compile_options(agenkit PRIVATE /W4)
else()
    target_compile_options(agenkit PRIVATE -Wall -Wextra -Wpedantic)
endif()

# Examples
if(AGENKIT_BUILD_EXAMPLES)
    add_subdirectory(examples)
endif()

# Tests
if(AGENKIT_BUILD_TESTS)
    enable_testing()
    add_subdirectory(tests)
endif()

# Install rules
install(TARGETS agenkit
    EXPORT agenkitTargets
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
    RUNTIME DESTINATION bin
    INCLUDES DESTINATION include
)

install(DIRECTORY include/
    DESTINATION include
)
```

**Key Decisions**:
- Modern CMake (3.16+)
- Header/source separation for library
- Optional shared/static library builds
- Find system dependencies (nlohmann_json)
- Vendor cpp-httplib (or use system)
- Install targets for package management
- Compiler warning flags

---

### 5. Testing Framework (Google Test)

**File**: `tests/CMakeLists.txt`

**Design**:
```cmake
# Fetch Google Test
include(FetchContent)
FetchContent_Declare(
    googletest
    GIT_REPOSITORY https://github.com/google/googletest.git
    GIT_TAG release-1.12.1
)
FetchContent_MakeAvailable(googletest)

# Test utilities
add_library(test_utils STATIC test_utils.cpp)
target_link_libraries(test_utils agenkit gtest)

# Test binaries
add_executable(test_message test_message.cpp)
target_link_libraries(test_message agenkit test_utils gtest_main)
add_test(NAME message_tests COMMAND test_message)

add_executable(test_agent test_agent.cpp)
target_link_libraries(test_agent agenkit test_utils gtest_main)
add_test(NAME agent_tests COMMAND test_agent)

add_executable(test_http_transport test_http_transport.cpp)
target_link_libraries(test_http_transport agenkit test_utils gtest_main)
add_test(NAME http_transport_tests COMMAND test_http_transport)

# More tests...
```

**Test Structure**:
```cpp
// tests/test_message.cpp
#include <gtest/gtest.h>
#include <agenkit/core/message.hpp>

using namespace agenkit::core;

TEST(MessageTest, CreateTextMessage) {
    auto msg = Message::with_text("user", "Hello");

    EXPECT_EQ(msg.role(), "user");
    EXPECT_EQ(msg.content().as_text(), "Hello");
}

TEST(MessageTest, JsonSerialization) {
    auto msg = Message::with_text("user", "Test");
    auto json = msg.to_json();
    auto deserialized = Message::from_json(json);

    EXPECT_EQ(deserialized.role(), msg.role());
    EXPECT_EQ(deserialized.content().as_text(), msg.content().as_text());
}

// More tests...
```

**Test Coverage**:
- Message creation and serialization (5 tests)
- Agent interface and echo agent (5 tests)
- HTTP transport client (5 tests)
- HTTP server (5 tests)
- Error handling (5 tests)
- **Total: 25 tests**

---

## Examples

### Example 1: Echo Agent

**File**: `examples/echo_agent.cpp`

```cpp
#include <agenkit/adapters/echo_agent.hpp>
#include <agenkit/core/message.hpp>
#include <iostream>

using namespace agenkit;

int main() {
    // Create echo agent
    adapters::EchoAgent agent;

    // Create message
    auto message = core::Message::with_text("user", "Hello, agent!");

    // Process message
    auto future = agent.process(std::move(message));
    auto result = future.get();

    if (result.is_ok()) {
        auto response = result.unwrap();
        std::cout << "Response: " << response.content().as_text() << std::endl;
    } else {
        auto error = result.unwrap_err();
        std::cerr << "Error: " << error.what() << std::endl;
    }

    return 0;
}
```

### Example 2: HTTP Transport

**File**: `examples/http_transport.cpp`

```cpp
#include <agenkit/adapters/echo_agent.hpp>
#include <agenkit/transports/http_server.hpp>
#include <agenkit/transports/http_agent.hpp>
#include <agenkit/core/message.hpp>
#include <iostream>
#include <thread>

using namespace agenkit;

void run_server() {
    auto agent = std::make_shared<adapters::EchoAgent>();
    transports::HttpServer server(agent, "127.0.0.1:8080");

    std::cout << "Server listening on http://127.0.0.1:8080" << std::endl;
    server.serve(); // Blocking
}

void run_client() {
    // Wait for server to start
    std::this_thread::sleep_for(std::chrono::seconds(1));

    transports::HttpTransportConfig config{
        "http://127.0.0.1:8080",
        30,
        std::nullopt
    };

    transports::HttpAgent client("remote-agent", config);

    auto message = core::Message::with_text("user", "Hello from client!");
    auto future = client.process(std::move(message));
    auto result = future.get();

    if (result.is_ok()) {
        auto response = result.unwrap();
        std::cout << "Client received: " << response.content().as_text() << std::endl;
    }
}

int main() {
    // Run server in background thread
    std::thread server_thread(run_server);
    server_thread.detach();

    // Run client in main thread
    run_client();

    return 0;
}
```

---

## Dependencies

### Required Libraries

1. **nlohmann/json** (3.11.0+)
   - JSON serialization/deserialization
   - Header-only, modern C++ interface
   - Install: vcpkg, conan, or system package manager

2. **cpp-httplib** (0.14.0+)
   - HTTP client and server
   - Header-only, no external dependencies
   - Alternative: libcurl + microhttpd

3. **Google Test** (1.12.1+)
   - Unit testing framework
   - FetchContent in CMake (auto-download)

### Optional Dependencies

4. **spdlog** (optional)
   - Fast C++ logging library
   - For tracing/debugging

5. **Boost.Beast** (alternative to cpp-httplib)
   - Part of Boost, more features
   - More complex, not header-only

### Dependency Management

**Option 1: vcpkg** (Recommended)
```bash
# Install vcpkg
git clone https://github.com/microsoft/vcpkg.git
./vcpkg/bootstrap-vcpkg.sh

# Install dependencies
./vcpkg/vcpkg install nlohmann-json cpp-httplib
```

**Option 2: Conan**
```bash
# conanfile.txt
[requires]
nlohmann_json/3.11.3
cpp-httplib/0.14.0

[generators]
cmake_find_package
```

**Option 3: System Package Manager**
```bash
# Ubuntu/Debian
sudo apt install nlohmann-json3-dev

# macOS
brew install nlohmann-json
```

---

## CI/CD Pipeline

**File**: `.github/workflows/cpp-ci.yml`

```yaml
name: C++ CI

on:
  push:
    branches: [ main ]
    paths:
      - 'agenkit-cpp/**'
  pull_request:
    branches: [ main ]
    paths:
      - 'agenkit-cpp/**'

jobs:
  build-and-test:
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        build_type: [Debug, Release]

    runs-on: ${{ matrix.os }}

    steps:
    - uses: actions/checkout@v3

    - name: Install dependencies (Ubuntu)
      if: matrix.os == 'ubuntu-latest'
      run: |
        sudo apt-get update
        sudo apt-get install -y cmake ninja-build nlohmann-json3-dev

    - name: Install dependencies (macOS)
      if: matrix.os == 'macos-latest'
      run: |
        brew install cmake ninja nlohmann-json

    - name: Install dependencies (Windows)
      if: matrix.os == 'windows-latest'
      uses: lukka/run-vcpkg@v11
      with:
        vcpkgGitCommitId: 'latest'

    - name: Configure CMake
      run: |
        cmake -B build -G Ninja \
          -DCMAKE_BUILD_TYPE=${{ matrix.build_type }} \
          -DAGENKIT_BUILD_EXAMPLES=ON \
          -DAGENKIT_BUILD_TESTS=ON

    - name: Build
      run: cmake --build build --parallel

    - name: Test
      run: ctest --test-dir build --output-on-failure

    - name: Install
      run: cmake --install build --prefix install
```

---

## Implementation Timeline

### Week 1: Core Infrastructure
- [x] Project setup (CMake, directory structure)
- [ ] Message types and JSON serialization
- [ ] Agent interface and error types
- [ ] Echo agent implementation
- [ ] Basic tests (10 tests)

### Week 2: HTTP Transport
- [ ] HTTP client implementation
- [ ] HTTP server implementation
- [ ] Transport tests (10 tests)
- [ ] HTTP example

### Week 3: Documentation & Polish
- [ ] README.md with examples
- [ ] BUILD.md with build instructions
- [ ] API documentation (Doxygen comments)
- [ ] CI/CD pipeline setup
- [ ] Additional tests (5 tests)

### Week 4: Integration & Verification
- [ ] Integration testing
- [ ] Performance benchmarking
- [ ] Cross-platform testing (Linux, macOS, Windows)
- [ ] Documentation review
- [ ] Final polish

---

## Acceptance Criteria

### Code Quality
- [ ] All 25 tests passing
- [ ] No compiler warnings (-Wall -Wextra)
- [ ] No memory leaks (valgrind clean)
- [ ] Static analysis clean (cppcheck, clang-tidy)
- [ ] Code coverage >85%

### Examples
- [ ] echo_agent compiles and runs
- [ ] http_transport compiles and runs
- [ ] Examples included in CMake build

### Documentation
- [ ] README.md complete
- [ ] BUILD.md with build instructions
- [ ] API documentation (Doxygen)
- [ ] Examples documented

### CI/CD
- [ ] GitHub Actions workflow passing
- [ ] Multi-platform builds (Linux, macOS, Windows)
- [ ] Automated tests in CI

### Integration
- [ ] Can create simple agents
- [ ] Can communicate via HTTP
- [ ] JSON serialization works
- [ ] Error handling works

---

## Next Steps (v0.30.0)

After infrastructure is complete, implement patterns:
1. Reflection Pattern
2. Agents-as-Tools Pattern
3. Orchestration Patterns (Sequential, Parallel)
4. ReAct Pattern
5. Planning Pattern
6. Conversational Pattern
7. Task Pattern
8. Multiagent Pattern
9. Autonomous Pattern
10. Memory Hierarchy Pattern
11. Reasoning with Tools Pattern

---

## References

### Language References
- **Python**: `agenkit/core/agent.py`
- **Go**: `agenkit-go/core/agent.go`
- **TypeScript**: `agenkit-ts/src/core/agent.ts`
- **Rust**: `agenkit-rust/src/core/agent.rs`

### C++ Best Practices
- C++ Core Guidelines: https://isocpp.github.io/CppCoreGuidelines/
- Modern C++ Design Patterns
- RAII for resource management
- Move semantics for performance
- Smart pointers for memory safety

### Libraries
- nlohmann/json: https://github.com/nlohmann/json
- cpp-httplib: https://github.com/yhirose/cpp-httplib
- Google Test: https://github.com/google/googletest
- CMake: https://cmake.org/cmake/help/latest/

---

**Last Updated**: November 26, 2025
**Status**: Planning Complete - Ready for Implementation
**Next Action**: Create Issue #143 subtasks and begin Week 1 implementation
