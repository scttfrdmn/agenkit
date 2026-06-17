/// Pattern Performance Benchmarks
///
/// Measures framework overhead for agent patterns using mock agents
/// to isolate pattern logic from LLM latency.

const std = @import("std");
const agenkit = @import("agenkit");
const Agent = agenkit.Agent;
const StreamCallbacks = agenkit.StreamCallbacks;
const AgentError = agenkit.AgentError;
const Result = agenkit.Result;
const Message = agenkit.Message;

/// Simple echo agent for benchmarking
pub const EchoAgent = struct {
    allocator: std.mem.Allocator,
    agent_name: []const u8,

    pub fn init(allocator: std.mem.Allocator, name: []const u8) !*EchoAgent {
        const self = try allocator.create(EchoAgent);
        self.* = EchoAgent{
            .allocator = allocator,
            .agent_name = name,
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
                .process_stream = processStreamImpl,
                .introspect = introspectImpl,
                .deinit = deinitImpl,
            },
        };
    }

    fn nameImpl(ptr: *anyopaque) []const u8 {
        const self: *EchoAgent = @ptrCast(@alignCast(ptr));
        return self.agent_name;
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: std.mem.Allocator) std.mem.Allocator.Error![]const []const u8 {
        _ = ptr;
        const caps = try allocator.alloc([]const u8, 1);
        caps[0] = "echo";
        return caps;
    }

    fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
        const self: *EchoAgent = @ptrCast(@alignCast(ptr));
        const content = message.contentAsText() catch "echo";
        const response = Message.withText(self.allocator, .assistant, content) catch {
            return AgentError.ProcessingFailed;
        };
        return Result{ .ok = response };
    }

    fn introspectImpl(ptr: *anyopaque, allocator: std.mem.Allocator) std.mem.Allocator.Error!agenkit.IntrospectionResult {
        const self: *EchoAgent = @ptrCast(@alignCast(ptr));
        const caps = try capabilitiesImpl(ptr, allocator);
        defer allocator.free(caps);
        return agenkit.createDefaultIntrospectionResult(allocator, self.agent_name, caps);
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *EchoAgent = @ptrCast(@alignCast(ptr));
        self.allocator.destroy(self);
    }
};

/// Benchmark result
pub const BenchmarkResult = struct {
    name: []const u8,
    iterations: usize,
    total_ns: u64,
    avg_us: f64,
    ops_per_sec: f64,
};

/// Run benchmark
pub fn benchmark(
    allocator: std.mem.Allocator,
    name: []const u8,
    iterations: usize,
    comptime func: fn (allocator: std.mem.Allocator) anyerror!void,
) !BenchmarkResult {
    // Warmup
    var i: usize = 0;
    while (i < 10) : (i += 1) {
        try func(allocator);
    }

    // Benchmark
    const start = std.time.nanoTimestamp();
    i = 0;
    while (i < iterations) : (i += 1) {
        try func(allocator);
    }
    const end = std.time.nanoTimestamp();
    const total_ns: u64 = @intCast(end - start);

    const avg_us = @as(f64, @floatFromInt(total_ns)) / @as(f64, @floatFromInt(iterations)) / 1000.0;
    const ops_per_sec = @as(f64, @floatFromInt(iterations)) / (@as(f64, @floatFromInt(total_ns)) / 1_000_000_000.0);

    return BenchmarkResult{
        .name = name,
        .iterations = iterations,
        .total_ns = total_ns,
        .avg_us = avg_us,
        .ops_per_sec = ops_per_sec,
    };
}

/// Sequential pattern benchmark
fn benchSequential(allocator: std.mem.Allocator) !void {
    var agent1 = try EchoAgent.init(allocator, "agent1");
    defer agent1.allocator.destroy(agent1);
    var agent2 = try EchoAgent.init(allocator, "agent2");
    defer agent2.allocator.destroy(agent2);
    var agent3 = try EchoAgent.init(allocator, "agent3");
    defer agent3.allocator.destroy(agent3);

    const agents = [_]Agent{ agent1.agent(), agent2.agent(), agent3.agent() };
    var seq = try agenkit.patterns.SequentialAgent.init(allocator, &agents, "sequential");
    defer seq.agent().deinit();

    const msg = try Message.withText(allocator, .user, "test");
    const result = try seq.agent().process(msg);
    _ = result; // Result is owned by the pattern, don't deinit
}

/// Parallel pattern benchmark
fn benchParallel(allocator: std.mem.Allocator) !void {
    var agent1 = try EchoAgent.init(allocator, "agent1");
    defer agent1.allocator.destroy(agent1);
    var agent2 = try EchoAgent.init(allocator, "agent2");
    defer agent2.allocator.destroy(agent2);
    var agent3 = try EchoAgent.init(allocator, "agent3");
    defer agent3.allocator.destroy(agent3);

    const agents = [_]Agent{ agent1.agent(), agent2.agent(), agent3.agent() };
    var parallel = try agenkit.patterns.ParallelAgent.init(
        allocator,
        &agents,
        "parallel",
        agenkit.patterns.defaultAggregator,
    );
    defer parallel.agent().deinit();

    const msg = try Message.withText(allocator, .user, "test");
    const result = try parallel.agent().process(msg);
    _ = result; // Result is owned by the pattern, don't deinit
}

/// Reflection pattern benchmark
fn benchReflection(allocator: std.mem.Allocator) !void {
    var generator = try EchoAgent.init(allocator, "generator");
    defer generator.allocator.destroy(generator);
    var critic = try EchoAgent.init(allocator, "critic");
    defer critic.allocator.destroy(critic);

    var reflection = try agenkit.patterns.ReflectionAgent.init(
        allocator,
        generator.agent(),
        critic.agent(),
        2, // max_iterations
        0.9, // quality_threshold
        0.05, // improvement_threshold
        .structured, // critique_format
        false, // verbose
    );
    defer reflection.agent().deinit();

    const msg = try Message.withText(allocator, .user, "test");
    const result = try reflection.agent().process(msg);
    _ = result; // Result is owned by the pattern, don't deinit
}

/// Fallback pattern benchmark
fn benchFallback(allocator: std.mem.Allocator) !void {
    var agent1 = try EchoAgent.init(allocator, "agent1");
    defer agent1.allocator.destroy(agent1);
    var agent2 = try EchoAgent.init(allocator, "agent2");
    defer agent2.allocator.destroy(agent2);

    const agents = [_]Agent{ agent1.agent(), agent2.agent() };
    var fallback = try agenkit.patterns.FallbackAgent.init(allocator, &agents, "fallback");
    defer fallback.agent().deinit();

    const msg = try Message.withText(allocator, .user, "test");
    const result = try fallback.agent().process(msg);
    _ = result; // Result is owned by the pattern, don't deinit
}


fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: StreamCallbacks) AgentError!void {
    _ = ptr;
    _ = message;
    callbacks.onError(AgentError.NotImplemented);
}
pub fn main() !void {
    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("=== Agenkit Pattern Benchmarks (Zig) ===\n\n", .{});
    std.debug.print("{s:<30} {s:>10}        {s:>10}\n", .{ "Pattern", "Time", "Throughput" });
    std.debug.print("{s}\n", .{"-" ** 60});

    const iterations: usize = 1000;

    // Sequential
    {
        const result = try benchmark(allocator, "Sequential", iterations, benchSequential);
        std.debug.print("{s:<30} {d:>10.0} μs/op  {d:>10.0} ops/s\n", .{
            result.name,
            result.avg_us,
            result.ops_per_sec,
        });
    }

    // Parallel
    {
        const result = try benchmark(allocator, "Parallel", iterations, benchParallel);
        std.debug.print("{s:<30} {d:>10.0} μs/op  {d:>10.0} ops/s\n", .{
            result.name,
            result.avg_us,
            result.ops_per_sec,
        });
    }

    // Reflection
    {
        const result = try benchmark(allocator, "Reflection", iterations, benchReflection);
        std.debug.print("{s:<30} {d:>10.0} μs/op  {d:>10.0} ops/s\n", .{
            result.name,
            result.avg_us,
            result.ops_per_sec,
        });
    }

    // Fallback
    {
        const result = try benchmark(allocator, "Fallback", iterations, benchFallback);
        std.debug.print("{s:<30} {d:>10.0} μs/op  {d:>10.0} ops/s\n", .{
            result.name,
            result.avg_us,
            result.ops_per_sec,
        });
    }

    std.debug.print("\n=== Benchmark Complete ===\n", .{});
}
