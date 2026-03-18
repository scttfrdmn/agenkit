# Agenkit for Zig

The foundation layer for AI agents in Zig.

## Overview

Agenkit-Zig is a systems-level implementation of the Agenkit framework, bringing robust AI agent primitives to the Zig programming language. It provides explicit memory management, zero-cost abstractions, and compile-time safety guarantees while maintaining API compatibility with other Agenkit implementations.

## Features

- **Explicit Memory Management**: All allocations use explicit `Allocator` parameters - no hidden memory allocations
- **Zero-Cost Abstractions**: Interface-based design using vtable pattern with no runtime overhead
- **Comprehensive Error Handling**: Error union types (`!`) for safe, explicit error propagation
- **Cross-Language Compatible**: API parity with Python, Go, TypeScript, C++, and Rust implementations
- **Built-in Testing**: Integrated test framework with memory leak detection and property-based tests
- **Production Observability**: OpenTelemetry tracing, metrics collection, structured logging, and audit logging

## Installation

### Requirements

- Zig 0.15.2 or later
- (Optional) wasmtime for running WASM builds: `brew install wasmtime`

### Using with Zig Package Manager

Add to your `build.zig.zon`:

```zig
.dependencies = .{
    .agenkit = .{
        .url = "https://github.com/agenkit/agenkit/releases/download/v0.41.0/agenkit-zig.tar.gz",
        .hash = "...",
    },
},
```

Then in your `build.zig`:

```zig
const agenkit = b.dependency("agenkit", .{
    .target = target,
    .optimize = optimize,
});

exe.root_module.addImport("agenkit", agenkit.module("agenkit"));
```

### Building from Source

```bash
git clone https://github.com/agenkit/agenkit.git
cd agenkit/agenkit-zig
zig build test
```

### WebAssembly (WASM) Build

Zig has native WASM support. Build for WASM using the `wasm32-wasi` target:

```bash
# Build for WASM
zig build -Dtarget=wasm32-wasi -Doptimize=ReleaseSmall

# Output files in zig-out/bin/*.wasm
ls zig-out/bin/*.wasm
```

All 18 agent patterns are available in WASM builds. The `wasm32-wasi` target includes WASI (WebAssembly System Interface) support for threading and system calls.

#### Running WASM Files

Install a WASI runtime like wasmtime:

```bash
# Install wasmtime (macOS)
brew install wasmtime

# Install wasmtime (Linux/other)
curl https://wasmtime.dev/install.sh -sSf | bash

# Run a WASM file
wasmtime zig-out/bin/echo_example.wasm

# Run pattern examples
wasmtime zig-out/bin/reflection_example.wasm
wasmtime zig-out/bin/sequential_example.wasm
wasmtime zig-out/bin/parallel_example.wasm
```

All 27 WASM files (18 pattern examples + 9 other examples) are executable with any WASI-compatible runtime.

## Quick Start

```zig
const std = @import("std");
const agenkit = @import("agenkit");

pub fn main() !void {
    // Setup allocator
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    // Create a message
    var msg = try agenkit.Message.withText(allocator, .user, "Hello, agent!");
    defer msg.deinit();

    // Create an agent
    var echo = try agenkit.EchoAgent.init(allocator);
    defer echo.agent().deinit();

    // Process the message
    const result = try echo.agent().process(msg);
    var response = try result.unwrap();
    defer response.deinit();

    // Get the response
    const text = try response.contentAsText();
    std.debug.print("Response: {s}\n", .{text});
}
```

## Core Concepts

### Message

Messages are the fundamental unit of communication in Agenkit. Each message has:

- **Role**: `user`, `assistant`, `system`, or `tool`
- **Content**: Text or structured JSON data
- **Metadata**: Key-value pairs for tracing, sessions, etc.

```zig
// Create a text message
var msg = try agenkit.Message.withText(allocator, .user, "Hello!");
defer msg.deinit();

// Add metadata
try msg.setMetadata("session_id", std.json.Value{ .string = "abc-123" });

// Access content
const text = try msg.contentAsText();
```

### Agent

Agents implement the `Agent` interface and process messages:

```zig
pub const Agent = struct {
    ptr: *anyopaque,
    vtable: *const VTable,

    pub fn name(self: Agent) []const u8;
    pub fn capabilities(self: Agent, allocator: Allocator) ![]const []const u8;
    pub fn process(self: Agent, message: Message) !Result;
    pub fn deinit(self: Agent) void;
};
```

### Result

Processing returns a `Result` union type for explicit error handling:

```zig
pub const Result = union(enum) {
    ok: Message,
    err: AgentError,

    pub fn isOk(self: Result) bool;
    pub fn isErr(self: Result) bool;
    pub fn unwrap(self: Result) !Message;
    pub fn unwrapErr(self: Result) AgentError;
};
```

## LLM Adapters

Agenkit-Zig provides adapters for connecting to various LLM providers and OpenAI-compatible services.

### OpenAI-Compatible Services

Use the `OpenAICompatibleLLM` adapter to connect to any OpenAI-compatible inference service (vLLM, llama.cpp, SGLang, TensorRT-LLM, etc.):

```zig
const std = @import("std");
const agenkit = @import("agenkit");

// vLLM example using provider helper
var llm_impl = try agenkit.adapter.OpenAICompatibleLLM.vllm(
    allocator,
    "meta-llama/Llama-3.3-8B-Instruct"
);
defer llm_impl.deinit();
const llm = llm_impl.asLLM();

// Or configure manually
var llm_impl = try agenkit.adapter.OpenAICompatibleLLM.init(
    allocator,
    "http://localhost:8000/v1",  // base_url
    "meta-llama/Llama-3.3-8B-Instruct",  // model
    null,  // api_key (optional for local services)
    "vllm"  // provider name
);
defer llm_impl.deinit();
const llm = llm_impl.asLLM();

// Use the LLM
const messages = [_]*agenkit.Message{ user_msg };
var options = agenkit.adapter.CallOptions.init(allocator);
defer options.deinit();
options.temperature = 0.7;

const response = try llm.complete(allocator, &messages, &options);
defer response.deinit();
```

**Supported Services:**
- **vLLM** - High-throughput batch inference (default port: 8000)
- **llama.cpp** - Lightweight C++ implementation, CPU-friendly (default port: 8080)
- **SGLang** - Optimized for complex prompts (default port: 30000)
- **TensorRT-LLM** - NVIDIA GPU optimized (default port: 8001)
- **OpenLLM** - Multi-model serving platform
- **MLC LLM** - Mobile and edge deployment
- **Text Generation Inference (TGI)** - HuggingFace inference server
- **Inferflow** - High-performance inference

**Provider Helpers:**
```zig
// vLLM (port 8000)
var llm = try agenkit.adapter.OpenAICompatibleLLM.vllm(allocator, "model-name");

// llama.cpp (port 8080)
var llm = try agenkit.adapter.OpenAICompatibleLLM.llamacpp(allocator, "model-name");

// SGLang (port 30000)
var llm = try agenkit.adapter.OpenAICompatibleLLM.sglang(allocator, "model-name");

// TensorRT-LLM (port 8001)
var llm = try agenkit.adapter.OpenAICompatibleLLM.tensorrt(allocator, "model-name");
```

### Other LLM Providers

- **OpenAILLM** - GPT-4, GPT-4 Turbo, GPT-3.5 Turbo
- **AnthropicLLM** - Claude 3.5 Sonnet, Claude 3 Opus
- **OllamaLLM** - Local Ollama models
- **GeminiLLM** - Google Gemini models
- **LiteLLMLLM** - Unified interface to 100+ models
- **BedrockLLM** - AWS Bedrock models

## Examples

Agenkit-Zig includes 11 comprehensive examples demonstrating various agent patterns and use cases.

### Basic Examples

Learn core concepts with 8 basic examples:

```bash
# Echo agent - simplest agent
zig build run-echo

# Error handling patterns
zig build run-error-handling

# Memory management best practices
zig build run-memory

# Testing patterns
zig build run-testing

# Sequential processing pipeline
zig build run-sequential

# Parallel concurrent processing
zig build run-parallel

# Reflection for self-improvement
zig build run-reflection

# Conversational multi-turn dialogue
zig build run-conversational
```

### Integration Examples

Real-world workflows combining multiple patterns:

```bash
# Multi-pattern workflow (Parallel + Sequential + Reflection + Planning)
zig build run-multi-pattern

# Long-running agent with memory (Conversational + Memory Hierarchy)
zig build run-long-running

# Performance evaluation pipeline (Metrics + Benchmarking)
zig build run-evaluation
```

### Observability Examples

Production-ready monitoring and tracing:

```bash
# OpenTelemetry distributed tracing with W3C Trace Context
zig build run-tracing-example

# Metrics collection (counters, histograms, labels)
zig build run-metrics-example

# Full observability stack (tracing + metrics + logging + audit)
zig build run-observability-example
```

See [docs/OBSERVABILITY.md](docs/OBSERVABILITY.md) for comprehensive observability documentation.

### Example: Echo Agent

The simplest agent - echoes messages back:

```zig
var echo = try agenkit.EchoAgent.init(allocator);
defer echo.agent().deinit();

const result = try echo.agent().process(msg);
if (result.isOk()) {
    var response = try result.unwrap();
    defer response.deinit();
    // Use response...
}
```

### Custom Agent

Implement your own agent using the vtable pattern:

```zig
pub const MyAgent = struct {
    allocator: Allocator,
    agent_name: []const u8,

    pub fn init(allocator: Allocator) !*MyAgent {
        const self = try allocator.create(MyAgent);
        self.* = MyAgent{
            .allocator = allocator,
            .agent_name = "my-agent",
        };
        return self;
    }

    pub fn agent(self: *MyAgent) Agent {
        return Agent{
            .ptr = self,
            .vtable = &.{
                .name = nameImpl,
                .capabilities = capabilitiesImpl,
                .process = processImpl,
                .deinit = deinitImpl,
            },
        };
    }

    fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
        const self: *MyAgent = @ptrCast(@alignCast(ptr));
        // Your implementation here...
        return Result{ .ok = response };
    }

    // Implement other vtable methods...
};
```

## Migration Guides

### Migrating to Zig

Choose your source language for detailed migration guide:

| From | Guide | Key Benefits |
|------|-------|-------------|
| **Python** | [MIGRATION.md](../docs/MIGRATION.md#python--zig) | 20-100x faster, no GC, explicit control, embedded systems |
| **Go** | [MIGRATE_GO_TO_ZIG.md](../docs/MIGRATE_GO_TO_ZIG.md) | No GC, explicit allocators, minimal runtime |
| **TypeScript** | [MIGRATE_TYPESCRIPT_TO_ZIG.md](../docs/MIGRATE_TYPESCRIPT_TO_ZIG.md) | No GC, 10-20x faster, explicit control |
| **Rust** | [MIGRATE_RUST_TO_ZIG.md](../docs/MIGRATE_RUST_TO_ZIG.md) | Simpler async model, explicit allocators, comptime |
| **C++** | [MIGRATE_CPP_TO_ZIG.md](../docs/MIGRATE_CPP_TO_ZIG.md) | Simpler language, explicit defer, faster compilation |

### Migrating from Zig

| To | Guide | Primary Use Case |
|----|-------|-----------------|
| **Python** | [MIGRATE_ZIG_TO_PYTHON.md](../docs/MIGRATE_ZIG_TO_PYTHON.md) | High-level APIs, ML integration, rapid prototyping |
| **Go** | [MIGRATE_ZIG_TO_GO.md](../docs/MIGRATE_ZIG_TO_GO.md) | Better concurrency, GC simplification, simpler deployment |
| **TypeScript** | [MIGRATE_ZIG_TO_TYPESCRIPT.md](../docs/MIGRATE_ZIG_TO_TYPESCRIPT.md) | Web deployment, universal code, GC simplification |
| **Rust** | [MIGRATE_ZIG_TO_RUST.md](../docs/MIGRATE_ZIG_TO_RUST.md) | Async ecosystem, ownership system, memory safety |
| **C++** | [MIGRATE_ZIG_TO_CPP.md](../docs/MIGRATE_ZIG_TO_CPP.md) | Larger ecosystem, mature tooling, legacy integration |

**See also:**
- [Language Profile: Zig](../docs/LANGUAGE_PROFILE_ZIG.md) - Deep dive into Zig idioms and patterns
- [Migration Index](../docs/MIGRATION_INDEX.md) - Complete migration documentation hub

## Memory Management

Zig requires explicit memory management. Follow these patterns:

### Allocator Threading

Pass allocators explicitly through your code:

```zig
pub fn createMessage(allocator: Allocator, text: []const u8) !Message {
    return Message.withText(allocator, .user, text);
}
```

### Cleanup Pattern

Always pair allocations with cleanup:

```zig
var msg = try Message.withText(allocator, .user, "text");
defer msg.deinit();  // Guaranteed cleanup

// Or with error handling:
var msg = try Message.withText(allocator, .user, "text");
errdefer msg.deinit();  // Only cleanup if error occurs
```

### Memory Leak Detection

Tests automatically detect leaks:

```bash
zig build test
# Will report: "leaked: [gpa] (err): memory address 0x... leaked"
```

## Testing

Agenkit includes comprehensive tests including property-based testing (v0.78.0+):

```bash
# Run all tests (unit + integration + property-based)
zig build test

# Run with verbose output
zig build test --summary all

# Run specific test
zig test src/message.zig
```

### Property-Based Tests

`tests/property/` contains 35 property-based tests using a custom framework built on `std.Random.DefaultPrng`. Each property runs 50 iterations with varied random inputs:

- `message_properties.zig` — 12 tests: Role/Content/Result invariants
- `middleware_properties.zig` — 13 tests: retry, circuit breaker, rate limiter behavior
- `agent_properties.zig` — 10 tests: EchoAgent, SequentialAgent, interface contracts

See [TESTING.md](TESTING.md) for details on the framework and how to add new properties.

Example test:

```zig
test "Message creation" {
    const allocator = std.testing.allocator;

    var msg = try Message.withText(allocator, .user, "Hello!");
    defer msg.deinit();

    try std.testing.expectEqual(Role.user, msg.role);
    const text = try msg.contentAsText();
    try std.testing.expectEqualStrings("Hello!", text);
}
```

## Design Philosophy

Agenkit-Zig follows Zig's core principles:

1. **Explicit is better than implicit** - No hidden allocations or control flow
2. **Error handling first** - All fallible operations return error unions
3. **Zero overhead abstractions** - Interface pattern compiles to direct function calls
4. **Memory safety** - Explicit allocator management prevents leaks

## API Reference

### Message

- `Message.withText(allocator, role, text)` - Create text message
- `Message.withStructured(allocator, role, data)` - Create structured message
- `msg.deinit()` - Free message resources
- `msg.setMetadata(key, value)` - Set metadata
- `msg.getMetadata(key)` - Get metadata
- `msg.contentAsText()` - Access text content
- `msg.toJson(allocator)` - Serialize to JSON
- `Message.fromJson(allocator, value)` - Deserialize from JSON

### Agent

- `agent.name()` - Get agent name
- `agent.capabilities(allocator)` - Get capabilities list
- `agent.process(message)` - Process a message
- `agent.deinit()` - Free agent resources

### Result

- `result.isOk()` - Check if successful
- `result.isErr()` - Check if error
- `result.unwrap()` - Get message (fails if error)
- `result.unwrapErr()` - Get error (unreachable if ok)

## Cross-Language Compatibility

Agenkit-Zig maintains API compatibility with:

- **Python** (agenkit) - Original reference implementation
- **Go** (agenkit-go) - High-performance concurrent agents
- **TypeScript** (@agenkit/core) - Browser and Node.js support
- **C++** (agenkit-cpp) - Systems programming
- **Rust** (agenkit-rs) - Memory-safe systems programming

All implementations share:
- Message structure (role, content, metadata)
- Agent interface (name, capabilities, process)
- Result types for error handling
- Composable patterns

## Contributing

Contributions welcome! Please:

1. Follow Zig style guide
2. Add tests for new features
3. Ensure `zig build test` passes with no leaks
4. Document public APIs
5. Maintain cross-language compatibility

## License

MIT License - See LICENSE file for details

## Links

- [Agenkit Documentation](https://github.com/agenkit/agenkit)
- [Zig Language](https://ziglang.org/)
- [Issue Tracker](https://github.com/agenkit/agenkit/issues)

## Agent Patterns

Agenkit-Zig provides 11 production-ready agent patterns:

### Composition Patterns
- **Sequential** - Process messages through agents in order
- **Parallel** - Concurrent processing with multiple agents

### Enhancement Patterns
- **Reflection** - Self-evaluation and improvement
- **React** - Reasoning before acting
- **Planning** - Multi-step task decomposition

### Specialized Patterns
- **Task** - Single-purpose job execution
- **Conversational** - Multi-turn dialogue with context
- **Agents as Tools** - Agents using other agents

### Advanced Patterns
- **Autonomous** - Self-directed goal pursuit
- **Multiagent** - Multi-agent coordination
- **Memory Hierarchy** - Efficient working/short/long-term memory

See [docs/PATTERNS.md](docs/PATTERNS.md) for detailed guide.

## Documentation

Comprehensive documentation is available in the `docs/` directory:

- **[Getting Started](docs/GETTING_STARTED.md)** - Installation, first agent, tutorials
- **[API Reference](docs/API.md)** - Complete API documentation
- **[Patterns Guide](docs/PATTERNS.md)** - Deep dive into 11 agent patterns
- **[Observability Guide](docs/OBSERVABILITY.md)** - Tracing, metrics, logging, and audit
- **[Migration Guide](docs/MIGRATION.md)** - Port from Python/Go/Rust/C++

## Version

Current version: **0.41.0**

Requires Zig: **≥ 0.15.2**

### What's New in v0.41.0

- ✨ **11 Comprehensive Examples** - 8 basic + 3 integration examples
- 📚 **Complete Documentation** - Getting Started, API, Patterns, Migration guides
- 🎯 **Real-World Use Cases** - Multi-pattern workflows, long-running agents, evaluation pipelines
- 🚀 **Production-Ready** - All 11 patterns fully implemented and tested
