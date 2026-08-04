# Getting Started with Agenkit-Zig

A beginner-friendly guide to building AI agents with Zig.

## Table of Contents

- [Installation](#installation)
- [Your First Agent](#your-first-agent)
- [Understanding Messages](#understanding-messages)
- [Processing Patterns](#processing-patterns)
- [Error Handling](#error-handling)
- [Memory Management](#memory-management)
- [Testing Your Agent](#testing-your-agent)
- [Next Steps](#next-steps)

---

## Installation

### Prerequisites

You need Zig 0.15.2 or later. Check your version:

```bash
zig version
# Should output: 0.15.2 or higher
```

If you don't have Zig installed, download it from [ziglang.org](https://ziglang.org/download/).

### Option 1: Using Zig Package Manager (Recommended)

1. **Add Agenkit to your `build.zig.zon`:**

```zig
.{
    .name = "my-agent-project",
    .version = "0.1.0",
    .dependencies = .{
        .agenkit = .{
            .url = "https://github.com/scttfrdmn/agenkit/releases/download/v0.41.0/agenkit-zig.tar.gz",
            .hash = "1220...",  // Zig will tell you the correct hash
        },
    },
}
```

2. **Update your `build.zig`:**

```zig
const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    // Get agenkit dependency
    const agenkit = b.dependency("agenkit", .{
        .target = target,
        .optimize = optimize,
    });

    // Your executable
    const exe = b.addExecutable(.{
        .name = "my-agent",
        .root_source_file = b.path("src/main.zig"),
        .target = target,
        .optimize = optimize,
    });

    // Add agenkit module
    exe.root_module.addImport("agenkit", agenkit.module("agenkit"));
    b.installArtifact(exe);
}
```

3. **Build your project:**

```bash
zig build
```

Zig will download Agenkit automatically and provide the correct hash if needed.

### Option 2: Building from Source

Clone the repository and build:

```bash
git clone https://github.com/scttfrdmn/agenkit.git
cd agenkit/agenkit-zig
zig build test  # Verify everything works
```

To use in your project, reference the local path in `build.zig`:

```zig
const agenkit_path = b.pathFromRoot("../agenkit/agenkit-zig");
exe.root_module.addImport("agenkit", b.addModule("agenkit", .{
    .root_source_file = b.path("../agenkit/agenkit-zig/src/lib.zig"),
}));
```

---

## Your First Agent

Let's build a simple echo agent that responds to messages.

### Step 1: Create the Project

```bash
mkdir my-first-agent
cd my-first-agent
zig init-exe
```

### Step 2: Write the Agent Code

Edit `src/main.zig`:

```zig
const std = @import("std");
const agenkit = @import("agenkit");

pub fn main() !void {
    // Setup memory allocator
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("=== My First Agent ===\n\n", .{});

    // Create a message
    var msg = try agenkit.Message.withText(allocator, .user, "Hello, agent!");
    defer msg.deinit();

    std.debug.print("User: {s}\n", .{try msg.contentAsText()});

    // Create an echo agent
    var echo = try agenkit.EchoAgent.init(allocator);
    defer echo.agent().deinit();

    // Process the message
    const result = try echo.agent().process(msg);
    var response = try result.unwrap();
    defer response.deinit();

    std.debug.print("Agent: {s}\n", .{try response.contentAsText()});
}
```

### Step 3: Build and Run

```bash
zig build run
```

**Output:**
```
=== My First Agent ===

User: Hello, agent!
Agent: Echo: Hello, agent!
```

**Congratulations!** You've built your first AI agent with Zig.

---

## Understanding Messages

Messages are the core data structure in Agenkit. Every interaction uses messages.

### Message Structure

A message has three components:

1. **Role** - Who sent the message (user, assistant, system, tool)
2. **Content** - The message content (text or structured data)
3. **Metadata** - Optional key-value pairs

### Creating Messages

#### Text Messages

```zig
var msg = try agenkit.Message.withText(allocator, .user, "Hello!");
defer msg.deinit();
```

The three parameters are:
1. `allocator` - Memory allocator
2. `.user` - Role (`.user`, `.assistant`, `.system`, `.tool`)
3. `"Hello!"` - Text content

#### Messages with Metadata

```zig
var msg = try agenkit.Message.withText(allocator, .user, "Hello!");
defer msg.deinit();

// Add metadata
try msg.setMetadata("session_id", .{ .string = "abc-123" });
try msg.setMetadata("priority", .{ .integer = 5 });
```

#### Structured Messages

```zig
var obj = std.json.ObjectMap.init(allocator);
defer obj.deinit();

try obj.put("action", .{ .string = "search" });
try obj.put("query", .{ .string = "AI agents" });

var msg = try agenkit.Message.withStructured(allocator, .tool, .{ .object = obj });
defer msg.deinit();
```

### Reading Messages

```zig
// Get text content
const text = try msg.contentAsText();
std.debug.print("Content: {s}\n", .{text});

// Check role
if (msg.role == .user) {
    std.debug.print("Message from user\n", .{});
}

// Get metadata
if (msg.getMetadata("session_id")) |value| {
    std.debug.print("Session: {s}\n", .{value.string});
}
```

### Memory Management for Messages

**Always use `defer msg.deinit()`** after creating a message:

```zig
var msg = try agenkit.Message.withText(allocator, .user, "text");
defer msg.deinit();  // ← This is critical!
```

Without `deinit()`, you'll leak memory.

---

## Processing Patterns

Agenkit provides built-in patterns for common agent workflows.

### Echo Agent

The simplest agent - echoes messages back:

```zig
var echo = try agenkit.EchoAgent.init(allocator);
defer echo.agent().deinit();

const result = try echo.agent().process(msg);
var response = try result.unwrap();
defer response.deinit();
```

### Custom Agent

Build your own agent by implementing the Agent interface:

```zig
pub const GreetingAgent = struct {
    allocator: std.mem.Allocator,

    pub fn init(allocator: std.mem.Allocator) !*GreetingAgent {
        const self = try allocator.create(GreetingAgent);
        self.* = .{ .allocator = allocator };
        return self;
    }

    pub fn deinit(self: *GreetingAgent) void {
        self.allocator.destroy(self);
    }

    pub fn agent(self: *GreetingAgent) agenkit.Agent {
        return agenkit.Agent{
            .ptr = self,
            .vtable = &.{
                .name = nameImpl,
                .capabilities = capabilitiesImpl,
                .process = processImpl,
                .deinit = deinitImpl,
            },
        };
    }

    fn nameImpl(_: *anyopaque) []const u8 {
        return "greeting-agent";
    }

    fn capabilitiesImpl(_: *anyopaque, allocator: std.mem.Allocator) ![]const []const u8 {
        const caps = try allocator.alloc([]const u8, 1);
        caps[0] = "greeting";
        return caps;
    }

    fn processImpl(ptr: *anyopaque, message: agenkit.Message) agenkit.AgentError!agenkit.Result {
        const self: *GreetingAgent = @ptrCast(@alignCast(ptr));

        const user_text = message.contentAsText() catch {
            return agenkit.Result{ .err = agenkit.AgentError.InvalidInput };
        };

        // Create greeting response
        const greeting = std.fmt.allocPrint(
            self.allocator,
            "Hello! You said: {s}",
            .{user_text},
        ) catch {
            return agenkit.AgentError.ProcessingFailed;
        };
        defer self.allocator.free(greeting);

        const response = agenkit.Message.withText(
            self.allocator,
            .assistant,
            greeting,
        ) catch {
            return agenkit.AgentError.ProcessingFailed;
        };

        return agenkit.Result{ .ok = response };
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *GreetingAgent = @ptrCast(@alignCast(ptr));
        self.deinit();
    }
};
```

**Using your custom agent:**

```zig
var greeting = try GreetingAgent.init(allocator);
defer greeting.agent().deinit();

var msg = try agenkit.Message.withText(allocator, .user, "Hi there!");
defer msg.deinit();

const result = try greeting.agent().process(msg);
var response = try result.unwrap();
defer response.deinit();

std.debug.print("Response: {s}\n", .{try response.contentAsText()});
// Output: Response: Hello! You said: Hi there!
```

---

## Error Handling

Zig uses error unions (`!T`) for explicit error handling.

### The Result Type

Agent processing returns a `Result` union:

```zig
pub const Result = union(enum) {
    ok: Message,     // Success with response message
    err: AgentError, // Failure with error code
};
```

### Handling Results

#### Pattern 1: Try (Propagate Errors)

```zig
const result = try agent.process(msg);
var response = try result.unwrap();
defer response.deinit();
```

If an error occurs, it propagates up the call stack.

#### Pattern 2: Explicit Checking

```zig
const result = try agent.process(msg);

if (result.isOk()) {
    var response = try result.unwrap();
    defer response.deinit();
    std.debug.print("Success: {s}\n", .{try response.contentAsText()});
} else {
    const err = result.unwrapErr();
    std.debug.print("Error: {}\n", .{err});
}
```

#### Pattern 3: Catch

```zig
var response = result.unwrap() catch |err| {
    std.debug.print("Failed to unwrap: {}\n", .{err});
    return err;
};
defer response.deinit();
```

### Error Types

```zig
pub const AgentError = error{
    InvalidInput,         // Bad input message
    ProcessingFailed,     // Processing error
    ResourceExhausted,    // Out of resources
    NotImplemented,       // Feature not available
    ConfigurationError,   // Bad configuration
    StateError,          // Invalid state
};
```

### Best Practices

1. **Use `try` for prototyping** - Quick and clean
2. **Use explicit checks for production** - Better error messages
3. **Always handle errors** - Don't ignore them
4. **Use `errdefer` for cleanup** - Clean up on error paths

```zig
var msg = try Message.withText(allocator, .user, "text");
errdefer msg.deinit();  // Only runs if an error occurs below

// More operations that might fail...
try doSomething(msg);

return msg;  // Success - caller now owns msg
```

---

## Memory Management

Zig requires explicit memory management. Here's what you need to know.

### The Allocator

All memory operations use an `Allocator`:

```zig
var gpa = std.heap.GeneralPurposeAllocator(.{}){};
defer _ = gpa.deinit();
const allocator = gpa.allocator();
```

**GeneralPurposeAllocator** provides:
- Leak detection
- Memory safety checks
- Thread-safe allocation

### The `defer` Pattern

Pair every allocation with cleanup using `defer`:

```zig
var msg = try Message.withText(allocator, .user, "text");
defer msg.deinit();  // ← Cleanup happens automatically
```

`defer` executes when the scope exits, guaranteeing cleanup.

### Ownership Rules

#### Rule 1: Caller Owns Return Values

```zig
// Agent.capabilities returns owned memory
const caps = try agent.capabilities(allocator);
defer allocator.free(caps);  // You must free it
```

#### Rule 2: Borrowed References

```zig
// Agent.name returns borrowed memory
const name = agent.name();
// Don't free this - agent owns it
```

#### Rule 3: Consumed Values

```zig
var seq = try SequentialAgent.init(allocator);
defer seq.agent().deinit();

// addAgent consumes the agent
try seq.addAgent(echo.agent());
// Don't deinit echo - seq now owns it
```

### Detecting Memory Leaks

Run tests to find leaks:

```bash
zig build test
```

If there's a leak, you'll see:

```
error(gpa): memory address 0x123456 leaked:
/path/to/file.zig:42:13: 0x... in functionName
```

Fix by adding `defer` after the allocation.

### Common Mistakes

❌ **Mistake 1: Forgetting deinit**
```zig
var msg = try Message.withText(allocator, .user, "text");
// Forgot defer msg.deinit()
return;  // LEAK!
```

✅ **Fixed:**
```zig
var msg = try Message.withText(allocator, .user, "text");
defer msg.deinit();
return;  // OK - cleanup happens
```

❌ **Mistake 2: Using const for deinit**
```zig
const msg = try Message.withText(allocator, .user, "text");
defer msg.deinit();  // ERROR: can't call deinit on const
```

✅ **Fixed:**
```zig
var msg = try Message.withText(allocator, .user, "text");
defer msg.deinit();  // OK - var is mutable
```

❌ **Mistake 3: Double free**
```zig
var msg = try Message.withText(allocator, .user, "text");
defer msg.deinit();
msg.deinit();  // ERROR: freed twice!
```

✅ **Fixed:**
```zig
var msg = try Message.withText(allocator, .user, "text");
defer msg.deinit();  // Only free once
```

---

## Testing Your Agent

### Basic Test Structure

```zig
const std = @import("std");
const agenkit = @import("agenkit");

test "greeting agent responds correctly" {
    // Use testing allocator - it detects leaks
    const allocator = std.testing.allocator;

    // Create agent
    var agent = try GreetingAgent.init(allocator);
    defer agent.agent().deinit();

    // Create message
    var msg = try agenkit.Message.withText(allocator, .user, "Hello");
    defer msg.deinit();

    // Process
    const result = try agent.agent().process(msg);
    var response = try result.unwrap();
    defer response.deinit();

    // Assert
    const text = try response.contentAsText();
    try std.testing.expect(std.mem.startsWith(u8, text, "Hello!"));
}
```

### Running Tests

```bash
# Run all tests
zig build test

# Run specific file
zig test src/main.zig

# Verbose output
zig build test --summary all
```

### Test Best Practices

1. **Always use `std.testing.allocator`** - It detects leaks
2. **Test cleanup paths** - Ensure `defer` works correctly
3. **Test error cases** - Don't just test happy paths
4. **Use descriptive names** - `test "agent handles empty input"` not `test "test1"`

### Example: Testing Error Handling

```zig
test "agent returns error for empty message" {
    const allocator = std.testing.allocator;

    var agent = try MyAgent.init(allocator);
    defer agent.agent().deinit();

    var msg = try agenkit.Message.withText(allocator, .user, "");
    defer msg.deinit();

    const result = try agent.agent().process(msg);

    // Expect error result
    try std.testing.expect(result.isErr());
    const err = result.unwrapErr();
    try std.testing.expectEqual(agenkit.AgentError.InvalidInput, err);
}
```

---

## Next Steps

Now that you understand the basics, explore more advanced topics:

### 1. Learn Agent Patterns

Agenkit provides 11 built-in patterns:

- **Sequential** - Process messages in order
- **Parallel** - Concurrent processing
- **Reflection** - Self-improvement
- **React** - Reasoning and acting
- **And 7 more...**

See [PATTERNS.md](PATTERNS.md) for detailed guide.

### 2. Explore Examples

The `examples/` directory contains working examples:

```bash
# Basic examples
zig build run-echo
zig build run-error-handling
zig build run-memory

# Integration examples
zig build run-multi-pattern
zig build run-long-running
zig build run-evaluation
```

### 3. Read the API Documentation

See [API.md](API.md) for complete API reference.

### 4. Port from Other Languages

If you're coming from Python, Go, Rust, or C++, see [MIGRATION.md](MIGRATION.md).

### 5. Build Real Agents

Try building:
- **Chat bot** - Use ConversationalAgent pattern
- **Task executor** - Use TaskAgent pattern
- **Research assistant** - Combine Parallel + Sequential patterns
- **Autonomous agent** - Use AutonomousAgent for goal-driven behavior

### 6. Join the Community

- [GitHub Issues](https://github.com/scttfrdmn/agenkit/issues) - Report bugs, request features
- [Discussions](https://github.com/scttfrdmn/agenkit/discussions) - Ask questions
- [Contributing](../CONTRIBUTING.md) - Contribute code

---

## Quick Reference

### Project Setup

```bash
# Create project
mkdir my-agent && cd my-agent
zig init-exe

# Add agenkit to build.zig.zon
# Add import to build.zig
# Build
zig build run
```

### Common Patterns

```zig
// Message creation
var msg = try Message.withText(allocator, .user, "text");
defer msg.deinit();

// Agent processing
const result = try agent.process(msg);
var response = try result.unwrap();
defer response.deinit();

// Error handling
if (result.isOk()) {
    // Handle success
} else {
    const err = result.unwrapErr();
    // Handle error
}

// Memory management
var obj = try allocator.create(T);
defer allocator.destroy(obj);
```

### Testing

```zig
test "description" {
    const allocator = std.testing.allocator;
    // Test code...
}
```

Run with: `zig build test`

---

## Troubleshooting

### "memory address leaked"

**Cause:** Forgot to call `deinit()`

**Fix:** Add `defer obj.deinit()` after creation

### "expected type '*T', found '*const T'"

**Cause:** Used `const` instead of `var` for mutable object

**Fix:** Change `const msg = ...` to `var msg = ...`

### "error: InvalidInput"

**Cause:** Message content is wrong type (e.g., structured when text expected)

**Fix:** Use `Message.withText()` for text or `Message.withStructured()` for JSON

### Build fails with "dependency not found"

**Cause:** Zig couldn't download dependency or hash mismatch

**Fix:** Run `zig build` again - it will show the correct hash

---

## Getting Help

- **Documentation:** [API.md](API.md), [PATTERNS.md](PATTERNS.md)
- **Examples:** Check `examples/` directory
- **Issues:** [GitHub Issues](https://github.com/scttfrdmn/agenkit/issues)
- **Discussions:** [GitHub Discussions](https://github.com/scttfrdmn/agenkit/discussions)

**Welcome to the Agenkit community! Happy building! 🚀**
