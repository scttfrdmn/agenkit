# Agenkit C++

Minimal, composable interfaces for AI agents in C++.

**Status**: ✅ Production Ready (v0.30.0 - 11 Patterns + Benchmarks)

---

## Features

- **Simple**: Minimal Agent interface with only 2 required methods
- **Composable**: Easy to wrap and extend agents
- **Type-safe**: Modern C++17 with smart pointers and move semantics
- **Fast**: 50-100x faster than Python (benchmarked)
- **Production-ready**: HTTP transport, error handling, comprehensive tests
- **Cross-platform**: Ubuntu, macOS, Windows with full CI/CD

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
./examples/agent_chain

# Run benchmarks
./benchmarks/bench_core
./benchmarks/bench_http
./benchmarks/bench_patterns  # All 11 patterns
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

# Claude with Reflection pattern (requires ANTHROPIC_API_KEY)
export ANTHROPIC_API_KEY=your-key-here
./build/examples/claude_reflection
```

### Claude Reflection Example

Real-world usage of the Reflection pattern with Anthropic's Claude API:

```cpp
// Configure Claude Sonnet 4
adapters::ClaudeConfig config;
config.api_key = std::getenv("ANTHROPIC_API_KEY");
config.model = adapters::ClaudeModels::SONNET_4;

// Create agents
auto agent = std::make_shared<adapters::ClaudeAgent>(config);
auto reflector = std::make_shared<adapters::ClaudeAgent>(config);

// Reflection pattern (max 3 iterations)
patterns::ReflectionAgent reflection(agent, reflector, 3);

// Process with iterative refinement
auto msg = core::Message::with_text("user", "Write a haiku about AI");
auto result = reflection.process(std::move(msg)).get();
```

See `examples/claude_reflection.cpp` for the complete example.

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
4. **Patterns** (`include/agenkit/patterns/`): 11 agent patterns (Reflection, ReAct, etc.)

---

## Current Status

**v0.30.0 - Pattern Parity ✅**

**All 11 Patterns Implemented**:
- [x] Core Patterns: Reflection, ReAct, Agents-as-Tools, Orchestration, Reasoning with Tools
- [x] Advanced Patterns: Conversational, Task, Multiagent, Planning, Autonomous
- [x] Memory Patterns: Working Memory, Memory Hierarchy
- [x] 100% test coverage (17/17 test suites passing)
- [x] Comprehensive benchmarks for all patterns

**Infrastructure Complete**:
- [x] Core Agent interface
- [x] Message protocol with JSON
- [x] Result<T,E> error handling
- [x] HTTP transport (client/server)
- [x] Pattern implementations
- [x] 3 working examples

**Performance**:
- Framework overhead: **<100μs** for most patterns (negligible vs LLM latency)
- Agent processing: **50-100x faster than Python**
- HTTP latency: **2-3ms** (target: <5ms)
- Memory: Sub-microsecond for memory patterns
- See [docs/BENCHMARKS.md](docs/BENCHMARKS.md) for detailed results

**Platforms**:
- ✅ Ubuntu (latest) - GCC, Clang
- ✅ macOS (latest) - AppleClang
- ✅ Windows (latest) - MSVC 2022

**Stats**:
- **Lines of Code**: ~5,000 LOC (patterns + core)
- **Tests**: 17 suites, 100+ test cases (100% pass)
- **Benchmarks**: 14 comprehensive benchmarks
- **Patterns**: 11/11 (100% parity with Python)
- **CI Configurations**: 6 (3 platforms × 2 builds)

**Next**: Performance optimization, documentation improvements

---

## Documentation

- **Build Instructions**: [docs/BUILD.md](docs/BUILD.md)
- **Benchmark Results**: [docs/BENCHMARKS.md](docs/BENCHMARKS.md)
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
