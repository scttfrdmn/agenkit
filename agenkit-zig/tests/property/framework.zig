/// Property-based testing framework for Agenkit Zig
///
/// Since the Zig ecosystem lacks a mature property-based testing library,
/// this module provides a lightweight custom framework built on std.Random.DefaultPrng.
///
/// Design:
/// - runProperty runs a property function N times with a shared advancing PRNG
/// - Each iteration sees different random values (PRNG state advances)
/// - No external dependencies required
/// - Deterministic given a seed (good for reproducing failures)
///
/// Usage:
/// ```zig
/// test "my property" {
///     const allocator = std.testing.allocator;
///     try framework.runProperty("name", 50, 42, allocator, myProperty);
/// }
///
/// fn myProperty(rng: std.Random, allocator: std.mem.Allocator) !void {
///     const n = rng.intRangeAtMost(u32, 1, 100);
///     // ... test some invariant using n
/// }
/// ```

const std = @import("std");
const agenkit = @import("agenkit");
const Agent = agenkit.Agent;
const AgentError = agenkit.AgentError;
const Message = agenkit.Message;
const Role = agenkit.Role;
const Result = agenkit.Result;
const StreamCallbacks = agenkit.StreamCallbacks;
const IntrospectionResult = agenkit.IntrospectionResult;
const createDefaultIntrospectionResult = agenkit.createDefaultIntrospectionResult;
const Allocator = std.mem.Allocator;

/// Run a property function N times with a shared advancing PRNG.
/// Each iteration gets the same std.Random interface but PRNG state advances,
/// so each call to rng.int() etc. produces fresh values.
pub fn runProperty(
    name: []const u8,
    iterations: u32,
    seed: u64,
    allocator: Allocator,
    prop_fn: *const fn (std.Random, Allocator) anyerror!void,
) !void {
    _ = name; // name is for documentation / error messages only
    var prng = std.Random.DefaultPrng.init(seed);
    const rng = prng.random();
    var i: u32 = 0;
    while (i < iterations) : (i += 1) {
        try prop_fn(rng, allocator);
    }
}

/// Return a random Role enum value
pub fn randomRole(rng: std.Random) Role {
    const index = rng.intRangeAtMost(u8, 0, 4);
    return switch (index) {
        0 => .user,
        1 => .assistant,
        2 => .system,
        3 => .tool,
        else => .agent,
    };
}

/// Generate a random ASCII text string of length 0..max_len
pub fn randomText(rng: std.Random, allocator: Allocator, max_len: usize) ![]u8 {
    const len = rng.intRangeAtMost(usize, 0, max_len);
    const buf = try allocator.alloc(u8, len);
    for (buf) |*b| {
        // Generate printable ASCII (0x20 .. 0x7e)
        b.* = rng.intRangeAtMost(u8, 0x20, 0x7e);
    }
    return buf;
}

/// FailingAgent — always returns ProcessingFailed, never sleeps
pub const FailingAgent = struct {
    allocator: Allocator,

    pub fn init(allocator: Allocator) !*FailingAgent {
        const self = try allocator.create(FailingAgent);
        self.* = FailingAgent{ .allocator = allocator };
        return self;
    }

    pub fn agent(self: *FailingAgent) Agent {
        return Agent{
            .ptr = self,
            .vtable = &vtable,
        };
    }

    pub fn deinit(self: *FailingAgent) void {
        self.allocator.destroy(self);
    }

    const vtable = Agent.VTable{
        .name = nameImpl,
        .capabilities = capabilitiesImpl,
        .process = processImpl,
        .process_stream = processStreamImpl,
        .introspect = introspectImpl,
        .deinit = deinitVtable,
    };

    fn nameImpl(ptr: *anyopaque) []const u8 {
        _ = ptr;
        return "failing-agent";
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const []const u8 {
        _ = ptr;
        return allocator.alloc([]const u8, 0);
    }

    fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
        _ = ptr;
        _ = message;
        return Result{ .err = AgentError.ProcessingFailed };
    }

    fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: StreamCallbacks) AgentError!void {
        _ = ptr;
        _ = message;
        callbacks.onError(AgentError.NotImplemented);
    }

    fn introspectImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error!IntrospectionResult {
        _ = ptr;
        const caps = try allocator.alloc([]const u8, 0);
        defer allocator.free(caps);
        return createDefaultIntrospectionResult(allocator, "failing-agent", caps);
    }

    fn deinitVtable(ptr: *anyopaque) void {
        const self: *FailingAgent = @ptrCast(@alignCast(ptr));
        self.allocator.destroy(self);
    }
};

/// CountingFailingAgent — counts process() calls AND always returns ProcessingFailed
pub const CountingFailingAgent = struct {
    allocator: Allocator,
    call_count: usize,

    pub fn init(allocator: Allocator) !*CountingFailingAgent {
        const self = try allocator.create(CountingFailingAgent);
        self.* = CountingFailingAgent{
            .allocator = allocator,
            .call_count = 0,
        };
        return self;
    }

    pub fn agent(self: *CountingFailingAgent) Agent {
        return Agent{
            .ptr = self,
            .vtable = &vtable,
        };
    }

    pub fn deinit(self: *CountingFailingAgent) void {
        self.allocator.destroy(self);
    }

    const vtable = Agent.VTable{
        .name = nameImpl,
        .capabilities = capabilitiesImpl,
        .process = processImpl,
        .process_stream = processStreamImpl,
        .introspect = introspectImpl,
        .deinit = deinitVtable,
    };

    fn nameImpl(ptr: *anyopaque) []const u8 {
        _ = ptr;
        return "counting-failing-agent";
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const []const u8 {
        _ = ptr;
        return allocator.alloc([]const u8, 0);
    }

    fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
        _ = message;
        const self: *CountingFailingAgent = @ptrCast(@alignCast(ptr));
        self.call_count += 1;
        return Result{ .err = AgentError.ProcessingFailed };
    }

    fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: StreamCallbacks) AgentError!void {
        _ = ptr;
        _ = message;
        callbacks.onError(AgentError.NotImplemented);
    }

    fn introspectImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error!IntrospectionResult {
        _ = ptr;
        const caps = try allocator.alloc([]const u8, 0);
        defer allocator.free(caps);
        return createDefaultIntrospectionResult(allocator, "counting-failing-agent", caps);
    }

    fn deinitVtable(ptr: *anyopaque) void {
        const self: *CountingFailingAgent = @ptrCast(@alignCast(ptr));
        self.allocator.destroy(self);
    }
};

/// CountingEchoAgent — counts process() calls AND echoes input as assistant
pub const CountingEchoAgent = struct {
    allocator: Allocator,
    call_count: usize,

    pub fn init(allocator: Allocator) !*CountingEchoAgent {
        const self = try allocator.create(CountingEchoAgent);
        self.* = CountingEchoAgent{
            .allocator = allocator,
            .call_count = 0,
        };
        return self;
    }

    pub fn agent(self: *CountingEchoAgent) Agent {
        return Agent{
            .ptr = self,
            .vtable = &vtable,
        };
    }

    pub fn deinit(self: *CountingEchoAgent) void {
        self.allocator.destroy(self);
    }

    const vtable = Agent.VTable{
        .name = nameImpl,
        .capabilities = capabilitiesImpl,
        .process = processImpl,
        .process_stream = processStreamImpl,
        .introspect = introspectImpl,
        .deinit = deinitVtable,
    };

    fn nameImpl(ptr: *anyopaque) []const u8 {
        _ = ptr;
        return "counting-echo-agent";
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const []const u8 {
        _ = ptr;
        return allocator.alloc([]const u8, 0);
    }

    fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
        const self: *CountingEchoAgent = @ptrCast(@alignCast(ptr));
        self.call_count += 1;

        const text = message.contentAsText() catch {
            return Result{ .err = AgentError.InvalidInput };
        };
        var response = Message.withText(self.allocator, .assistant, text) catch {
            return Result{ .err = AgentError.ProcessingFailed };
        };
        _ = &response;
        return Result{ .ok = response };
    }

    fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: StreamCallbacks) AgentError!void {
        _ = ptr;
        _ = message;
        callbacks.onError(AgentError.NotImplemented);
    }

    fn introspectImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error!IntrospectionResult {
        _ = ptr;
        const caps = try allocator.alloc([]const u8, 0);
        defer allocator.free(caps);
        return createDefaultIntrospectionResult(allocator, "counting-echo-agent", caps);
    }

    fn deinitVtable(ptr: *anyopaque) void {
        const self: *CountingEchoAgent = @ptrCast(@alignCast(ptr));
        self.allocator.destroy(self);
    }
};
