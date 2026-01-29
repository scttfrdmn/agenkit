# Getting Started with Agenkit (Zig)

**Target audience**: Zig developers new to Agenkit
**Time to first agent**: 15-30 minutes
**Prerequisites**: Zig 0.15.2+

---

## Installation

Add to your `build.zig.zon`:

```zig
.{
    .name = "your-project",
    .version = "0.1.0",
    .dependencies = .{
        .agenkit = .{
            .url = "https://github.com/yourusername/agenkit-zig/archive/v0.50.0.tar.gz",
            .hash = "...",
        },
    },
}
```

And in your `build.zig`:

```zig
const agenkit = b.dependency("agenkit", .{});
exe.root_module.addImport("agenkit", agenkit.module("agenkit"));
```

---

## Your First Agent

Let's create a simple greeting agent:

```zig
const std = @import("std");
const agenkit = @import("agenkit");
const Agent = agenkit.Agent;
const Message = agenkit.Message;
const Allocator = std.mem.Allocator;

const GreetingAgent = struct {
    allocator: Allocator,

    pub fn init(allocator: Allocator) *GreetingAgent {
        const self = allocator.create(GreetingAgent) catch unreachable;
        self.* = GreetingAgent{ .allocator = allocator };
        return self;
    }

    pub fn deinit(self: *GreetingAgent) void {
        self.allocator.destroy(self);
    }

    pub fn asAgent(self: *GreetingAgent) Agent {
        return Agent{
            .ptr = self,
            .vtable = &.{
                .name = name,
                .process = process,
                .deinit = deinitVTable,
            },
        };
    }

    fn name(ptr: *anyopaque) []const u8 {
        _ = ptr;
        return "greeting-agent";
    }

    fn process(
        ptr: *anyopaque,
        allocator: Allocator,
        message: *Message,
    ) !*Message {
        const self: *GreetingAgent = @ptrCast(@alignCast(ptr));

        const greeting = try std.fmt.allocPrint(
            allocator,
            "Hello! You said: {s}",
            .{message.content.text},
        );

        const response = try allocator.create(Message);
        response.* = try Message.withText(allocator, .assistant, greeting);
        try response.setMetadata("processed_by", std.json.Value{ .string = "greeting-agent" });

        return response;
    }

    fn deinitVTable(ptr: *anyopaque) void {
        const self: *GreetingAgent = @ptrCast(@alignCast(ptr));
        self.deinit();
    }
};

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var greeting_agent = GreetingAgent.init(allocator);
    defer greeting_agent.deinit();
    const agent = greeting_agent.asAgent();

    var message = try Message.withText(allocator, .user, "Hi there!");
    defer message.deinit();

    const response = try agent.process(allocator, &message);
    defer response.deinit();

    std.debug.print("Agent: {s}\n", .{response.content.text});
    // Output: Agent: Hello! You said: Hi there!
}
```

Run it:
```bash
zig build run
```

---

## Production-Ready Agent with Middleware

Add resilience with retry, circuit breaker, and timeout middleware:

```zig
const std = @import("std");
const agenkit = @import("agenkit");
const Agent = agenkit.Agent;
const Message = agenkit.Message;
const middleware = agenkit.middleware;
const Allocator = std.mem.Allocator;

const ProductionAgent = struct {
    allocator: Allocator,

    pub fn asAgent(self: *ProductionAgent) Agent {
        return Agent{
            .ptr = self,
            .vtable = &.{
                .name = name,
                .process = process,
                .deinit = deinitVTable,
            },
        };
    }

    fn name(ptr: *anyopaque) []const u8 {
        _ = ptr;
        return "production-agent";
    }

    fn process(
        ptr: *anyopaque,
        allocator: Allocator,
        message: *Message,
    ) !*Message {
        _ = ptr;

        // Simulate some processing
        std.time.sleep(100 * std.time.ns_per_ms);

        const content = try std.fmt.allocPrint(
            allocator,
            "Processed: {s}",
            .{message.content.text},
        );

        const response = try allocator.create(Message);
        response.* = try Message.withText(allocator, .assistant, content);
        try response.setMetadata("agent", std.json.Value{ .string = "production-agent" });

        return response;
    }

    fn deinitVTable(ptr: *anyopaque) void {
        _ = ptr;
    }
};

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var base_agent = ProductionAgent{ .allocator = allocator };

    // Wrap with middleware (v0.50.0 uses milliseconds with _ms suffix)
    var retry_decorator = try middleware.RetryDecorator.init(
        allocator,
        base_agent.asAgent(),
        .{
            .max_attempts = 3,
            .initial_delay_ms = 100,
        },
    );
    defer retry_decorator.deinit();

    var circuit_breaker = try middleware.CircuitBreakerDecorator.init(
        allocator,
        retry_decorator.asAgent(),
        .{
            .failure_threshold = 5,
            .recovery_timeout_ms = 30000,
        },
    );
    defer circuit_breaker.deinit();

    var timeout_decorator = try middleware.TimeoutDecorator.init(
        allocator,
        circuit_breaker.asAgent(),
        .{ .timeout_ms = 5000 },
    );
    defer timeout_decorator.deinit();

    const agent = timeout_decorator.asAgent();

    var message = try Message.withText(allocator, .user, "Hello production!");
    defer message.deinit();

    const response = try agent.process(allocator, &message);
    defer response.deinit();

    std.debug.print("{s}\n", .{response.content.text});
}
```

**Note**: Zig uses milliseconds with `_ms` suffix for clarity (v0.50.0).

---

## Using LLM Adapters

### OpenAI Example

```zig
const std = @import("std");
const agenkit = @import("agenkit");
const OpenAILLM = agenkit.adapters.OpenAILLM;
const Message = agenkit.Message;

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    // Initialize LLM (validates parameters at construction)
    var llm_impl = try OpenAILLM.init(
        allocator,
        std.process.getEnvVarOwned(allocator, "OPENAI_API_KEY") catch unreachable,
        "gpt-4-turbo",
    );
    defer llm_impl.deinit();
    const llm = llm_impl.asLLM();

    // Create conversation
    var system_msg = try Message.withText(allocator, .system, "You are a helpful assistant.");
    defer system_msg.deinit();

    var user_msg = try Message.withText(allocator, .user, "What is Agenkit?");
    defer user_msg.deinit();

    const messages = [_]*Message{ &system_msg, &user_msg };

    // Configure options with validation
    var options = agenkit.CallOptions.init(allocator);
    defer options.deinit();
    try options.withTemperature(0.7);  // Validated: 0-2
    try options.withMaxTokens(1024);   // Validated: >0

    // Get completion
    const response = try llm.complete(allocator, &messages, &options);
    defer response.deinit();
    std.debug.print("{s}\n", .{response.content.text});

    // Stream response
    var stream = try llm.stream(allocator, &messages, &options);
    defer stream.deinit();

    while (try stream.next(allocator)) |chunk| {
        defer chunk.deinit();
        std.debug.print("{s}", .{chunk.content.text});
    }
}
```

### Anthropic Example

```zig
var llm_impl = try agenkit.adapters.AnthropicLLM.init(
    allocator,
    std.process.getEnvVarOwned(allocator, "ANTHROPIC_API_KEY") catch unreachable,
    "claude-3-5-sonnet-20241022",
);
defer llm_impl.deinit();

var options = agenkit.CallOptions.init(allocator);
try options.withTemperature(1.0);
try options.withMaxTokens(4096);
```

**Parameter Validation** (v0.50.0):
- `temperature`: 0.0 - 2.0 (validated via `withTemperature()`)
- `max_tokens`: > 0 (validated via `withMaxTokens()`)
- `top_p`: 0.0 - 1.0 (validated via `withTopP()`)

Invalid values return errors immediately.

---

## Common Patterns

Agenkit provides **18 core patterns** for building AI agents (see the [Agent Patterns Book](../../agent-patterns-book) for comprehensive details). Here are three essential patterns to get started:

### 1. Reflection Pattern

**One-line**: Iterative self-improvement through draft-critique-refine loop

```zig
const std = @import("std");
const agenkit = @import("agenkit");
const ReflectionAgent = agenkit.patterns.ReflectionAgent;
const OpenAILLM = agenkit.adapters.OpenAILLM;

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var llm_impl = try OpenAILLM.init(
        allocator,
        std.process.getEnvVarOwned(allocator, "OPENAI_API_KEY") catch unreachable,
        "gpt-4-turbo",
    );
    defer llm_impl.deinit();
    const llm = llm_impl.asLLM();

    var agent = try ReflectionAgent.init(allocator, llm, .{
        .max_iterations = 3,
        .reflection_prompt = "Review and improve this response:",
    });
    defer agent.deinit();

    var message = try agenkit.Message.withText(allocator, .user, "Explain comptime in Zig");
    defer message.deinit();

    const response = try agent.process(allocator, &message);
    defer response.deinit();

    std.debug.print("{s}\n", .{response.content.text});
}
```

### 2. ReAct Pattern

**One-line**: Reasoning + Acting with explicit thought-action-observation loop

```zig
const std = @import("std");
const agenkit = @import("agenkit");
const Tool = agenkit.Tool;
const ToolResult = agenkit.ToolResult;
const ReActAgent = agenkit.patterns.ReActAgent;

const SearchTool = struct {
    allocator: std.mem.Allocator,

    pub fn asTool(self: *SearchTool) Tool {
        return Tool{
            .ptr = self,
            .vtable = &.{
                .name = name,
                .description = description,
                .parameters = parameters,
                .execute = execute,
                .deinit = deinitVTable,
            },
        };
    }

    fn name(ptr: *anyopaque) []const u8 {
        _ = ptr;
        return "search";
    }

    fn description(ptr: *anyopaque) []const u8 {
        _ = ptr;
        return "Search for information";
    }

    fn parameters(ptr: *anyopaque, allocator: std.mem.Allocator) !std.json.Value {
        _ = ptr;
        return std.json.parseFromSlice(
            std.json.Value,
            allocator,
            \\{"query": {"type": "string", "description": "Search query"}}
        ,
            .{},
        );
    }

    fn execute(
        ptr: *anyopaque,
        allocator: std.mem.Allocator,
        params: std.json.Value,
    ) !ToolResult {
        _ = ptr;
        const query = params.object.get("query").?.string;

        const result = try std.fmt.allocPrint(
            allocator,
            "Search results for: {s}",
            .{query},
        );

        return ToolResult{
            .success = true,
            .result = result,
        };
    }

    fn deinitVTable(ptr: *anyopaque) void {
        _ = ptr;
    }
};

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var llm_impl = try agenkit.adapters.OpenAILLM.init(
        allocator,
        std.process.getEnvVarOwned(allocator, "OPENAI_API_KEY") catch unreachable,
        "gpt-4-turbo",
    );
    defer llm_impl.deinit();

    var search_tool = SearchTool{ .allocator = allocator };
    const tools = [_]Tool{search_tool.asTool()};

    var agent = try ReActAgent.init(allocator, llm_impl.asLLM(), &tools, .{
        .max_iterations = 5,
    });
    defer agent.deinit();

    var message = try agenkit.Message.withText(allocator, .user, "What's the weather in Paris?");
    defer message.deinit();

    const response = try agent.process(allocator, &message);
    defer response.deinit();

    std.debug.print("{s}\n", .{response.content.text});
}
```

### 3. Sequential Pattern

**One-line**: Execute agents in order, passing outputs between stages

```zig
const std = @import("std");
const agenkit = @import("agenkit");
const SequentialAgent = agenkit.patterns.SequentialAgent;

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    // Create agent pipeline
    const agents = [_]agenkit.Agent{
        research_agent.asAgent(),
        summarizer_agent.asAgent(),
        editor_agent.asAgent(),
    };

    var agent = try SequentialAgent.init(allocator, &agents);
    defer agent.deinit();

    var message = try agenkit.Message.withText(allocator, .user, "Research AI safety");
    defer message.deinit();

    const final_response = try agent.process(allocator, &message);
    defer final_response.deinit();

    std.debug.print("{s}\n", .{final_response.content.text});
}
```

**See all 18 patterns**: Refer to the [Agent Patterns Book](../../agent-patterns-book) for complete pattern descriptions, trade-offs, and when to use each pattern.

---

## Memory Management

### Allocators

```zig
// Always pass allocator explicitly
pub fn init(allocator: Allocator) !*Self {
    const self = try allocator.create(Self);
    return self;
}

pub fn deinit(self: *Self) void {
    self.allocator.destroy(self);
}
```

### Error Handling

```zig
// Use error unions for fallible operations
fn process(message: *Message) !*Message {
    const response = try createResponse();
    return response;
}

// Check errors with try
const result = try agent.process(&message);

// Or handle explicitly
const result = agent.process(&message) catch |err| {
    std.debug.print("Error: {}\n", .{err});
    return err;
};
```

---

## Common Pitfalls

### 1. Memory Leaks

```zig
// WRONG: Forgot to call deinit
var message = try Message.withText(allocator, .user, "Hello");
// ... use message ...
// ❌ Memory leak!

// CORRECT: Always defer deinit
var message = try Message.withText(allocator, .user, "Hello");
defer message.deinit();
// ... use message ...
// ✅ Cleaned up automatically
```

### 2. Comptime vs Runtime

```zig
// Comptime: Known at compile time
const pattern_count = 18;

// Runtime: Determined at runtime
var iteration_count: usize = 0;
```

### 3. Pointer Alignment

```zig
// Always use @ptrCast with @alignCast for interface patterns
const self: *MyAgent = @ptrCast(@alignCast(ptr));
```

---

## Next Steps

1. **Explore Patterns**: See the [Agent Patterns Book](../../agent-patterns-book) for all 18 patterns
2. **Read Architecture**: `ARCHITECTURE.md` explains design principles
3. **Check Examples**: `agenkit-zig/examples/` has production examples
4. **API Reference**: Coming soon in `docs/api-reference/zig/`
5. **Zig Language**: https://ziglang.org/documentation/master/

---

## Quick Reference

```zig
// Core imports
const agenkit = @import("agenkit");
const Agent = agenkit.Agent;
const Message = agenkit.Message;
const Tool = agenkit.Tool;

// Middleware
const middleware = agenkit.middleware;
middleware.RetryDecorator
middleware.TimeoutDecorator
middleware.CircuitBreakerDecorator

// LLM adapters
const OpenAILLM = agenkit.adapters.OpenAILLM;
const AnthropicLLM = agenkit.adapters.AnthropicLLM;

// Patterns
const patterns = agenkit.patterns;
patterns.ReflectionAgent
patterns.ReActAgent
patterns.SequentialAgent

// Error handling
try operation();  // Propagate error
operation() catch |err| { /* handle */ };
```

---

**Version**: v0.50.0
**Last Updated**: January 28, 2026

For help: Open an issue at https://github.com/yourusername/agenkit/issues
