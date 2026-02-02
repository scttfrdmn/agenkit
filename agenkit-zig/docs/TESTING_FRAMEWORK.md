# Zig Testing Framework

## Current State

The Zig implementation has **442 tests across 82 modules** with solid coverage. Basic mock agents (`MockAgent` and `FailingMockAgent`) are available in `src/test_utils.zig`.

**Test Coverage:**
- ✅ Core agent interface: 15+ tests
- ✅ Message handling: 20+ tests
- ✅ Patterns (Sequential, Parallel, Reflection, etc.): 180+ tests
- ✅ LLM Adapters: 50+ tests
- ✅ Middleware (Retry, Circuit Breaker, etc.): 60+ tests
- ✅ Observability: 40+ tests
- ✅ Infrastructure: 50+ tests
- ✅ Techniques (Graph of Thought, etc.): 27+ tests

## Available Test Utilities

### Mock Agents (`src/test_utils.zig`)

**MockAgent** - Cycles through predefined responses:
```zig
var mock = try MockAgent.init(allocator, &[_][]const u8{
    "Response 1",
    "Response 2",
});
defer mock.deinit();

const agent = mock.agent();
const result = try agent.process(message);
// First call returns "Response 1"
// Second call returns "Response 2"
// Third call returns "Response 1" (cycles)

// Track calls
try testing.expectEqual(@as(usize, 1), mock.getCallCount());
mock.resetCallCount();
```

**FailingMockAgent** - Always returns specified error:
```zig
var failing = try FailingMockAgent.init(allocator, AgentError.ProcessingFailed);
defer failing.deinit();

const agent = failing.agent();
const result = try agent.process(message);
try testing.expectEqual(AgentError.ProcessingFailed, result.err);
```

## Identified Patterns and Opportunities

Based on analysis of 442 tests, the following patterns occur frequently:

### 1. Message Creation (80+ occurrences)

**Current Pattern:**
```zig
var msg = try Message.withText(allocator, .user, "Test content");
defer msg.deinit();
```

**Opportunity:** Message builder with automatic cleanup tracking (15-20% code reduction in tests)

### 2. Config + Decorator Setup (30+ occurrences)

**Current Pattern:**
```zig
var config = RetryConfig{
    .max_retries = 3,
    .initial_delay_ms = 100,
    .max_delay_ms = 10000,
    .multiplier = 2.0,
};
var retry = try RetryDecorator.init(allocator, base_agent, config);
defer retry.deinit();
```

**Opportunity:** Builder pattern for common config types

### 3. HashMap/ArrayList Initialization (100+ occurrences)

**Current Pattern:**
```zig
var map = std.StringHashMap(T).init(allocator);
defer map.deinit();
try map.put("key", value);
```

**Opportunity:** Fixture wrappers with automatic cleanup

### 4. Custom Assertions (150+ potential uses)

**Current Pattern:**
```zig
try testing.expectEqualStrings("expected", result.ok.content.string);
```

**Opportunity:** Assertions with context and better error messages

## Recommended Test Utilities

### Priority 1: High Impact (15+ test occurrences each)

#### 1.1 Message Builder
```zig
pub const MessageBuilder = struct {
    allocator: Allocator,
    messages: std.ArrayList(Message),

    pub fn init(allocator: Allocator) MessageBuilder;
    pub fn deinit(self: *MessageBuilder) void;
    pub fn user(self: *MessageBuilder, content: []const u8) !Message;
    pub fn assistant(self: *MessageBuilder, content: []const u8) !Message;
    pub fn system(self: *MessageBuilder, content: []const u8) !Message;
    pub fn tool(self: *MessageBuilder, content: []const u8) !Message;
};
```

**Impact:** Eliminates 80+ repetitions, auto cleanup, cleaner test code

#### 1.2 Config Builders
```zig
pub fn retryConfigBuilder() RetryConfigBuilder;
pub fn circuitBreakerConfigBuilder() CircuitBreakerConfigBuilder;
pub fn timeoutConfigBuilder() TimeoutConfigBuilder;

// Usage:
const config = retryConfigBuilder()
    .maxAttempts(5)
    .initialBackoff(100)
    .build();
```

**Impact:** Eliminates 30+ repetitions, more readable test setup

#### 1.3 Custom Assertion Helpers
```zig
pub fn assertContains(allocator: Allocator, haystack: []const u8, needle: []const u8, context: []const u8) !void;
pub fn assertApproxEqual(comptime T: type, expected: T, actual: T, tolerance: T, context: []const u8) !void;
pub fn assertSliceContains(comptime T: type, slice: []const T, expected: T, context: []const u8) !void;
pub fn assertMetricsEqual(allocator: Allocator, snapshot: MetricsSnapshot, checks: []const MetricCheck) !void;
```

**Impact:** Adds ~150 missing assertions with helpful error messages

#### 1.4 Collection Fixtures
```zig
pub fn HashMapFixture(comptime V: type) type;
pub fn ArrayListFixture(comptime T: type) type;

// Usage:
var map = try HashMapFixture([]const u8).init(allocator);
defer map.deinit();
try map.put("key", "value");
```

**Impact:** Eliminates 100+ repetitions, automatic cleanup

### Priority 2: Medium Impact (5-15 test occurrences)

#### 2.1 Metrics Assertion Helpers
```zig
pub const MetricCheck = struct {
    name: []const u8,
    expected: u64,
};

pub fn assertMetricsEqual(allocator: Allocator, snapshot: MetricsSnapshot, checks: []const MetricCheck) !void;
```

**Usage:**
```zig
try assertMetricsEqual(allocator, snapshot, &[_]MetricCheck{
    .{ .name = "total_attempts", .expected = 10 },
    .{ .name = "successful_first_attempt", .expected = 5 },
});
```

#### 2.2 Mock Agent Call Tracking Helpers
```zig
pub const MockAgentTracker = struct {
    pub fn expectCallCount(self: *MockAgentTracker, expected: usize) !void;
    pub fn expectCallSequence(self: *MockAgentTracker, expected_inputs: []const []const u8) !void;
    pub fn getCallHistory(self: *MockAgentTracker) []const Message;
};
```

#### 2.3 Common Error Scenario Builders
```zig
pub fn timeoutScenario(allocator: Allocator, agent: Agent, timeout_ms: u64) !void;
pub fn retryScenario(allocator: Allocator, agent: Agent, max_retries: usize) !void;
pub fn circuitBreakerScenario(allocator: Allocator, agent: Agent, failure_threshold: usize) !void;
```

### Priority 3: Low Impact (1-5 test occurrences)

#### 3.1 Thread-safe Test Utilities
```zig
pub const ThreadSafeTestHelper = struct {
    pub fn withMutex(comptime T: type, value: T) !*MutexGuarded(T);
    pub fn assertThreadSafe(fn_to_test: anytype, num_threads: usize) !void;
};
```

#### 3.2 Timeout Test Wrappers
```zig
pub fn withTimeout(comptime T: type, fn_to_test: anytype, timeout_ms: u64) !T;
```

#### 3.3 Parameterized Test Support
```zig
pub fn parameterizedTest(
    test_fn: anytype,
    params: []const Param,
) !void;

// Usage:
try parameterizedTest(testRetryLogic, &[_]Param{
    .{ .name = "3 retries", .max_retries = 3 },
    .{ .name = "5 retries", .max_retries = 5 },
});
```

## Implementation Notes

### Zig 0.15.2 API Considerations

When implementing these utilities, note the following API patterns:

1. **ArrayList Usage:**
   ```zig
   var list = std.ArrayList(T).init(allocator);
   defer list.deinit();
   try list.append(item);  // Takes only item, not allocator
   ```

2. **Agent VTable:**
   ```zig
   pub const VTable = struct {
       name: *const fn (ptr: *anyopaque) []const u8,
       capabilities: *const fn (ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const []const u8,
       process: *const fn (ptr: *anyopaque, message: Message) AgentError!Result,
       process_stream: *const fn (ptr: *anyopaque, message: Message, callbacks: StreamCallbacks) AgentError!void,
       introspect: *const fn (ptr: *anyopaque, allocator: Allocator) Allocator.Error!IntrospectionResult,
       deinit: *const fn (ptr: *anyopaque) void,
   };
   ```

3. **Result Type:**
   ```zig
   pub const Result = union(enum) {
       ok: Message,
       err: AgentError,
   };
   ```

4. **Content Access:**
   ```zig
   // Message content is a union, not always .string
   switch (message.content) {
       .string => |text| // Handle string content
       .tool => |tool_result| // Handle tool content
   }
   ```

### Testing the Test Utilities

All test utilities should include comprehensive tests:

```zig
test "MessageBuilder creates messages with auto cleanup" { ... }
test "MockAgent cycles through responses" { ... }
test "assertContains succeeds when substring found" { ... }
test "assertApproxEqual fails for distant values" { ... }
```

## Estimated Impact

Implementing Priority 1 utilities would reduce test boilerplate by approximately:
- **2,000-3,000 lines** of test code (15-20% of all test code)
- **80+ Message creation patterns** → 1 builder pattern
- **30+ Config creation patterns** → Builder functions
- **100+ Collection patterns** → Fixture types
- **150+ Basic assertions** → Custom assertions with context

## Related Issues

- #436 - Mock LLMs for C++ and Zig (COMPLETED for Zig)
- #437 - Comprehensive Zig testing framework (THIS DOCUMENT)
- #438 - Cross-language API consistency tests

## Status

- ✅ MockAgent and FailingMockAgent implemented
- ✅ Comprehensive test coverage analysis complete
- ⏳ Additional fixtures documented, ready for implementation
- ⏳ Builder patterns documented, ready for implementation
- ⏳ Custom assertions documented, ready for implementation

## Next Steps

1. Implement Priority 1 utilities (MessageBuilder, Config Builders, Custom Assertions)
2. Add comprehensive tests for each new utility
3. Refactor existing tests to use new utilities (optional, gradual migration)
4. Implement Priority 2 utilities as needed
5. Document patterns in codebase for consistent usage
