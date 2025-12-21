# Zig API Reference

Complete API documentation for Agenkit Zig implementation.

## Official Documentation

The Zig implementation includes comprehensive manual API documentation in the repository. Zig's autodoc feature is experimental (v0.13.0), so detailed documentation is maintained in markdown format.

[📚 View Zig API Documentation](https://github.com/scttfrdmn/agenkit/blob/main/agenkit-zig/docs/API.md){ .md-button .md-button--primary }

**Additional Resources:**
- [Getting Started Guide](https://github.com/scttfrdmn/agenkit/blob/main/agenkit-zig/docs/GETTING_STARTED.md)
- [Patterns Guide](https://github.com/scttfrdmn/agenkit/blob/main/agenkit-zig/docs/PATTERNS.md)
- [Migration Guide](https://github.com/scttfrdmn/agenkit/blob/main/agenkit-zig/docs/MIGRATION.md)

---

## Quick Navigation

### Core Module

**`agenkit`** - Core types and interfaces

```zig
const agenkit = @import("agenkit");
const Agent = agenkit.Agent;
const Message = agenkit.Message;
const AgentError = agenkit.AgentError;
const Result = agenkit.Result;
```

Key types:
- `Agent` - Core agent interface (vtable-based)
- `Message` - Universal message format
- `Result` - Result union for success/error
- `AgentError` - Error set for agent operations
- `Role` - Message roles (user, assistant, system, tool)

### Patterns

**`agenkit.patterns`** - Agent patterns

```zig
const patterns = agenkit.patterns;
```

Available patterns:
- `SequentialAgent` - Sequential pipeline
- `ParallelAgent` - Concurrent execution
- `ReflectionAgent` - Self-critique loop
- `ReActAgent` - Reasoning + Acting
- `AgentsAsToolsAgent` - Hierarchical delegation
- `OrchestrationAgent` - Complex workflows
- `ReasoningWithToolsAgent` - Advanced tool usage
- `ConversationalAgent` - Multi-turn conversations
- `TaskAgent` - Task decomposition
- `PlanningAgent` - Goal-driven planning
- `AutonomousAgent` - Self-directed behavior
- `MultiagentAgent` - Multi-agent coordination
- `MemoryHierarchyAgent` - Memory management
- `RouterAgent` - Dynamic routing
- `SupervisorAgent` - Agent supervision
- `CollaborativeAgent` - Agent collaboration
- `HumanInLoopAgent` - Human oversight
- `FallbackAgent` - Graceful degradation

### Reasoning Techniques

**`agenkit.techniques.reasoning`** - Advanced reasoning

```zig
const reasoning = agenkit.techniques.reasoning;
```

Available techniques:
- `ChainOfThought` - Step-by-step reasoning
- `SelfConsistency` - Voting strategy

### LLM Adapters

**`agenkit.adapters`** - LLM provider adapters

```zig
const adapters = agenkit.adapters;
```

Available adapters:
- `OpenAIAdapter` - OpenAI API
- `AnthropicAdapter` - Claude API
- `GeminiAdapter` - Google Gemini
- `BedrockAdapter` - AWS Bedrock
- `OllamaAdapter` - Ollama (local models)
- `LiteLLMAdapter` - LiteLLM proxy

### Transport

**`agenkit.transports`** - HTTP/WebSocket

```zig
const transports = agenkit.transports;
```

Features:
- `HttpServer` - Serve agents over HTTP
- `HttpAgent` - Connect to remote agents

### Evaluation

**`agenkit.evaluation`** - Testing and optimization

```zig
const evaluation = agenkit.evaluation;
```

Features:
- `Recorder` - Session recording
- `QualityMetrics` - Quality evaluation
- `ContextMetrics` - Context analysis

---

## Getting Started with Zig

### Installation

```bash
# Install Zig (0.13.0+)
# macOS: brew install zig
# Linux: https://ziglang.org/download/
# Windows: https://ziglang.org/download/

# Clone repository
git clone https://github.com/scttfrdmn/agenkit.git
cd agenkit/agenkit-zig

# Build
zig build

# Run tests
zig build test

# Run example
zig build run-example-echo
```

### Basic Example

```zig
const std = @import("std");
const agenkit = @import("agenkit");

const Agent = agenkit.Agent;
const Message = agenkit.Message;
const AgentError = agenkit.AgentError;
const Result = agenkit.Result;

const EchoAgent = struct {
    allocator: std.mem.Allocator,
    agent_name: []const u8,

    pub fn init(allocator: std.mem.Allocator) !*EchoAgent {
        const self = try allocator.create(EchoAgent);
        self.* = .{
            .allocator = allocator,
            .agent_name = "echo-agent",
        };
        return self;
    }

    pub fn agent(self: *EchoAgent) Agent {
        return Agent{
            .ptr = self,
            .vtable = &.{
                .name = nameImpl,
                .capabilities = capabilitiesImpl,
                .process = processImpl,
                .introspect = introspectImpl,
                .deinit = deinitImpl,
            },
        };
    }

    fn nameImpl(ptr: *anyopaque) []const u8 {
        const self: *EchoAgent = @ptrCast(@alignCast(ptr));
        return self.agent_name;
    }

    fn capabilitiesImpl(_: *anyopaque, allocator: std.mem.Allocator) ![]const []const u8 {
        const caps = try allocator.alloc([]const u8, 2);
        caps[0] = "echo";
        caps[1] = "simple";
        return caps;
    }

    fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
        const self: *EchoAgent = @ptrCast(@alignCast(ptr));
        const content = try message.contentAsText();

        const response_text = try std.fmt.allocPrint(
            self.allocator,
            "Echo: {s}",
            .{content}
        );
        defer self.allocator.free(response_text);

        var response = try Message.withText(
            self.allocator,
            .assistant,
            response_text
        );

        return Result{ .ok = response };
    }

    fn introspectImpl(ptr: *anyopaque, allocator: std.mem.Allocator) !agenkit.IntrospectionResult {
        const self: *EchoAgent = @ptrCast(@alignCast(ptr));
        return agenkit.createDefaultIntrospectionResult(allocator, self.agent_name);
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *EchoAgent = @ptrCast(@alignCast(ptr));
        self.allocator.destroy(self);
    }
};

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    // Create agent
    const echo_agent = try EchoAgent.init(allocator);
    defer echo_agent.allocator.destroy(echo_agent);
    const agent_iface = echo_agent.agent();

    // Process message
    var message = try Message.withText(allocator, .user, "Hello!");
    defer message.deinit();

    const result = try agent_iface.process(message);
    switch (result) {
        .ok => |response| {
            defer response.deinit();
            const text = try response.contentAsText();
            std.debug.print("{s}\n", .{text}); // "Echo: Hello!"
        },
        .err => |err| {
            std.debug.print("Error: {}\n", .{err});
        },
    }
}
```

---

## Zig-Specific Features

### Explicit Memory Management

Zig requires explicit allocator management:

```zig
// Create allocator
var gpa = std.heap.GeneralPurposeAllocator(.{}){};
defer _ = gpa.deinit();
const allocator = gpa.allocator();

// Pass allocator to functions
var message = try Message.withText(allocator, .user, "Hello");
defer message.deinit(); // Always deinit!

// Allocator is tracked per-message
const text = try message.contentAsText();
// No need to free - owned by message
```

### Comptime

Zig leverages compile-time execution:

```zig
// Compile-time type checking
const AgentImpl = struct {
    // Comptime ensures correct vtable
    comptime {
        if (!@hasDecl(@This(), "agent")) {
            @compileError("AgentImpl must have 'agent' method");
        }
    }
};

// Comptime generics
fn Sequential(comptime T: type) type {
    return struct {
        agents: []T,
        // ...
    };
}
```

### Error Handling

Zig uses error unions for explicit error handling:

```zig
const result = agent.process(message); // returns AgentError!Result

// Handle with try
const res = try agent.process(message);

// Or match explicitly
const res = agent.process(message) catch |err| {
    std.debug.print("Failed: {}\n", .{err});
    return err;
};

// Result union for success/error
switch (res) {
    .ok => |msg| {
        // Success case
        const text = try msg.contentAsText();
    },
    .err => |e| {
        // Error case
        std.debug.print("Agent error: {}\n", .{e});
    },
}
```

### vtable Pattern

Zig uses vtables for interface polymorphism:

```zig
pub const Agent = struct {
    ptr: *anyopaque,      // Opaque pointer to implementation
    vtable: *const VTable, // Function pointers

    pub const VTable = struct {
        name: *const fn (ptr: *anyopaque) []const u8,
        process: *const fn (ptr: *anyopaque, message: Message) AgentError!Result,
        deinit: *const fn (ptr: *anyopaque) void,
    };

    // Interface methods delegate to vtable
    pub fn process(self: Agent, message: Message) !Result {
        return self.vtable.process(self.ptr, message);
    }
};
```

### Performance

Zig provides exceptional performance:

- **Zero-overhead abstractions** - No hidden costs
- **Compile-time execution** - Many operations at comptime
- **No garbage collection** - Explicit memory management
- **SIMD support** - Built-in vector types
- **Cross-compilation** - Single command for any target

---

## Autodoc Status

Zig's built-in autodoc feature is experimental in v0.13.0:

```bash
# Generate autodoc (experimental)
zig build-lib src/agenkit.zig -femit-docs -fno-emit-bin

# Output in zig-out/docs/
```

**Current Status:**
- ✅ Markdown documentation (complete)
- 🚧 Autodoc generation (experimental - may have formatting issues)
- ✅ IDE integration (ZLS language server)

---

## IDE Integration

### Zed / Visual Studio Code

Install Zig Language Server (ZLS):

```bash
# Install ZLS
# macOS: brew install zls
# Or build from source: https://github.com/zigtools/zls

# VS Code: Install Zig extension
code --install-extension ziglang.vscode-zig

# Configure to use ZLS
```

Features:
- Hover for documentation
- Go to definition
- Auto-completion
- Inline error messages

### vim/neovim

Use ZLS with your LSP client:

```vim
" For vim-lsp
Plug 'prabirshrestha/vim-lsp'
" Configure for ZLS

" For coc.nvim
Plug 'neoclide/coc.nvim', {'branch': 'release'}
" :CocInstall coc-zls
```

---

## Documentation Standards

All Zig code follows standard doc comment conventions:

### Top-level Documentation

```zig
/// Agent interface for agenkit
///
/// An Agent is the core abstraction in Agenkit. Agents process messages and
/// return responses. They can wrap LLMs, implement patterns, or provide
/// custom logic.
///
/// Key design principles:
/// - Explicit error handling with error union types
/// - Explicit memory management with allocators
/// - Composable through interface-based design
pub const Agent = struct {
    // ...
};
```

### Function Documentation

```zig
/// Create a new message with text content
///
/// Allocates a new Message with the given role and text content.
/// Caller is responsible for calling deinit().
///
/// Arguments:
///   - allocator: Allocator for message memory
///   - role: Message role (user, assistant, system, tool)
///   - text: Text content for the message
///
/// Returns: A new Message or allocation error
///
/// Example:
///   var msg = try Message.withText(allocator, .user, "Hello");
///   defer msg.deinit();
pub fn withText(
    allocator: std.mem.Allocator,
    role: Role,
    text: []const u8
) !Message {
    // ...
}
```

---

## Examples

Comprehensive examples are available in the [Zig examples directory](https://github.com/scttfrdmn/agenkit/tree/main/agenkit-zig/examples):

### Basic Examples
- Echo agent
- HTTP transport
- Sequential pipeline
- Parallel execution

### Pattern Examples
- Reflection loop
- Agents-as-Tools
- Orchestration
- ReAct with tools
- All 18 agent patterns

### LLM Examples
- OpenAI integration
- Anthropic/Claude integration
- Google Gemini integration
- AWS Bedrock integration
- Ollama (local models)
- LiteLLM proxy

### Production Examples
- Error handling
- Memory management
- Long-running operations
- Testing patterns
- Tracing/observability

---

## Testing

Run tests for the Zig implementation:

```bash
cd agenkit-zig

# Run all tests
zig build test

# Run specific test
zig build test -Dtest-filter="echo"

# Run with verbose output
zig build test --summary all

# Run benchmarks
zig build bench
```

---

## Cross-Language Compatibility

Zig agents can communicate with Python, Go, TypeScript, and other language implementations via HTTP:

### Call Python Agent from Zig

```zig
const transports = agenkit.transports;

const python_agent = try transports.HttpAgent.init(
    allocator,
    "http://localhost:8000",
    .{}
);
defer python_agent.deinit();

const result = try python_agent.agent().process(message);
```

### Expose Zig Agent to Python

```zig
const transports = agenkit.transports;

const echo_agent = try EchoAgent.init(allocator);
const server = try transports.HttpServer.init(
    allocator,
    echo_agent.agent(),
    .{ .port = 8080 }
);
defer server.deinit();

try server.serve(); // Blocking
```

Python can now call this agent:
```python
from agenkit.transports import HTTPClient

zig_agent = HTTPClient("http://localhost:8080")
response = await zig_agent.process(message)
```

---

## Build System

Zig uses build.zig for configuration:

```zig
// build.zig
const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    // Library
    const lib = b.addStaticLibrary(.{
        .name = "agenkit",
        .root_source_file = .{ .path = "src/agenkit.zig" },
        .target = target,
        .optimize = optimize,
    });
    b.installArtifact(lib);

    // Tests
    const tests = b.addTest(.{
        .root_source_file = .{ .path = "src/agenkit.zig" },
        .target = target,
        .optimize = optimize,
    });
    const run_tests = b.addRunArtifact(tests);
    const test_step = b.step("test", "Run tests");
    test_step.dependOn(&run_tests.step);
}
```

---

## Contributing

Help improve Zig implementation:

1. **Report issues**: [GitHub Issues](https://github.com/scttfrdmn/agenkit/issues)
2. **Improve docs**: Add doc comments to code
3. **Add examples**: [Submit PR](https://github.com/scttfrdmn/agenkit/pulls)

---

## See Also

- **[Python API Reference](python.md)**: Python implementation
- **[Go API Reference](go.md)**: Go implementation
- **[Rust API Reference](rust.md)**: Rust implementation
- **[TypeScript API Reference](typescript.md)**: TypeScript implementation
- **[C++ API Reference](cpp.md)**: C++ implementation
- **[Cross-Language Guide](../guides/cross-language.md)**: Language interop
- **[Zig README](https://github.com/scttfrdmn/agenkit/blob/main/agenkit-zig/README.md)**: Zig-specific features

---

**Last Updated**: December 2025
**Zig Version**: 0.13.0+
**Agenkit Version**: 0.41.0+
