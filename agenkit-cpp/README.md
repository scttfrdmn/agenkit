# Agenkit C++

Minimal, composable interfaces for AI agents in C++.

**Status**: ✅ Production Ready (v0.49.0 - 11 Patterns + Observability ⭐)

---

## Features

- **Simple**: Minimal Agent interface with only 2 required methods
- **Composable**: Easy to wrap and extend agents
- **Type-safe**: Modern C++17 with smart pointers and move semantics
- **Fast**: 50-100x faster than Python (benchmarked)
- **Production-ready**: HTTP transport, error handling, comprehensive tests
- **Observability**: OpenTelemetry tracing, metrics, logging, audit ⭐ NEW
- **Cross-platform**: Ubuntu, macOS, Windows with full CI/CD
- **LLM Support**: Claude, Ollama (local/free) ⭐, OpenAI (coming soon)
- **Real Examples**: ReAct with tools, Reflection, and more

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

### LLM Adapters

Connect to various LLM providers or OpenAI-compatible services:

**OpenAI-Compatible Services** (vLLM, llama.cpp, SGLang, etc.):

```cpp
#include <agenkit/adapters/openai_compatible_agent.hpp>

using namespace agenkit::adapters;

// vLLM local deployment
auto config = OpenAICompatibleProviders::vllm("meta-llama/Llama-2-7b-chat-hf");
OpenAICompatibleAgent agent(config);

// llama.cpp server
auto config = OpenAICompatibleProviders::llamacpp("llama-2-7b-chat");
OpenAICompatibleAgent agent(config);

auto msg = Message::with_text("user", "What is machine learning?");
auto result = agent.process(std::move(msg)).get();
```

Supports: vLLM, llama.cpp, SGLang, TensorRT-LLM, OpenLLM, MLC LLM, TGI, Inferflow

**Other LLM Providers**:
- `ClaudeAgent` - Claude 3.5 Sonnet, Claude 3 Opus
- `OpenAIAgent` - GPT-4, GPT-4 Turbo, GPT-3.5 Turbo
- `OllamaAgent` - Local Ollama models
- `LiteLLMAgent` - Unified interface to 100+ models
- `GeminiAgent` - Google Gemini models
- `BedrockAgent` - AWS Bedrock models

---

## Examples

### LLM Examples (Real-World)

```bash
# Ollama (Local LLM - Free!) ⭐ Recommended for getting started
ollama serve                        # Start Ollama (separate terminal)
ollama pull llama3.3               # Pull a model
./build/examples/ollama_example    # Basic Q&A
./build/examples/react_tools_example  # ReAct with tools

# Claude (Requires API key)
export ANTHROPIC_API_KEY=your-key
./build/examples/claude_reflection
```

### Basic Examples

```bash
# Simple echo agent
./examples/echo_agent

# Client/server communication
./examples/http_transport
```

### Ollama + ReAct Example ⭐

Real-world ReAct pattern with tool use (FREE - no API key needed!):

```cpp
// Configure Ollama (local, free, fast)
adapters::OllamaConfig config;
config.host = "http://localhost:11434";
config.model = "llama3.3";

auto agent = std::make_shared<adapters::OllamaAgent>(config);

// Create ReAct agent with tools
patterns::ReactAgent react(agent, 5);
react.add_tool(std::make_shared<CalculatorTool>());
react.add_tool(std::make_shared<WeatherTool>());
react.add_tool(std::make_shared<SearchTool>());

// Agent reasons, selects tools, and solves problems
auto msg = Message::with_text("user",
    "What's 15% tip on $47.50? Also, what's the weather in Paris?");
auto result = react.process(std::move(msg)).get();
```

**Benefits**:
- ✅ Free (no API costs)
- ✅ Fast (local inference)
- ✅ Private (data stays local)
- ✅ 3 simulated tools: Calculator, Weather, Search

See `examples/react_tools_example.cpp` for complete code.

### Claude Reflection Example

Real-world Reflection pattern with Anthropic's Claude:

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

## Migration Guides

### Migrating to C++

Choose your source language for detailed migration guide:

| From | Guide | Key Benefits |
|------|-------|-------------|
| **Python** | [MIGRATION.md](../docs/MIGRATION.md#python--c) | 20-100x faster, native performance, direct hardware access |
| **Go** | [MIGRATE_GO_TO_CPP.md](../docs/MIGRATE_GO_TO_CPP.md) | Fine-grained control, performance tuning, legacy integration |
| **TypeScript** | [MIGRATE_TYPESCRIPT_TO_CPP.md](../docs/MIGRATE_TYPESCRIPT_TO_CPP.md) | Native performance, 10-20x faster, systems programming |
| **Rust** | [MIGRATE_RUST_TO_CPP.md](../docs/MIGRATE_RUST_TO_CPP.md) | Legacy integration, C ABI, existing C++ codebases |
| **Zig** | [MIGRATE_ZIG_TO_CPP.md](../docs/MIGRATE_ZIG_TO_CPP.md) | Larger ecosystem, mature tooling, RAII patterns |

### Migrating from C++

| To | Guide | Primary Use Case |
|----|-------|-----------------|
| **Python** | [MIGRATE_CPP_TO_PYTHON.md](../docs/MIGRATE_CPP_TO_PYTHON.md) | Easier maintenance, prototyping, ML integration |
| **Go** | [MIGRATE_CPP_TO_GO.md](../docs/MIGRATE_CPP_TO_GO.md) | Simpler memory, better concurrency, faster compilation |
| **TypeScript** | [MIGRATE_CPP_TO_TYPESCRIPT.md](../docs/MIGRATE_CPP_TO_TYPESCRIPT.md) | Web deployment, cross-platform, universal code |
| **Rust** | [MIGRATE_CPP_TO_RUST.md](../docs/MIGRATE_CPP_TO_RUST.md) | Memory safety, modern async, prevents data races |
| **Zig** | [MIGRATE_CPP_TO_ZIG.md](../docs/MIGRATE_CPP_TO_ZIG.md) | Simpler language, explicit control, faster compilation |

**See also:**
- [Language Profile: C++](../docs/LANGUAGE_PROFILE_CPP.md) - Deep dive into C++ idioms and patterns
- [Migration Index](../docs/MIGRATION_INDEX.md) - Complete migration documentation hub

---

## Architecture

Agenkit C++ follows a layered architecture:

1. **Core** (`include/agenkit/core/`): Message types and Agent interface
2. **Adapters** (`include/agenkit/adapters/`): Local agent implementations
3. **Transports** (`include/agenkit/transports/`): HTTP, WebSocket, gRPC
4. **Patterns** (`include/agenkit/patterns/`): 11 agent patterns (Reflection, ReAct, etc.)
5. **Observability** (`include/agenkit/observability/`): OpenTelemetry-based monitoring ⭐ NEW

---

## Observability ⭐ NEW

Production-ready OpenTelemetry integration for distributed tracing, metrics, logging, and audit:

### Quick Setup

```bash
# Install OpenTelemetry C++ SDK
vcpkg install opentelemetry-cpp

# Build with observability enabled
cmake -DAGENKIT_WITH_OBSERVABILITY=ON \
      -DCMAKE_TOOLCHAIN_FILE=[vcpkg]/scripts/buildsystems/vcpkg.cmake ..
make
```

### Basic Usage

```cpp
#include "agenkit/observability/tracing.hpp"
#include "agenkit/observability/metrics.hpp"
#include "agenkit/observability/logging.hpp"
#include "agenkit/observability/audit.hpp"

using namespace agenkit::observability;

// Initialize observability
init_tracing("console", "");
init_metrics("console", "");
configure_logging("json", "info");
auto audit = AuditLogger::create("audit.log");

// Wrap agent with observability middleware
auto agent = std::make_shared<EchoAgent>();
auto traced = std::make_shared<TracingMiddleware>(agent, "echo.process");
auto observed = std::make_shared<MetricsMiddleware>(traced);

// Process message (automatically traced and metered)
auto result = observed->process(msg).get();

// Audit the operation
audit->log(
    AuditEvent::create(AuditEventType::MessageProcessed, "echo", "session_1")
        .with_detail("success", true)
);
```

### Features

- **Distributed Tracing**: W3C Trace Context propagation across agents
- **Metrics Collection**: Request counts, durations, errors (Prometheus/OTLP)
- **Structured Logging**: JSON/Compact/Pretty formats with trace correlation
- **Audit Logging**: Compliance-ready event persistence with queries
- **Multiple Exporters**: OTLP, Jaeger, Zipkin, Prometheus, Console
- **RAII-based**: Automatic resource cleanup with `ScopedSpan`
- **Thread-safe**: Production-ready concurrency support
- **Zero overhead when disabled**: Optional compilation flag

### Examples

```bash
# Basic observability setup
./build/examples/observability_basic

# Distributed tracing across agents
./build/examples/observability_distributed

# Production configuration with OTLP
export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4317"
./build/examples/observability_production
```

### Documentation

- **Complete Guide**: [docs/OBSERVABILITY.md](docs/OBSERVABILITY.md)
- **API Reference**: Full API documentation with examples
- **Production Deployment**: Kubernetes, Docker Compose, alerting
- **63 Tests**: Comprehensive test coverage (tracing: 12, metrics: 12, logging: 14, audit: 17, integration: 8)

---

## Current Status

**v0.49.0 - Production Observability ⭐**

**All 11 Patterns Implemented**:
- [x] Core Patterns: Reflection, ReAct, Agents-as-Tools, Orchestration, Reasoning with Tools
- [x] Advanced Patterns: Conversational, Task, Multiagent, Planning, Autonomous
- [x] Memory Patterns: Working Memory, Memory Hierarchy
- [x] 100% test coverage (17/17 test suites passing)
- [x] Comprehensive benchmarks for all patterns

**Observability Complete** ⭐ NEW:
- [x] Distributed Tracing (OpenTelemetry)
- [x] Metrics Collection (Prometheus/OTLP)
- [x] Structured Logging (JSON/Compact/Pretty)
- [x] Audit Logging (Compliance-ready)
- [x] 63 tests (12 tracing + 12 metrics + 14 logging + 17 audit + 8 integration)
- [x] 3 production-ready examples
- [x] Complete documentation

**Infrastructure Complete**:
- [x] Core Agent interface
- [x] Message protocol with JSON
- [x] Result<T,E> error handling
- [x] HTTP transport (client/server)
- [x] Pattern implementations
- [x] Observability stack (tracing, metrics, logging, audit)

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
- **Lines of Code**: ~7,500 LOC (patterns + core + observability)
- **Tests**: 22 suites, 150+ test cases (100% pass)
- **Benchmarks**: 14 comprehensive benchmarks
- **Patterns**: 11/11 (100% parity with Python)
- **Observability**: 4 modules, 63 tests (exceeds Python/Go parity by 54%)
- **CI Configurations**: 6 (3 platforms × 2 builds)

**Next**: Advanced patterns, performance optimization

---

## Documentation

- **Build Instructions**: [docs/BUILD.md](docs/BUILD.md)
- **Benchmark Results**: [docs/BENCHMARKS.md](docs/BENCHMARKS.md)
- **Observability Guide**: [docs/OBSERVABILITY.md](docs/OBSERVABILITY.md)
- **API Reference**: [docs/API.md](docs/API.md)
- **Getting Started**: [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)
- **Patterns Guide**: [docs/PATTERNS.md](docs/PATTERNS.md)
- **Migration Guide**: [docs/MIGRATION.md](docs/MIGRATION.md)
- **Testing Framework**: [docs/TESTING_FRAMEWORK.md](docs/TESTING_FRAMEWORK.md)

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
