# Zig API Reference

**Import:** `const agenkit = @import("agenkit");`
**Zig:** 0.13+
**Build system:** `build.zig` + `build.zig.zon`

---

## Build Integration

Add agenkit as a dependency in `build.zig.zon`:

```zig
.dependencies = .{
    .agenkit = .{
        .url = "https://github.com/scttfrdmn/agenkit/archive/main.tar.gz",
    },
},
```

Then in `build.zig`:

```zig
const agenkit_dep = b.dependency("agenkit", .{ .target = target, .optimize = optimize });
exe.root_module.addImport("agenkit", agenkit_dep.module("agenkit"));
```

---

## Core Types

**File:** `src/message.zig`, `src/agent.zig`

### `Message`

```zig
pub const Message = struct {
    role:     []const u8,
    content:  []const u8,
    metadata: std.StringHashMap([]const u8),

    pub fn init(allocator: std.mem.Allocator, role: []const u8, content: []const u8) !Message;
    pub fn deinit(self: *Message) void;
    pub fn setMetadata(self: *Message, key: []const u8, value: []const u8) !void;
    pub fn getMetadata(self: *const Message, key: []const u8) ?[]const u8;
};
```

### `Agent` (comptime interface)

Agenkit uses a comptime duck-typed interface rather than a vtable. Any struct that provides a `process` method conforming to the following signature is a valid agent:

```zig
pub fn process(self: *Self, message: Message) anyerror!Message;
pub fn name(self: *const Self) []const u8;
pub fn capabilities(self: *const Self) [][]const u8;
```

The `agenkit.agent` module provides `validateAgent(comptime T: type)` — a comptime check that emits a descriptive compile error if a type does not satisfy the interface.

```zig
pub fn validateAgent(comptime T: type) void;
```

### `AgentError`

```zig
pub const AgentError = error{
    AdapterFailure,
    Timeout,
    CircuitOpen,
    BudgetExceeded,
    CheckpointFailure,
    InvalidMessage,
    NotImplemented,
};
```

### `Tool`

```zig
pub const Tool = struct {
    name:        []const u8,
    description: []const u8,
    executeFn:   *const fn (args: std.json.Value, allocator: std.mem.Allocator) anyerror!std.json.Value,
};
```

---

## LLM Adapters

**Module:** `agenkit.adapter`

### Anthropic

```zig
const anthropic = agenkit.adapter.anthropic;

pub const Config = struct {
    model:       []const u8 = "claude-sonnet-4-6",
    api_key:     []const u8,          // or ANTHROPIC_API_KEY env var
    max_tokens:  u32        = 4096,
    temperature: f32        = 1.0,
};

pub const Client = struct {
    pub fn init(allocator: std.mem.Allocator, config: Config) !Client;
    pub fn deinit(self: *Client) void;
    pub fn process(self: *Client, message: Message) anyerror!Message;
    pub fn name(self: *const Client) []const u8;
    pub fn capabilities(self: *const Client) [][]const u8;
};
```

### OpenAI

```zig
const openai = agenkit.adapter.openai;

pub const Config = struct {
    model:       []const u8 = "gpt-4o",
    api_key:     []const u8,          // or OPENAI_API_KEY env var
    max_tokens:  u32        = 4096,
    temperature: f32        = 0.7,
};

pub const Client = struct {
    pub fn init(allocator: std.mem.Allocator, config: Config) !Client;
    pub fn deinit(self: *Client) void;
    pub fn process(self: *Client, message: Message) anyerror!Message;
    pub fn name(self: *const Client) []const u8;
};
```

### Additional Adapters

| Module | Notes |
|--------|-------|
| `agenkit.adapter.bedrock` | AWS Bedrock |
| `agenkit.adapter.gemini` | Google Gemini |
| `agenkit.adapter.ollama` | Local Ollama |
| `agenkit.adapter.litellm` | LiteLLM proxy |
| `agenkit.adapter.openai_compatible` | Any OpenAI-compatible endpoint |

---

## Patterns

**Module:** `agenkit.patterns`

All pattern structs provide `init`, `deinit`, `process`, `name`, and `capabilities`.

| Struct | Key Init Parameters |
|--------|---------------------|
| `ReflectionAgent(T)` | `agent: *T`, `max_iterations: u32 = 3` |
| `ReactAgent(T)` | `agent: *T`, `tools: []Tool` |
| `AgentsAsToolsAgent(T)` | `agent: *T`, sub-agent slice |
| `OrchestrationAgent(O, W)` | `orchestrator: *O`, `workers: []W` |
| `ReasoningWithToolsAgent(T)` | `agent: *T`, `tools: []Tool`, `max_steps: u32` |
| `ConversationalAgent(T)` | `agent: *T`, optional `memory` |
| `TaskAgent(T)` | `agent: *T`, `task: []const u8` |
| `MultiagentAgent` | slice of type-erased agents |
| `PlanningAgent(P, E)` | `planner: *P`, `executor: *E` |
| `AutonomousAgent(T)` | `agent: *T`, `max_iterations: u32` |
| `SequentialAgent` | slice of type-erased agents |
| `ParallelAgent` | slice of type-erased agents |
| `RouterAgent(R)` | `router: *R`, route map |
| `FallbackAgent(P)` | `primary: *P`, fallback slice |
| `CollaborativeAgent(C)` | `coordinator: *C`, agent slice |
| `HumanInLoopAgent(T)` | `agent: *T`, approval callback |
| `SupervisorAgent(S)` | `supervisor: *S`, worker slice |
| `WorkingMemoryAgent(T)` | `agent: *T`, `memory: *Memory` |

Pattern structs are generic over the underlying agent type(s) — the comptime parameter avoids vtable overhead while preserving type safety.

---

## Middleware

**Module:** `agenkit.middleware`

| Struct | Key Init Parameters |
|--------|---------------------|
| `RetryMiddleware(T)` | `agent: *T`, `max_attempts: u32 = 3`, `backoff_base_ms: u64 = 1000` |
| `TimeoutMiddleware(T)` | `agent: *T`, `timeout_ms: u64` |
| `RateLimiter(T)` | `agent: *T`, `requests_per_second: f32`, `burst: u32` |
| `CircuitBreaker(T)` | `agent: *T`, `failure_threshold: u32 = 5`, `recovery_timeout_ms: u64 = 60000` |
| `CachingMiddleware(T)` | `agent: *T`, `ttl_ms: u64 = 0` |
| `BatchingMiddleware(T)` | `agent: *T`, `max_batch_size: u32 = 10`, `max_wait_ms: u64 = 100` |
| `PerUserRateLimiter(T)` | `agent: *T`, per-user config |

---

## Memory

**Module:** `agenkit.memory` (via `agenkit.patterns.memory`)

```zig
pub const Memory = struct {
    pub fn init(allocator: std.mem.Allocator, max_messages: ?u32) !Memory;
    pub fn deinit(self: *Memory) void;
    pub fn add(self: *Memory, message: Message) !void;
    pub fn history(self: *const Memory) []const Message;
    pub fn clear(self: *Memory) void;
};
```

---

## Evaluation Framework

**Module:** `agenkit.evaluation`

The Zig implementation includes a full evaluation framework for prompt and agent optimization.

### `Optimizer`

```zig
pub const Optimizer = struct {
    pub fn init(allocator: std.mem.Allocator, config: OptimizerConfig) !Optimizer;
    pub fn optimize(self: *Optimizer, agent: anytype, dataset: []EvalSample) !OptimizationResult;
};

pub const OptimizerConfig = struct {
    max_iterations:   u32   = 100,
    learning_rate:    f32   = 0.01,
    convergence_eps:  f32   = 1e-4,
};
```

### `ABTesting`

```zig
pub const ABTesting = struct {
    pub fn init(allocator: std.mem.Allocator, config: ABConfig) !ABTesting;
    pub fn addVariant(self: *ABTesting, name: []const u8, agent: anytype) !void;
    pub fn run(self: *ABTesting, samples: []EvalSample) !ABResult;
};
```

### `Benchmarks`

```zig
pub const Benchmarks = struct {
    pub fn init(allocator: std.mem.Allocator) !Benchmarks;
    pub fn add(self: *Benchmarks, name: []const u8, agent: anytype) !void;
    pub fn run(self: *Benchmarks, iterations: u32) !BenchmarkResult;
    pub fn report(self: *const Benchmarks, writer: anytype) !void;
};
```

### `BayesianOptimizer`

```zig
pub const BayesianOptimizer = struct {
    pub fn init(allocator: std.mem.Allocator, config: BayesianConfig) !BayesianOptimizer;
    pub fn suggest(self: *BayesianOptimizer) !ParameterSet;
    pub fn observe(self: *BayesianOptimizer, params: ParameterSet, score: f64) !void;
    pub fn bestParams(self: *const BayesianOptimizer) ParameterSet;
};
```

---

## Safety

**Module:** `agenkit.safety`

```zig
pub const SafetyConfig = struct {
    allow_network:    bool = false,
    allow_filesystem: bool = false,
    allowed_paths:    [][]const u8 = &.{},
    denied_paths:     [][]const u8 = &.{},
};

pub const SafetyFilter = struct {
    pub fn init(allocator: std.mem.Allocator, config: SafetyConfig) !SafetyFilter;
    pub fn wrap(self: *SafetyFilter, agent: anytype) SafetyFilteredAgent(@TypeOf(agent));
};
```

---

## Introspection

**File:** `src/introspection.zig`

```zig
pub const IntrospectionResult = struct {
    name:         []const u8,
    agent_type:   []const u8,
    capabilities: [][]const u8,
    sub_agents:   []IntrospectionResult,
};

pub fn introspect(agent: anytype) IntrospectionResult;
```

`introspect` is a comptime function — it resolves agent structure at compile time with no runtime overhead.
