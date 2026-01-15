# Getting Started with Agenkit - Zig

**Complete guide to building zero-dependency AI agents with Agenkit in Zig**

## Table of Contents

1. [Installation](#installation)
2. [Your First Agent](#your-first-agent)
3. [Core Concepts](#core-concepts)
4. [Using Patterns](#using-patterns)
5. [Adding Middleware](#adding-middleware)
6. [Working with LLMs](#working-with-llms)
7. [Testing Your Agents](#testing-your-agents)
8. [Next Steps](#next-steps)

---

## Installation

### Prerequisites

- Zig 0.11 or higher (install from [ziglang.org](https://ziglang.org/download/))

### Create New Project

```bash
mkdir my-agent
cd my-agent
zig init-exe
```

### Add Agenkit Dependency

Edit `build.zig`:

```zig
const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    // Add agenkit dependency
    const agenkit = b.dependency("agenkit", .{
        .target = target,
        .optimize = optimize,
    });

    const exe = b.addExecutable(.{
        .name = "my-agent",
        .root_source_file = .{ .path = "src/main.zig" },
        .target = target,
        .optimize = optimize,
    });

    // Link agenkit
    exe.addModule("agenkit", agenkit.module("agenkit"));

    b.installArtifact(exe);
}
```

Create `build.zig.zon`:

```zig
.{
    .name = "my-agent",
    .version = "0.1.0",
    .dependencies = .{
        .agenkit = .{
            .url = "https://github.com/scttfrdmn/agenkit/releases/download/v0.46.0/agenkit-zig.tar.gz",
            .hash = "1220...",  // Use actual hash from release
        },
    },
}
```

### Verify Installation

```bash
zig build
# Should compile successfully
```

---

## Your First Agent

Let's create a simple agent that processes messages:

### Step 1: Create Your Agent

Create `src/agent.zig`:

```zig
const std = @import("std");
const agenkit = @import("agenkit");

/// A simple agent that greets users
pub const GreetingAgent = struct {
    allocator: std.mem.Allocator,

    const Self = @This();

    pub fn init(allocator: std.mem.Allocator) Self {
        return Self{
            .allocator = allocator,
        };
    }

    pub fn deinit(self: *Self) void {
        _ = self;
        // Cleanup if needed
    }

    pub fn name(self: *const Self) []const u8 {
        _ = self;
        return "greeting-agent";
    }

    pub fn process(self: *Self, message: agenkit.Message) !agenkit.Message {
        // Get user message content
        const user_message = message.content;

        // Create response
        const response_content = try std.fmt.allocPrint(
            self.allocator,
            "Hello! You said: '{s}'. How can I help you today?",
            .{user_message},
        );

        return agenkit.Message{
            .role = .assistant,
            .content = response_content,
            .metadata = null,
            .allocator = self.allocator,
        };
    }
};
```

### Step 2: Use Your Agent

Edit `src/main.zig`:

```zig
const std = @import("std");
const agent_mod = @import("agent.zig");

pub fn main() !void {
    // Setup allocator
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    // Create agent instance
    var agent = agent_mod.GreetingAgent.init(allocator);
    defer agent.deinit();

    // Create a user message
    const user_msg = agenkit.Message{
        .role = .user,
        .content = "Hi there!",
        .metadata = null,
        .allocator = allocator,
    };

    // Process the message
    const response = try agent.process(user_msg);
    defer allocator.free(response.content);

    // Print the response
    const stdout = std.io.getStdOut().writer();
    try stdout.print("{s}: {s}\n", .{ agent.name(), response.content });
}
```

### Step 3: Run It

```bash
zig build run
# Output: greeting-agent: Hello! You said: 'Hi there!'. How can I help you today?
```

**🎉 Congratulations!** You've created your first Agenkit agent in Zig.

---

## Core Concepts

### The Agent Interface

Every agent in Agenkit implements these methods:

```zig
pub const Agent = struct {
    allocator: std.mem.Allocator,

    pub fn name(self: *const Self) []const u8 {
        // Return agent name
    }

    pub fn process(self: *Self, message: Message) !Message {
        // Process message and return response
        // ! indicates this can return an error
    }

    pub fn deinit(self: *Self) void {
        // Clean up resources
    }
};
```

**Key points**:
- Explicit allocator passed to all agents
- Error union `!` for functions that can fail
- Manual resource cleanup with `deinit`

### Messages

Messages are the unit of communication:

```zig
const agenkit = @import("agenkit");

// Create a message
const msg = agenkit.Message{
    .role = .user,           // Role: .user, .assistant, .system
    .content = "Hello!",     // Content as string
    .metadata = null,        // Optional metadata (JSON)
    .allocator = allocator,  // Explicit allocator
};

// Access message properties
std.debug.print("Role: {}\n", .{msg.role});
std.debug.print("Content: {s}\n", .{msg.content});
```

### Memory Management

Zig requires explicit memory management:

```zig
const std = @import("std");

pub const MyAgent = struct {
    allocator: std.mem.Allocator,
    cached_data: ?[]u8,

    pub fn init(allocator: std.mem.Allocator) MyAgent {
        return MyAgent{
            .allocator = allocator,
            .cached_data = null,
        };
    }

    pub fn deinit(self: *MyAgent) void {
        // Free any allocated memory
        if (self.cached_data) |data| {
            self.allocator.free(data);
        }
    }

    pub fn process(self: *MyAgent, message: agenkit.Message) !agenkit.Message {
        // Allocate response content
        const response_content = try std.fmt.allocPrint(
            self.allocator,
            "Processed: {s}",
            .{message.content},
        );
        // Caller must free response_content!

        return agenkit.Message{
            .role = .assistant,
            .content = response_content,
            .metadata = null,
            .allocator = self.allocator,
        };
    }
};
```

### Error Handling

Zig uses error sets and error unions:

```zig
const ProcessingError = error{
    EmptyContent,
    InvalidFormat,
    AllocationFailed,
};

pub fn process(self: *MyAgent, message: agenkit.Message) !agenkit.Message {
    // Validate input
    if (message.content.len == 0) {
        return ProcessingError.EmptyContent;
    }

    // Try to process - propagate errors with try
    const result = try self.processInternal(message);

    // Or catch and handle errors
    const data = self.fetchData() catch |err| switch (err) {
        error.NetworkFailure => {
            std.log.warn("Network failed, using cached data", .{});
            return self.cachedData;
        },
        else => return err,
    };

    return result;
}
```

### Tools

Tools let agents take actions:

```zig
const std = @import("std");
const agenkit = @import("agenkit");

pub const CalculatorTool = struct {
    allocator: std.mem.Allocator,

    pub fn init(allocator: std.mem.Allocator) CalculatorTool {
        return CalculatorTool{ .allocator = allocator };
    }

    pub fn name(self: *const CalculatorTool) []const u8 {
        _ = self;
        return "calculator";
    }

    pub fn description(self: *const CalculatorTool) []const u8 {
        _ = self;
        return "Performs basic arithmetic operations";
    }

    pub fn execute(self: *CalculatorTool, params: std.json.Value) !agenkit.ToolResult {
        const operation = params.object.get("operation").?.string;
        const a = params.object.get("a").?.float;
        const b = params.object.get("b").?.float;

        const result = if (std.mem.eql(u8, operation, "add"))
            a + b
        else if (std.mem.eql(u8, operation, "multiply"))
            a * b
        else
            return error.UnknownOperation;

        // Format result
        const output = try std.fmt.allocPrint(
            self.allocator,
            "{d}",
            .{result},
        );

        return agenkit.ToolResult{
            .output = output,
            .error_msg = null,
            .allocator = self.allocator,
        };
    }
};
```

---

## Using Patterns

Agenkit includes 18 pre-built patterns for common agent architectures.

### Reflection Pattern

Iteratively improve outputs through self-critique:

```zig
const agenkit = @import("agenkit");

// Configure reflection
const config = agenkit.ReflectionConfig{
    .max_iterations = 3,
    .quality_threshold = 0.8,
    .stop_on_repeat = true,
};

// Create reflection agent
var generator = GeneratorAgent.init(allocator);
var critic = CriticAgent.init(allocator);

var agent = try agenkit.ReflectionAgent.init(
    allocator,
    &generator.agent,
    &critic.agent,
    config,
);
defer agent.deinit();

// Use it
const msg = agenkit.Message{
    .role = .user,
    .content = "Write a haiku about coding",
    .metadata = null,
    .allocator = allocator,
};

const response = try agent.process(msg);
defer allocator.free(response.content);

// Response includes iteration metadata
if (response.metadata) |metadata| {
    std.debug.print("Iterations: {}\n", .{metadata.get("iterations")});
    std.debug.print("Quality: {d}\n", .{metadata.get("final_quality_score")});
}
```

### Sequential Pattern

Chain multiple agents in sequence:

```zig
// Create a pipeline: research → summarize → format
var research = ResearchAgent.init(allocator);
var summary = SummaryAgent.init(allocator);
var formatter = FormatterAgent.init(allocator);

const agents = [_]*agenkit.Agent{
    &research.agent,
    &summary.agent,
    &formatter.agent,
};

var pipeline = try agenkit.SequentialPattern.init(allocator, &agents);
defer pipeline.deinit();

// Input flows through each agent in order
const msg = agenkit.Message{
    .role = .user,
    .content = "Research quantum computing",
    .metadata = null,
    .allocator = allocator,
};

const response = try pipeline.process(msg);
defer allocator.free(response.content);
```

### Parallel Pattern

Run multiple agents concurrently and aggregate results:

```zig
// Configure parallel execution
var technical = TechnicalAgent.init(allocator);
var business = BusinessAgent.init(allocator);
var user_agent = UserAgent.init(allocator);

const agents = [_]*agenkit.Agent{
    &technical.agent,
    &business.agent,
    &user_agent.agent,
};

const config = agenkit.ParallelConfig{
    .agents = &agents,
    .aggregation = .merge,
};

var parallel = try agenkit.ParallelPattern.init(allocator, config);
defer parallel.deinit();

// All agents process simultaneously
const msg = agenkit.Message{
    .role = .user,
    .content = "Analyze this product idea",
    .metadata = null,
    .allocator = allocator,
};

const response = try parallel.process(msg);
defer allocator.free(response.content);
```

### ReAct Pattern

Reasoning + Acting with tool use:

```zig
// Configure ReAct
var search_tool = SearchTool.init(allocator);
var calc_tool = CalculatorTool.init(allocator);

const tools = [_]*agenkit.Tool{
    &search_tool.tool,
    &calc_tool.tool,
};

const config = agenkit.ReActConfig{
    .max_steps = 5,
    .tools = &tools,
};

var reasoning = ReasoningAgent.init(allocator);

var agent = try agenkit.ReActAgent.init(
    allocator,
    &reasoning.agent,
    config,
);
defer agent.deinit();

// Agent will alternate between thinking and acting
const msg = agenkit.Message{
    .role = .user,
    .content = "What's the population of Tokyo divided by the population of NYC?",
    .metadata = null,
    .allocator = allocator,
};

const response = try agent.process(msg);
defer allocator.free(response.content);

// Response includes reasoning trace
if (response.metadata) |metadata| {
    std.debug.print("Steps: {}\n", .{metadata.get("steps")});
    std.debug.print("Tool calls: {}\n", .{metadata.get("tool_calls")});
}
```

---

## Adding Middleware

Middleware adds production features without changing your agent code.

### Retry Logic

Automatically retry failed operations:

```zig
const agenkit = @import("agenkit");
const std = @import("std");

// Configure retries
const config = agenkit.RetryConfig{
    .max_attempts = 3,
    .backoff_factor = 2.0,
    .initial_delay_ms = 1000,
    .max_delay_ms = 30000,
};

// Wrap your agent
var base_agent = MyAgent.init(allocator);
var resilient_agent = try agenkit.RetryMiddleware.init(
    allocator,
    &base_agent.agent,
    config,
);
defer resilient_agent.deinit();

// Now handles transient failures automatically
const response = try resilient_agent.process(message);
defer allocator.free(response.content);
```

### Circuit Breaker

Prevent cascading failures:

```zig
// Configure circuit breaker
const config = agenkit.CircuitBreakerConfig{
    .failure_threshold = 5,
    .timeout_ms = 60000,
    .success_threshold = 2,
};

// Wrap your agent
var base_agent = MyAgent.init(allocator);
var protected_agent = try agenkit.CircuitBreakerMiddleware.init(
    allocator,
    &base_agent.agent,
    config,
);
defer protected_agent.deinit();

// Fails fast when circuit is open
const response = protected_agent.process(message) catch |err| {
    if (err == error.CircuitOpen) {
        std.log.warn("Circuit is open - service unavailable", .{});
        return err;
    }
    return err;
};
defer allocator.free(response.content);
```

### Timeout

Set maximum execution time:

```zig
// Configure timeout
const config = agenkit.TimeoutConfig{
    .timeout_ms = 30000,
    .grace_period_ms = 5000,
};

// Wrap your agent
var base_agent = MyAgent.init(allocator);
var timed_agent = try agenkit.TimeoutMiddleware.init(
    allocator,
    &base_agent.agent,
    config,
);
defer timed_agent.deinit();

// Will cancel after 30 seconds
const response = timed_agent.process(message) catch |err| {
    if (err == error.Timeout) {
        std.log.warn("Agent took too long to respond", .{});
        return err;
    }
    return err;
};
defer allocator.free(response.content);
```

### Stacking Middleware

Combine multiple middleware layers:

```zig
// Stack middleware (innermost to outermost)
var base = MyAgent.init(allocator);

var with_timeout = try agenkit.TimeoutMiddleware.init(
    allocator,
    &base.agent,
    timeout_config,
);
defer with_timeout.deinit();

var with_circuit = try agenkit.CircuitBreakerMiddleware.init(
    allocator,
    &with_timeout.agent,
    circuit_config,
);
defer with_circuit.deinit();

var with_retry = try agenkit.RetryMiddleware.init(
    allocator,
    &with_circuit.agent,
    retry_config,
);
defer with_retry.deinit();

// Now has full production resilience
const response = try with_retry.process(message);
defer allocator.free(response.content);
```

---

## Working with LLMs

### OpenAI Integration

```zig
const agenkit = @import("agenkit");
const std = @import("std");

// Create OpenAI agent
const config = agenkit.OpenAIConfig{
    .model = "gpt-4",
    .api_key = std.os.getenv("OPENAI_API_KEY") orelse return error.MissingApiKey,
};

var agent = try agenkit.OpenAIAdapter.init(allocator, config);
defer agent.deinit();

// Use it like any agent
const msg = agenkit.Message{
    .role = .user,
    .content = "Explain quantum computing",
    .metadata = null,
    .allocator = allocator,
};

const response = try agent.process(msg);
defer allocator.free(response.content);

std.debug.print("{s}\n", .{response.content});
```

### Anthropic (Claude) Integration

```zig
// Create Claude agent
const config = agenkit.AnthropicConfig{
    .model = "claude-3-opus-20240229",
    .api_key = std.os.getenv("ANTHROPIC_API_KEY") orelse return error.MissingApiKey,
};

var agent = try agenkit.AnthropicAdapter.init(allocator, config);
defer agent.deinit();

const msg = agenkit.Message{
    .role = .user,
    .content = "Write a function to calculate Fibonacci numbers",
    .metadata = null,
    .allocator = allocator,
};

const response = try agent.process(msg);
defer allocator.free(response.content);
```

### Custom LLM Integration

```zig
const std = @import("std");
const agenkit = @import("agenkit");

pub const CustomLLMAgent = struct {
    allocator: std.mem.Allocator,
    api_url: []const u8,
    api_key: []const u8,
    client: std.http.Client,

    pub fn init(allocator: std.mem.Allocator, api_url: []const u8, api_key: []const u8) CustomLLMAgent {
        return CustomLLMAgent{
            .allocator = allocator,
            .api_url = api_url,
            .api_key = api_key,
            .client = std.http.Client{ .allocator = allocator },
        };
    }

    pub fn deinit(self: *CustomLLMAgent) void {
        self.client.deinit();
    }

    pub fn name(self: *const CustomLLMAgent) []const u8 {
        _ = self;
        return "custom-llm";
    }

    pub fn process(self: *CustomLLMAgent, message: agenkit.Message) !agenkit.Message {
        // Build request
        const request_body = try std.json.stringifyAlloc(
            self.allocator,
            .{ .prompt = message.content },
            .{},
        );
        defer self.allocator.free(request_body);

        // Call API
        var req = try self.client.request(.POST, self.api_url, .{
            .extra_headers = &.{
                .{ .name = "Authorization", .value = try std.fmt.allocPrint(self.allocator, "Bearer {s}", .{self.api_key}) },
                .{ .name = "Content-Type", .value = "application/json" },
            },
        }, .{});
        defer req.deinit();

        try req.writer().writeAll(request_body);
        try req.finish();
        try req.wait();

        // Parse response
        const body = try req.reader().readAllAlloc(self.allocator, 1024 * 1024);
        defer self.allocator.free(body);

        const parsed = try std.json.parseFromSlice(
            struct { completion: []const u8 },
            self.allocator,
            body,
            .{},
        );
        defer parsed.deinit();

        const response_content = try self.allocator.dupe(u8, parsed.value.completion);

        return agenkit.Message{
            .role = .assistant,
            .content = response_content,
            .metadata = null,
            .allocator = self.allocator,
        };
    }
};
```

---

## Testing Your Agents

### Unit Testing

```zig
const std = @import("std");
const testing = std.testing;
const agent_mod = @import("agent.zig");

test "GreetingAgent responds with greeting" {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var agent = agent_mod.GreetingAgent.init(allocator);
    defer agent.deinit();

    const msg = agenkit.Message{
        .role = .user,
        .content = "Hello",
        .metadata = null,
        .allocator = allocator,
    };

    const response = try agent.process(msg);
    defer allocator.free(response.content);

    try testing.expect(response.role == .assistant);
    try testing.expect(std.mem.indexOf(u8, response.content, "Hello") != null);
}

test "GreetingAgent has correct name" {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var agent = agent_mod.GreetingAgent.init(allocator);
    defer agent.deinit();

    try testing.expectEqualStrings("greeting-agent", agent.name());
}
```

Run tests:
```bash
zig build test
```

### Integration Testing with Mocks

```zig
const MockAgent = struct {
    allocator: std.mem.Allocator,
    response: []const u8,

    pub fn init(allocator: std.mem.Allocator, response: []const u8) MockAgent {
        return MockAgent{
            .allocator = allocator,
            .response = response,
        };
    }

    pub fn deinit(self: *MockAgent) void {
        _ = self;
    }

    pub fn name(self: *const MockAgent) []const u8 {
        _ = self;
        return "mock-agent";
    }

    pub fn process(self: *MockAgent, message: agenkit.Message) !agenkit.Message {
        _ = message;
        const content = try self.allocator.dupe(u8, self.response);
        return agenkit.Message{
            .role = .assistant,
            .content = content,
            .metadata = null,
            .allocator = self.allocator,
        };
    }
};

test "SequentialPattern processes through all agents" {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var agent1 = MockAgent.init(allocator, "Step 1 complete");
    var agent2 = MockAgent.init(allocator, "Step 2 complete");
    var agent3 = MockAgent.init(allocator, "Step 3 complete");

    const agents = [_]*agenkit.Agent{
        &agent1.agent,
        &agent2.agent,
        &agent3.agent,
    };

    var pipeline = try agenkit.SequentialPattern.init(allocator, &agents);
    defer pipeline.deinit();

    const msg = agenkit.Message{
        .role = .user,
        .content = "Start pipeline",
        .metadata = null,
        .allocator = allocator,
    };

    const response = try pipeline.process(msg);
    defer allocator.free(response.content);

    try testing.expect(std.mem.indexOf(u8, response.content, "Step 3 complete") != null);
}
```

---

## Next Steps

### Learn More

- **[Pattern Guide](../patterns/README.md)** - Detailed guide to all 18 patterns
- **[API Reference](../api/zig/README.md)** - Complete API documentation
- **[Best Practices](../best-practices/ZIG.md)** - Production deployment tips
- **[Examples](../../agenkit-zig/examples/)** - Working examples

### Performance Optimization

- **[Memory Management](../performance/ZIG_MEMORY.md)** - Allocators and arenas
- **[Comptime Features](../performance/ZIG_COMPTIME.md)** - Compile-time optimization
- **[Zero Dependencies](../philosophy/ZIG_ZERO_DEPS.md)** - Minimal dependency philosophy
- **[Profiling Guide](../performance/ZIG_PROFILING.md)** - Profile your agents

### Deploy to Production

- **[Docker Deployment](../deployment/DOCKER.md)** - Containerize your agents
- **[Bare Metal Deployment](../deployment/BARE_METAL.md)** - Direct system deployment
- **[Monitoring & Observability](../observability/README.md)** - Track agent performance

### Migrate from Other Languages

Coming from another language?

- **[C++ → Zig Migration](../migration/CPP_TO_ZIG.md)** - Migrate from C++
- **[Rust → Zig Migration](../migration/RUST_TO_ZIG.md)** - Migrate from Rust

---

## Quick Reference

### Installation
```bash
# In build.zig.zon
.dependencies = .{
    .agenkit = .{ .url = "...", .hash = "..." },
}
```

### Minimal Agent
```zig
pub const MyAgent = struct {
    allocator: std.mem.Allocator,

    pub fn init(allocator: std.mem.Allocator) MyAgent {
        return MyAgent{ .allocator = allocator };
    }

    pub fn deinit(self: *MyAgent) void {
        _ = self;
    }

    pub fn name(self: *const MyAgent) []const u8 {
        _ = self;
        return "my-agent";
    }

    pub fn process(self: *MyAgent, message: agenkit.Message) !agenkit.Message {
        const content = try std.fmt.allocPrint(
            self.allocator,
            "Response",
            .{},
        );

        return agenkit.Message{
            .role = .assistant,
            .content = content,
            .metadata = null,
            .allocator = self.allocator,
        };
    }
};
```

### Common Imports
```zig
const std = @import("std");
const agenkit = @import("agenkit");

// Core
const Agent = agenkit.Agent;
const Message = agenkit.Message;
const Tool = agenkit.Tool;
const ToolResult = agenkit.ToolResult;

// Patterns
const ReflectionAgent = agenkit.ReflectionAgent;
const ReActAgent = agenkit.ReActAgent;
const SequentialPattern = agenkit.SequentialPattern;
const ParallelPattern = agenkit.ParallelPattern;

// Middleware
const RetryMiddleware = agenkit.RetryMiddleware;
const CircuitBreakerMiddleware = agenkit.CircuitBreakerMiddleware;
const TimeoutMiddleware = agenkit.TimeoutMiddleware;
```

---

**Ready to build?** Check out the [examples](../../agenkit-zig/examples/) for working code you can run right now.

**Philosophy tip:** Zig's explicit control and zero-dependency approach make it perfect for embedded systems, edge computing, and environments where you need complete control over every byte!
