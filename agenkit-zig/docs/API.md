# Agenkit Zig API Reference

Complete API documentation for Agenkit-Zig v0.41.0.

## Table of Contents

- [Core Types](#core-types)
  - [Message](#message)
  - [Agent](#agent)
  - [Result](#result)
  - [Role](#role)
  - [AgentError](#agenterror)
- [Message API](#message-api)
- [Agent API](#agent-api)
- [Patterns](#patterns)
  - [Sequential](#sequential)
  - [Parallel](#parallel)
  - [Reflection](#reflection)
  - [React](#react)
  - [Planning](#planning)
  - [Task](#task)
  - [Conversational](#conversational)
  - [Agents as Tools](#agents-as-tools)
  - [Autonomous](#autonomous)
  - [Multiagent](#multiagent)
  - [Memory Hierarchy](#memory-hierarchy)

---

## Core Types

### Message

The fundamental unit of communication in Agenkit.

```zig
pub const Message = struct {
    role: Role,
    content: Content,
    metadata: std.StringHashMap(std.json.Value),
    allocator: std.mem.Allocator,

    // Constructors
    pub fn withText(allocator: std.mem.Allocator, role: Role, text: []const u8) !Message
    pub fn withStructured(allocator: std.mem.Allocator, role: Role, data: std.json.Value) !Message
    pub fn fromJson(allocator: std.mem.Allocator, value: std.json.Value) !Message

    // Methods
    pub fn deinit(self: *Message) void
    pub fn contentAsText(self: *const Message) ![]const u8
    pub fn setMetadata(self: *Message, key: []const u8, value: std.json.Value) !void
    pub fn getMetadata(self: *const Message, key: []const u8) ?std.json.Value
    pub fn toJson(self: *const Message, allocator: std.mem.Allocator) !std.json.Value
};
```

**Fields:**
- `role`: The message role (user, assistant, system, tool)
- `content`: Message content (text or structured data)
- `metadata`: Key-value pairs for tracing, sessions, etc.
- `allocator`: Allocator used for this message

**Example:**
```zig
var msg = try Message.withText(allocator, .user, "Hello, agent!");
defer msg.deinit();

try msg.setMetadata("session_id", .{ .string = "abc-123" });
const text = try msg.contentAsText();
```

---

### Agent

The core agent interface using vtable pattern.

```zig
pub const Agent = struct {
    ptr: *anyopaque,
    vtable: *const VTable,

    pub const VTable = struct {
        name: *const fn (ptr: *anyopaque) []const u8,
        capabilities: *const fn (ptr: *anyopaque, allocator: std.mem.Allocator) std.mem.Allocator.Error![]const []const u8,
        process: *const fn (ptr: *anyopaque, message: Message) AgentError!Result,
        deinit: *const fn (ptr: *anyopaque) void,
    };

    // Methods
    pub fn name(self: Agent) []const u8
    pub fn capabilities(self: Agent, allocator: std.mem.Allocator) ![]const []const u8
    pub fn process(self: Agent, message: Message) !Result
    pub fn deinit(self: Agent) void
};
```

**Example Implementation:**
```zig
pub const MyAgent = struct {
    allocator: std.mem.Allocator,
    agent_name: []const u8,

    pub fn init(allocator: std.mem.Allocator) !*MyAgent {
        const self = try allocator.create(MyAgent);
        self.* = .{
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

    fn nameImpl(ptr: *anyopaque) []const u8 {
        const self: *MyAgent = @ptrCast(@alignCast(ptr));
        return self.agent_name;
    }

    fn capabilitiesImpl(_: *anyopaque, allocator: std.mem.Allocator) ![]const []const u8 {
        const caps = try allocator.alloc([]const u8, 1);
        caps[0] = "custom";
        return caps;
    }

    fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
        const self: *MyAgent = @ptrCast(@alignCast(ptr));
        // Implementation...
        return Result{ .ok = response };
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *MyAgent = @ptrCast(@alignCast(ptr));
        self.allocator.destroy(self);
    }
};
```

---

### Result

Result type for agent processing.

```zig
pub const Result = union(enum) {
    ok: Message,
    err: AgentError,

    pub fn isOk(self: Result) bool
    pub fn isErr(self: Result) bool
    pub fn unwrap(self: Result) !Message
    pub fn unwrapErr(self: Result) AgentError
};
```

**Example:**
```zig
const result = try agent.process(msg);
if (result.isOk()) {
    var response = try result.unwrap();
    defer response.deinit();
    const text = try response.contentAsText();
    std.debug.print("Response: {s}\n", .{text});
} else {
    const err = result.unwrapErr();
    std.debug.print("Error: {}\n", .{err});
}
```

---

### Role

Message role enumeration.

```zig
pub const Role = enum {
    user,
    assistant,
    system,
    tool,

    pub fn toString(self: Role) []const u8
    pub fn fromString(str: []const u8) !Role
};
```

**Values:**
- `user`: Messages from the user
- `assistant`: Messages from the agent/assistant
- `system`: System-level instructions
- `tool`: Tool execution results

---

### AgentError

Error types for agent operations.

```zig
pub const AgentError = error{
    InvalidInput,
    ProcessingFailed,
    ResourceExhausted,
    NotImplemented,
    ConfigurationError,
    StateError,
};
```

---

## Message API

### Creating Messages

#### `Message.withText`
```zig
pub fn withText(allocator: std.mem.Allocator, role: Role, text: []const u8) !Message
```
Creates a text message.

**Parameters:**
- `allocator`: Memory allocator for the message
- `role`: Message role (.user, .assistant, .system, .tool)
- `text`: Text content (will be duplicated)

**Returns:** `!Message` - New message or error

**Example:**
```zig
var msg = try Message.withText(allocator, .user, "Hello!");
defer msg.deinit();
```

---

#### `Message.withStructured`
```zig
pub fn withStructured(allocator: std.mem.Allocator, role: Role, data: std.json.Value) !Message
```
Creates a structured message with JSON data.

**Parameters:**
- `allocator`: Memory allocator
- `role`: Message role
- `data`: JSON value (will be cloned)

**Returns:** `!Message`

**Example:**
```zig
const data = std.json.Value{ .object = std.json.ObjectMap.init(allocator) };
var msg = try Message.withStructured(allocator, .tool, data);
defer msg.deinit();
```

---

#### `Message.fromJson`
```zig
pub fn fromJson(allocator: std.mem.Allocator, value: std.json.Value) !Message
```
Deserializes a message from JSON.

**Parameters:**
- `allocator`: Memory allocator
- `value`: JSON object with "role", "content", "metadata" fields

**Returns:** `!Message`

**Example:**
```zig
const json_text =
    \\{
    \\  "role": "user",
    \\  "content": {"text": "Hello"},
    \\  "metadata": {}
    \\}
;
const parsed = try std.json.parseFromSlice(std.json.Value, allocator, json_text, .{});
defer parsed.deinit();

var msg = try Message.fromJson(allocator, parsed.value);
defer msg.deinit();
```

---

### Message Methods

#### `deinit`
```zig
pub fn deinit(self: *Message) void
```
Frees all resources owned by the message.

**Important:** Always call `deinit()` when done with a message to prevent memory leaks.

---

#### `contentAsText`
```zig
pub fn contentAsText(self: *const Message) ![]const u8
```
Gets the text content of the message.

**Returns:** `![]const u8` - Text content or error if not text

**Example:**
```zig
const text = try msg.contentAsText();
std.debug.print("Content: {s}\n", .{text});
```

---

#### `setMetadata`
```zig
pub fn setMetadata(self: *Message, key: []const u8, value: std.json.Value) !void
```
Sets a metadata key-value pair.

**Parameters:**
- `key`: Metadata key (will be duplicated)
- `value`: JSON value (will be cloned)

**Example:**
```zig
try msg.setMetadata("session_id", .{ .string = "abc-123" });
try msg.setMetadata("priority", .{ .integer = 5 });
```

---

#### `getMetadata`
```zig
pub fn getMetadata(self: *const Message, key: []const u8) ?std.json.Value
```
Gets a metadata value by key.

**Parameters:**
- `key`: Metadata key to lookup

**Returns:** `?std.json.Value` - Value if exists, null otherwise

**Example:**
```zig
if (msg.getMetadata("session_id")) |value| {
    if (value == .string) {
        std.debug.print("Session: {s}\n", .{value.string});
    }
}
```

---

#### `toJson`
```zig
pub fn toJson(self: *const Message, allocator: std.mem.Allocator) !std.json.Value
```
Serializes the message to JSON.

**Parameters:**
- `allocator`: Allocator for JSON object

**Returns:** `!std.json.Value` - JSON object

**Example:**
```zig
const json = try msg.toJson(allocator);
defer json.object.deinit();
```

---

## Agent API

### Agent Methods

#### `name`
```zig
pub fn name(self: Agent) []const u8
```
Returns the agent's name.

**Returns:** `[]const u8` - Agent name (caller does not own)

**Example:**
```zig
const agent_name = agent.name();
std.debug.print("Agent: {s}\n", .{agent_name});
```

---

#### `capabilities`
```zig
pub fn capabilities(self: Agent, allocator: std.mem.Allocator) ![]const []const u8
```
Returns a list of agent capabilities.

**Parameters:**
- `allocator`: Allocator for the capabilities list

**Returns:** `![]const []const u8` - Array of capability strings (caller owns)

**Example:**
```zig
const caps = try agent.capabilities(allocator);
defer allocator.free(caps);

for (caps) |cap| {
    std.debug.print("  - {s}\n", .{cap});
}
```

---

#### `process`
```zig
pub fn process(self: Agent, message: Message) !Result
```
Processes a message and returns a result.

**Parameters:**
- `message`: Input message to process

**Returns:** `!Result` - Processing result (ok with message or error)

**Example:**
```zig
const result = try agent.process(msg);
if (result.isOk()) {
    var response = try result.unwrap();
    defer response.deinit();
    // Use response...
} else {
    const err = result.unwrapErr();
    // Handle error...
}
```

---

#### `deinit`
```zig
pub fn deinit(self: Agent) void
```
Frees all resources owned by the agent.

**Example:**
```zig
var agent = try MyAgent.init(allocator);
defer agent.agent().deinit();
```

---

## Patterns

Agenkit-Zig provides 11 built-in agent patterns. All patterns follow the same Agent interface.

### Sequential

Sequential composition - agents process messages in order.

```zig
const sequential = @import("agenkit").patterns.sequential;

var seq = try sequential.SequentialAgent.init(allocator);
defer seq.agent().deinit();

try seq.addAgent(agent1.agent());
try seq.addAgent(agent2.agent());

const result = try seq.agent().process(msg);
```

**Use Cases:**
- Data transformation pipelines
- Multi-stage processing
- Validation → Processing → Formatting workflows

---

### Parallel

Parallel composition - agents process messages concurrently.

```zig
const parallel = @import("agenkit").patterns.parallel;

var par = try parallel.ParallelAgent.init(allocator);
defer par.agent().deinit();

try par.addAgent(agent1.agent());
try par.addAgent(agent2.agent());

const results = try par.processAll(msg);
defer allocator.free(results);
```

**Use Cases:**
- Concurrent data gathering
- Independent task execution
- Fan-out processing

---

### Reflection

Self-reflection pattern - agent evaluates and improves its output.

```zig
const reflection = @import("agenkit").patterns.reflection;

var refl = try reflection.ReflectionAgent.init(
    allocator,
    base_agent.agent(),
    3,  // max iterations
);
defer refl.agent().deinit();

const result = try refl.agent().process(msg);
```

**Use Cases:**
- Quality improvement
- Self-correction
- Iterative refinement

---

### React

Reasoning and Acting pattern - agent reasons before taking actions.

```zig
const react = @import("agenkit").patterns.react;

var react_agent = try react.ReactAgent.init(
    allocator,
    reasoner_agent.agent(),
    actor_agent.agent(),
);
defer react_agent.agent().deinit();

const result = try react_agent.agent().process(msg);
```

**Use Cases:**
- Decision-making systems
- Planning before execution
- Explainable AI

---

### Planning

Planning pattern - breaks complex tasks into steps.

```zig
const planning = @import("agenkit").patterns.planning;

var planner = try planning.PlanningAgent.init(
    allocator,
    executor_agent.agent(),
);
defer planner.agent().deinit();

const result = try planner.agent().process(msg);
```

**Use Cases:**
- Complex task decomposition
- Multi-step workflows
- Goal-oriented behavior

---

### Task

Task-based agent - manages and executes specific tasks.

```zig
const task = @import("agenkit").patterns.task;

var task_agent = try task.TaskAgent.init(
    allocator,
    "task-name",
);
defer task_agent.agent().deinit();

const result = try task_agent.agent().process(msg);
```

**Use Cases:**
- Job execution
- Specialized processing
- Single-responsibility agents

---

### Conversational

Conversational pattern - maintains dialogue context.

```zig
const conversational = @import("agenkit").patterns.conversational;

var conv = try conversational.ConversationalAgent.init(allocator);
defer conv.agent().deinit();

// Multi-turn conversation
const result1 = try conv.agent().process(msg1);
const result2 = try conv.agent().process(msg2);
```

**Use Cases:**
- Chatbots
- Interactive systems
- Context-aware responses

---

### Agents as Tools

Agents as tools pattern - agents can use other agents as tools.

```zig
const tools = @import("agenkit").patterns.agents_as_tools;

var main = try tools.ToolUsingAgent.init(allocator);
defer main.agent().deinit();

try main.registerTool("calculator", calculator_agent.agent());
try main.registerTool("search", search_agent.agent());

const result = try main.agent().process(msg);
```

**Use Cases:**
- Tool orchestration
- Agent delegation
- Capability composition

---

### Autonomous

Autonomous pattern - self-directed goal pursuit.

```zig
const autonomous = @import("agenkit").patterns.autonomous;

var auto = try autonomous.AutonomousAgent.init(
    allocator,
    "Complete the project",
    100,  // max steps
);
defer auto.deinit();

const result = try auto.run();
defer result.deinit();
```

**Use Cases:**
- Goal-driven systems
- Self-directed agents
- Long-running autonomous behavior

---

### Multiagent

Multiagent pattern - coordinate multiple agents.

```zig
const multiagent = @import("agenkit").patterns.multiagent;

var multi = try multiagent.MultiagentSystem.init(allocator);
defer multi.agent().deinit();

try multi.addAgent("agent1", agent1.agent());
try multi.addAgent("agent2", agent2.agent());

const result = try multi.coordinate(msg);
```

**Use Cases:**
- Multi-agent systems
- Distributed processing
- Agent collaboration

---

### Memory Hierarchy

Memory hierarchy pattern - working/short-term/long-term memory.

```zig
const memory = @import("agenkit").patterns.memory_hierarchy;

var mem = try memory.MemoryHierarchyAgent.init(
    allocator,
    base_agent.agent(),
);
defer mem.agent().deinit();

const result = try mem.agent().process(msg);
```

**Use Cases:**
- Contextual memory management
- Efficient context windows
- Long-term learning systems

---

## Memory Management

### Allocator Pattern

All operations requiring memory take an explicit `Allocator` parameter:

```zig
var gpa = std.heap.GeneralPurposeAllocator(.{}){};
defer _ = gpa.deinit();
const allocator = gpa.allocator();

var msg = try Message.withText(allocator, .user, "text");
defer msg.deinit();
```

### Cleanup Guidelines

1. **Always use defer** - Pair allocations with cleanup:
   ```zig
   var msg = try Message.withText(allocator, .user, "text");
   defer msg.deinit();
   ```

2. **Use errdefer for error paths** - Cleanup only on error:
   ```zig
   var msg = try Message.withText(allocator, .user, "text");
   errdefer msg.deinit();
   // More operations...
   return msg;  // Caller now owns
   ```

3. **No hidden allocations** - All allocations are explicit in function signatures

4. **Test for leaks** - Run `zig build test` to detect memory leaks:
   ```bash
   zig build test
   # Reports: "error(gpa): memory address 0x... leaked" if leaks found
   ```

### Ownership Rules

1. **Return values** - Caller owns and must free:
   ```zig
   const caps = try agent.capabilities(allocator);
   defer allocator.free(caps);
   ```

2. **Borrowed references** - Caller does not own:
   ```zig
   const name = agent.name();  // Don't free this
   ```

3. **Consumed values** - Function takes ownership:
   ```zig
   try seq.addAgent(agent.agent());  // Sequential now owns agent
   ```

---

## Error Handling

All fallible operations return error unions (`!T`):

```zig
const result: !Message = Message.withText(allocator, .user, "text");

// Handle with try
var msg = try result;

// Or explicit handling
var msg = result catch |err| {
    std.debug.print("Failed: {}\n", .{err});
    return err;
};
```

Common error patterns:
- `try` - Propagate errors up
- `catch |err|` - Handle errors locally
- `errdefer` - Cleanup on error paths

---

## Testing

### Example Test

```zig
test "Message creation and content" {
    const allocator = std.testing.allocator;

    var msg = try Message.withText(allocator, .user, "Hello!");
    defer msg.deinit();

    try std.testing.expectEqual(Role.user, msg.role);

    const text = try msg.contentAsText();
    try std.testing.expectEqualStrings("Hello!", text);
}
```

### Running Tests

```bash
# All tests
zig build test

# Verbose output
zig build test --summary all

# Specific file
zig test src/message.zig
```

---

## Cross-Language Compatibility

Agenkit-Zig maintains API parity with:
- Python (agenkit)
- Go (agenkit-go)
- TypeScript (@agenkit/core)
- C++ (agenkit-cpp)
- Rust (agenkit-rs)

### Message Structure (Universal)
```zig
{
  "role": "user|assistant|system|tool",
  "content": {"text": "..."} | {"structured": {...}},
  "metadata": {"key": "value", ...}
}
```

### Agent Interface (Universal)
- `name()` - Returns agent identifier
- `capabilities()` - Lists agent capabilities
- `process(message)` - Processes a message
- `deinit()` / `close()` / `destroy()` - Cleanup

---

## Performance Considerations

1. **Zero-cost abstractions** - Agent vtable compiles to direct function calls
2. **No hidden allocations** - All memory operations are explicit
3. **Compile-time guarantees** - Type safety without runtime overhead
4. **Efficient patterns** - Parallel pattern uses actual concurrency

### Optimization Tips

1. **Reuse allocators** - Don't create new allocators per operation
2. **Pre-allocate when possible** - Use `ArrayList.ensureTotalCapacity()`
3. **Profile with tracy** - Use `@import("tracy")` for performance analysis
4. **Batch operations** - Process multiple messages together when possible

---

## Version Information

**API Version:** 0.41.0
**Zig Version:** ≥ 0.15.2
**Stability:** Production-ready

### Breaking Changes from 0.39.0

- None - v0.41.0 is backward compatible with v0.39.0

---

## See Also

- [Getting Started Guide](GETTING_STARTED.md) - Installation and first agent
- [Patterns Guide](PATTERNS.md) - Deep dive into agent patterns
- [Migration Guide](MIGRATION.md) - Porting from other languages
- [Main README](../README.md) - Project overview
