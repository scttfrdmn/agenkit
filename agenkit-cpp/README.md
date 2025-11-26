# Agenkit C++

Minimal, composable interfaces for AI agents in C++.

**Status**: 🚧 Infrastructure (v0.29.0 - In Progress)

---

## Features

- **Simple**: Minimal Agent interface with only 2 required methods
- **Composable**: Easy to wrap and extend agents
- **Type-safe**: Modern C++17 with smart pointers and move semantics
- **Performance**: Native speed for compute-intensive agents
- **Production-ready**: HTTP transport, error handling, and logging
- **GPU Support**: CUDA/GPU integration for ML inference (v0.30.0+)

---

## Quick Start

### Prerequisites

- C++17 compatible compiler (GCC 7+, Clang 5+, MSVC 2017+)
- CMake 3.16+
- Dependencies:
  - nlohmann/json (3.11.0+)
  - cpp-httplib (0.14.0+) or libcurl
  - Google Test (1.12.1+) for testing

### Installation

```bash
# Clone the repository
git clone https://github.com/scttfrdmn/agenkit.git
cd agenkit/agenkit-cpp

# Install dependencies (vcpkg)
vcpkg install nlohmann-json cpp-httplib

# Build
mkdir build && cd build
cmake ..
cmake --build .

# Run tests
ctest

# Run examples
./examples/echo_agent
./examples/http_transport
```

---

## Core Concepts

### Message

Universal message format for agent communication:

```cpp
#include <agenkit/core/message.hpp>

using namespace agenkit::core;

// Create text message
auto msg = Message::with_text("user", "Hello, agent!");

// Add metadata
msg.with_metadata("session_id", "abc123");
```

### Agent

Core interface that all agents must implement:

```cpp
#include <agenkit/core/agent.hpp>
#include <agenkit/core/message.hpp>

using namespace agenkit::core;

class EchoAgent : public Agent {
public:
    std::string name() const override {
        return "echo";
    }

    std::future<Result<Message, AgentError>>
    process(Message message) override {
        auto response = Message::with_text(
            "assistant",
            message.content().as_text()
        );
        return make_ready_future(Result<Message, AgentError>::ok(response));
    }
};
```

### HTTP Transport

Expose agents over HTTP or connect to remote agents:

```cpp
#include <agenkit/transports/http_server.hpp>
#include <agenkit/transports/http_agent.hpp>

using namespace agenkit::transports;

// Server
auto agent = std::make_shared<EchoAgent>();
HttpServer server(agent, "127.0.0.1:8080");
server.serve();

// Client
HttpTransportConfig config{
    "http://localhost:8080",
    30,  // timeout_secs
    std::nullopt  // api_key
};
HttpAgent client("remote", config);
auto result = client.process(message).get();
```

---

## Examples

Run the included examples:

```bash
# Simple echo agent
./examples/echo_agent

# Client/server communication
./examples/http_transport
```

---

## Testing

Run all tests:

```bash
cd build
ctest --output-on-failure
```

Run specific test:

```bash
./tests/test_message
./tests/test_agent
./tests/test_http_transport
```

---

## Architecture

Agenkit C++ follows a layered architecture:

1. **Core** (`include/agenkit/core/`): Message types and Agent interface
2. **Adapters** (`include/agenkit/adapters/`): Local agent implementations
3. **Transports** (`include/agenkit/transports/`): HTTP, WebSocket, gRPC
4. **Patterns** (`include/agenkit/patterns/`): Coming in v0.30.0

---

## Current Status

**v0.29.0 - Infrastructure (In Progress)**

**Infrastructure (~600 LOC, 25 tests)**
- [ ] Core Agent interface (virtual base class)
- [ ] Message and ToolResult types
- [ ] HTTP transport (client and server)
- [ ] Error handling
- [ ] Echo agent example
- [ ] HTTP transport example
- [ ] Unit tests with Google Test

**Target**: December 2025

**Next**: v0.30.0 - Pattern Implementation (11 patterns)

---

## Documentation

- **Build Instructions**: [docs/BUILD.md](docs/BUILD.md)
- **Infrastructure Plan**: [../docs/cpp_infrastructure_plan.md](../docs/cpp_infrastructure_plan.md)
- **API Reference**: Coming soon (Doxygen)

---

## Performance

C++ implementation goals:
- **25x faster** than Python (native performance)
- **Low memory footprint**: ~6 MB per agent
- **CUDA/GPU support**: ML inference acceleration
- **SIMD optimizations**: Vector operations
- **Zero-copy** where possible

---

## License

MIT

---

## Contributing

Contributions welcome! See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

---

## Links

- **Repository**: https://github.com/scttfrdmn/agenkit
- **Documentation**: https://docs.agenkit.dev
- **Issue Tracker**: https://github.com/scttfrdmn/agenkit/issues/143
