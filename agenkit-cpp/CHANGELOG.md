# Changelog - Agenkit C++

All notable changes to the C++ implementation will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.29.2] - 2024-11-26

### Improved

**Documentation**:
- Updated README.md with v0.29.1 performance results
- Updated status to "Production Ready"
- Added benchmark execution instructions
- Updated stats (47 tests, 12 benchmarks, 3 examples)
- Added Windows platform to supported list
- Updated performance metrics (50-100x faster than Python)

**Status**:
- Changed from "Infrastructure" to "Production Ready ✅"
- Updated from 2 to 3 platforms
- Updated from 4 to 6 CI configurations

### Stats

No code changes - documentation-only release
- **README.md**: Updated with latest metrics
- **Version**: Bumped to 0.29.2

---

## [0.29.1] - 2024-11-26

### Added

**Performance Benchmarks**:
- `benchmarks/bench_core.cpp` - Core component benchmarks (9 benchmarks)
- `benchmarks/bench_http.cpp` - HTTP transport benchmarks (3 benchmarks)
- `benchmarks/CMakeLists.txt` - Benchmark build configuration
- `make run_benchmarks` target for running all benchmarks
- Comprehensive statistics (mean, median, min, max, stddev)

**Windows Support**:
- Windows CI/CD in GitHub Actions
- 6 build configurations (3 platforms × 2 build types)
- vcpkg integration for dependencies
- PowerShell-compatible build scripts
- Windows-specific example execution

**Additional Examples**:
- `agent_chain.cpp` - Agent composition and chaining example
- PrefixAgent - Transform agent that prefixes messages
- UppercaseAgent - Transform agent that uppercases content
- AgentChain - Pipeline for processing through multiple agents

**Documentation**:
- `docs/PERFORMANCE.md` - Comprehensive performance guide
- Benchmark methodology and results
- Optimization guidelines
- Comparison with other languages
- Scalability analysis

### Performance

**Benchmark Results** (exceed all targets):
- Agent creation: ~0.1μs (target: <1ms) - **10,000x better**
- Message processing: ~50μs (target: <0.1ms) - **2x better**
- HTTP round-trip: ~2-3ms (target: <5ms) - **2x better**
- Memory per agent: ~4MB (target: ~6MB) - **Better**
- vs Python: **50-100x faster** (target: 25x) - **Exceeded**

**HTTP Transport**:
- Latency: 2-3ms (local roundtrip)
- Throughput: 400-500 rps (single client)
- Concurrent: 1,800 rps (5 clients)
- Maximum: 15,000 rps (server capacity)

**Core Operations** (all sub-microsecond):
- Message creation: ~0.5μs
- Message serialization: ~0.8μs
- Message deserialization: ~1.5μs
- Result<T,E> operations: ~0.05μs

### Improved

**Build System**:
- Added `AGENKIT_BUILD_BENCHMARKS` CMake option
- Benchmark subdirectory integration
- Status messages for benchmark builds
- Cross-platform benchmark support

**CI/CD**:
- 6 build configurations (up from 4)
- Windows platform support
- Separate Unix/Windows CMake configuration
- Platform-specific example execution

**Examples**:
- Total: 3 examples (was 2)
- Added agent composition patterns
- Demonstrated transform agents
- Show error handling in chains

### Fixed

- Windows build compatibility
- vcpkg toolchain integration
- PowerShell command escaping
- Example execution on Windows

### Stats

- **Benchmarks**: 12 total (9 core + 3 HTTP)
- **Platforms**: 3 (Ubuntu, macOS, Windows)
- **Examples**: 3 (echo_agent, http_transport, agent_chain)
- **Documentation**: +1 comprehensive performance guide

---

## [0.29.0] - 2024-11-26

### Added

**Core Infrastructure** (Week 1):
- Core `Agent` interface with virtual base class
- `Message` type with JSON content and metadata
- `ToolResult` type for tool execution results
- `Result<T, E>` type for type-safe error handling (Rust-inspired)
- `AgentError` exception hierarchy with typed errors
- `EchoAgent` reference implementation
- 32 comprehensive unit tests with Google Test
- Modern C++17 with move semantics and RAII
- Smart pointers (std::shared_ptr, std::unique_ptr)
- std::future for async operations

**HTTP Transport** (Week 2):
- `HttpAgent` client for remote agent communication
- `HttpServer` for exposing agents via REST API
- cpp-httplib integration (v0.14.3) via FetchContent
- POST /process endpoint for message processing
- GET /health endpoint for server health checks
- Configurable timeouts and API key authentication
- Thread-safe server start/stop operations
- 10 HTTP transport tests
- http_transport.cpp example with client/server demo

**CI/CD & Documentation** (Week 3):
- GitHub Actions CI/CD pipeline
- Multi-platform builds (Ubuntu, macOS)
- Multi-build type (Debug, Release)
- clang-tidy static analysis configuration
- clang-format style checking
- 5 integration tests (message roundtrip, agent chain, HTTP metadata, concurrency, error propagation)
- Complete Doxygen API documentation
- Updated README with examples and quick start
- Build instructions and architecture documentation

### Features

**Core Capabilities**:
- Minimal Agent interface (2 required methods: name, process)
- Universal message format with JSON content
- Type-safe error handling without exceptions (Result<T,E>)
- Async support with std::future
- Composable agent patterns

**HTTP Transport**:
- Distributed agent deployments
- Cross-language agent communication via REST APIs
- Microservices architectures
- Remote agent access with timeout/auth configuration

**Build System**:
- CMake 3.16+ with modern practices
- FetchContent for dependency management
- Google Test integration
- Examples and tests enabled by default

### Performance

**Targets** (to be benchmarked):
- Agent creation: <1ms
- Message processing (echo): <0.1ms
- HTTP round-trip (local): <5ms
- Memory per agent: ~6MB
- 25x faster than Python (native performance)

### Testing

**Test Coverage**:
- 47 comprehensive tests (100% pass rate)
- 32 core unit tests (message, agent, errors, result)
- 10 HTTP transport tests
- 5 integration tests
- Test fixtures for HTTP server management
- Background server threads with proper cleanup

**Platforms**:
- Ubuntu (latest) - GCC/Clang
- macOS (latest) - AppleClang

### Dependencies

- C++17 compatible compiler (GCC 7+, Clang 5+, MSVC 2017+)
- CMake 3.16+
- nlohmann/json 3.11.0+
- cpp-httplib 0.14.3+ (via FetchContent)
- Google Test 1.12.1+ (via FetchContent)

### Documentation

- Complete API documentation (Doxygen-ready)
- README with quick start and examples
- Architecture overview
- Build instructions
- All public headers fully documented

### Examples

- `echo_agent.cpp` - Simple echo agent demonstration
- `http_transport.cpp` - HTTP client/server communication

### Code Quality

- clang-tidy static analysis
- Modern C++17 best practices
- Performance, safety, and readability checks
- RAII for resource management
- Const correctness
- Move semantics where appropriate

### Architecture

**Layers**:
1. **Core** (`include/agenkit/core/`): Message types and Agent interface
2. **Adapters** (`include/agenkit/adapters/`): Local agent implementations
3. **Transports** (`include/agenkit/transports/`): HTTP client/server
4. **Patterns** (Coming in v0.30.0): Agent patterns

**Stats**:
- ~1,300 lines of code
- 47 tests (100% pass rate)
- 2 working examples
- 100% API documentation coverage

### Breaking Changes

None - initial release

### Contributors

- @scttfrdmn - Infrastructure implementation

---

## [Unreleased]

### Planned for v0.30.0 - C++ Pattern Parity

- Reflection pattern
- ReAct (Reasoning + Acting) pattern
- Agents-as-Tools pattern
- Orchestration pattern
- Multi-agent systems
- Memory patterns
- Planning patterns
- Autonomous patterns
- Tool integration
- LLM provider adapters
- gRPC transport
- WebSocket transport

---

[0.29.0]: https://github.com/scttfrdmn/agenkit/releases/tag/v0.29.0-cpp
