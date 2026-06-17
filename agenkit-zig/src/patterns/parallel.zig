/// Parallel Pattern - Execute agents concurrently
///
/// The Parallel pattern executes multiple agents with the same input,
/// collects all results, and aggregates them. This enables fan-out/fan-in
/// patterns for consensus, voting, or redundancy.
///
/// Performance Characteristics:
/// - Bounded by slowest agent (true parallel execution via std.Thread)
/// - Memory: O(n) where n = number of agents
///
/// Use Cases:
/// - Consensus building (multiple agents vote)
/// - Redundancy (multiple approaches to same problem)
/// - Ensemble methods (combine multiple results)
///
/// Example:
///     const agents = [_]Agent{ agent1, agent2, agent3 };
///     var parallel = try ParallelAgent.init(
///         allocator,
///         &agents,
///         "ensemble",
///         defaultAggregator
///     );
///     defer parallel.deinit();
///
///     const result = try parallel.agent().process(input_message);
///
/// Thread Safety:
///   Each agent processes an independent copy of the input message.
///   Agents must not modify the message in place; they are expected to
///   produce a new Message as their result.
const std = @import("std");
const Agent = @import("../agent.zig").Agent;
const AgentError = @import("../agent.zig").AgentError;
const StreamCallbacks = @import("../agent.zig").StreamCallbacks;
const Result = @import("../agent.zig").Result;
const Message = @import("../message.zig").Message;
const IntrospectionResult = @import("../introspection.zig").IntrospectionResult;
const createDefaultIntrospectionResult = @import("../introspection.zig").createDefaultIntrospectionResult;
const Allocator = std.mem.Allocator;

/// Aggregator function type - combines multiple messages into one
pub const Aggregator = *const fn (allocator: Allocator, messages: []Message) AgentError!Message;

/// Default aggregator - returns first message, stores others in metadata
pub fn defaultAggregator(allocator: Allocator, messages: []Message) AgentError!Message {
    if (messages.len == 0) {
        return AgentError.ProcessingFailed;
    }

    // Clone first message
    const first = messages[0];
    const text = first.contentAsText() catch {
        return AgentError.InvalidInput;
    };

    var result = Message.withText(allocator, first.role, text) catch {
        return AgentError.ProcessingFailed;
    };

    // Copy metadata from first
    var it = first.metadata.object.iterator();
    while (it.next()) |entry| {
        result.setMetadata(entry.key_ptr.*, entry.value_ptr.*) catch {
            return AgentError.ProcessingFailed;
        };
    }

    // Add parallel results count to metadata
    const count_value = std.json.Value{ .integer = @intCast(messages.len) };
    result.setMetadata("parallel_results_count", count_value) catch {
        return AgentError.ProcessingFailed;
    };

    return result;
}

/// Parallel Pattern - Executes agents concurrently and aggregates results
pub const ParallelAgent = struct {
    allocator: Allocator,
    agents: []Agent,
    pattern_name: []const u8,
    aggregator: Aggregator,
    owned_agents: bool,

    /// Initialize a parallel pattern with a list of agents
    ///
    /// Args:
    ///     allocator: Memory allocator
    ///     agents: Slice of agents to execute in parallel
    ///     name: Pattern name for identification
    ///     aggregator_fn: Function to combine results (default: defaultAggregator)
    ///
    /// Returns:
    ///     Initialized ParallelAgent
    ///
    /// Errors:
    ///     - Allocator.Error: If memory allocation fails
    pub fn init(
        allocator: Allocator,
        agents: []const Agent,
        name: []const u8,
        aggregator_fn: Aggregator,
    ) !*ParallelAgent {
        if (agents.len == 0) {
            return error.OutOfMemory; // Reuse existing error type
        }

        const self = try allocator.create(ParallelAgent);

        // Copy agents slice
        const agents_copy = try allocator.alloc(Agent, agents.len);
        @memcpy(agents_copy, agents);

        // Duplicate name
        const name_copy = try allocator.dupe(u8, name);

        self.* = ParallelAgent{
            .allocator = allocator,
            .agents = agents_copy,
            .pattern_name = name_copy,
            .aggregator = aggregator_fn,
            .owned_agents = true,
        };

        return self;
    }

    /// Create agent interface for this pattern
    pub fn agent(self: *ParallelAgent) Agent {
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
        const self: *ParallelAgent = @ptrCast(@alignCast(ptr));
        return self.pattern_name;
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const []const u8 {
        const self: *ParallelAgent = @ptrCast(@alignCast(ptr));

        // Collect unique capabilities from all agents
        var caps_set = std.StringHashMap(void).init(allocator);
        defer caps_set.deinit();

        for (self.agents) |a| {
            const agent_caps = try a.capabilities(allocator);
            defer allocator.free(agent_caps);

            for (agent_caps) |cap| {
                try caps_set.put(cap, {});
            }
        }

        // Convert to slice
        const caps = try allocator.alloc([]const u8, caps_set.count());
        var iter = caps_set.keyIterator();
        var i: usize = 0;
        while (iter.next()) |key| : (i += 1) {
            caps[i] = key.*;
        }

        return caps;
    }

    /// Per-thread context: holds the input, output, and error state for one agent.
    /// The `message` field is a shallow copy of the caller's input — agents must
    /// only READ from it, never call deinit() or modify it.
    const ThreadContext = struct {
        agent: Agent,
        message: Message, // NOT owned; shared read-only input
        result: ?Message = null,
        failed: bool = false,
        err: AgentError = AgentError.ProcessingFailed,

        fn run(ctx: *ThreadContext) void {
            const res = ctx.agent.process(ctx.message) catch |err| {
                ctx.failed = true;
                ctx.err = err;
                return;
            };
            ctx.result = res.unwrap() catch |err| {
                ctx.failed = true;
                ctx.err = err;
                return;
            };
        }
    };

    fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
        const self: *ParallelAgent = @ptrCast(@alignCast(ptr));

        // Allocate per-thread contexts
        const contexts = self.allocator.alloc(ThreadContext, self.agents.len) catch {
            return AgentError.ProcessingFailed;
        };
        defer self.allocator.free(contexts);

        // Allocate thread handles
        const threads = self.allocator.alloc(std.Thread, self.agents.len) catch {
            return AgentError.ProcessingFailed;
        };
        defer self.allocator.free(threads);

        // Initialise all contexts
        for (self.agents, 0..) |a, i| {
            contexts[i] = .{ .agent = a, .message = message };
        }

        // Spawn one thread per agent; on spawn failure join already-running threads
        var spawned: usize = 0;
        for (0..self.agents.len) |i| {
            threads[i] = std.Thread.spawn(.{}, ThreadContext.run, .{&contexts[i]}) catch {
                for (threads[0..spawned]) |t| t.join();
                for (contexts[0..spawned]) |*ctx| {
                    if (ctx.result) |*r| r.deinit();
                }
                return AgentError.ProcessingFailed;
            };
            spawned += 1;
        }

        // Join all threads
        for (threads[0..spawned]) |t| t.join();

        // Check for errors from any thread; clean up all results on failure
        for (contexts) |ctx| {
            if (ctx.failed) {
                for (contexts) |*c| {
                    if (c.result) |*r| r.deinit();
                }
                return ctx.err;
            }
        }

        // Collect results into a contiguous slice
        const results = self.allocator.alloc(Message, self.agents.len) catch {
            for (contexts) |*ctx| {
                if (ctx.result) |*r| r.deinit();
            }
            return AgentError.ProcessingFailed;
        };
        defer self.allocator.free(results);

        for (contexts, 0..) |ctx, i| {
            results[i] = ctx.result.?;
        }

        // Aggregate results (creates a new message)
        const aggregated = self.aggregator(self.allocator, results) catch |err| {
            for (results) |*r| r.deinit();
            return err;
        };

        // Clean up individual results (aggregator owns the output message)
        for (results) |*r| {
            r.deinit();
        }

        return Result{ .ok = aggregated };
    }

    fn introspectImpl(ptr: *anyopaque, alloc: Allocator) Allocator.Error!IntrospectionResult {
        const caps = try capabilitiesImpl(ptr, alloc);
        defer {
            for (caps) |cap| alloc.free(cap);
            alloc.free(caps);
        }
        const name_str = nameImpl(ptr);
        return createDefaultIntrospectionResult(alloc, name_str, caps);
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *ParallelAgent = @ptrCast(@alignCast(ptr));

        if (self.owned_agents) {
            self.allocator.free(self.agents);
        }
        self.allocator.free(self.pattern_name);
        self.allocator.destroy(self);
    }

    pub fn deinit(self: *ParallelAgent) void {
        if (self.owned_agents) {
            self.allocator.free(self.agents);
        }
        self.allocator.free(self.pattern_name);
        self.allocator.destroy(self);
    }
};

// ============================================================================
// Deprecated Aliases (v0.42.0 - will be removed in v0.43.0)
// ============================================================================

/// DEPRECATED: Use ParallelAgent instead
/// This alias exists for backward compatibility and will be removed in v0.43.0
pub const ParallelPattern = ParallelAgent;

// ============================================================================
// Tests
// ============================================================================

fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: StreamCallbacks) AgentError!void {
    _ = ptr;
    _ = message;
    callbacks.onError(AgentError.NotImplemented);
}

test "ParallelAgent basic execution" {
    const allocator = std.testing.allocator;
    const EchoAgent = @import("../agent.zig").EchoAgent;

    // Create agents
    var echo1 = try EchoAgent.init(allocator);
    defer echo1.agent().deinit();
    var echo2 = try EchoAgent.init(allocator);
    defer echo2.agent().deinit();
    var echo3 = try EchoAgent.init(allocator);
    defer echo3.agent().deinit();

    const agents = [_]Agent{ echo1.agent(), echo2.agent(), echo3.agent() };

    var parallel = try ParallelAgent.init(allocator, &agents, "test_parallel", defaultAggregator);
    defer parallel.deinit();

    // Test execution
    var msg = try Message.withText(allocator, .user, "Hello!");
    defer msg.deinit();

    const result = try parallel.agent().process(msg);
    var response = try result.unwrap();
    defer response.deinit();

    const text = try response.contentAsText();
    try std.testing.expectEqualStrings("Hello!", text);

    // Check metadata
    const count = response.getMetadata("parallel_results_count");
    try std.testing.expect(count != null);
    try std.testing.expectEqual(@as(i64, 3), count.?.integer);
}

test "ParallelAgent custom aggregator" {
    const allocator = std.testing.allocator;
    const EchoAgent = @import("../agent.zig").EchoAgent;

    // Custom aggregator that concatenates all results
    const concatenateAggregator = struct {
        fn aggregate(alloc: Allocator, messages: []Message) AgentError!Message {
            if (messages.len == 0) {
                return AgentError.ProcessingFailed;
            }

            // Concatenate all content
            var buffer = std.ArrayList(u8).empty;
            defer buffer.deinit(alloc);

            for (messages, 0..) |m, i| {
                const text = m.contentAsText() catch {
                    return AgentError.InvalidInput;
                };
                buffer.appendSlice(alloc, text) catch {
                    return AgentError.ProcessingFailed;
                };
                if (i < messages.len - 1) {
                    buffer.appendSlice(alloc, ", ") catch {
                        return AgentError.ProcessingFailed;
                    };
                }
            }

            const result = Message.withText(alloc, .assistant, buffer.items) catch {
                return AgentError.ProcessingFailed;
            };

            return result;
        }
    }.aggregate;

    var echo1 = try EchoAgent.init(allocator);
    defer echo1.agent().deinit();
    var echo2 = try EchoAgent.init(allocator);
    defer echo2.agent().deinit();

    const agents = [_]Agent{ echo1.agent(), echo2.agent() };
    var parallel = try ParallelAgent.init(allocator, &agents, "concat_parallel", concatenateAggregator);
    defer parallel.deinit();

    var msg = try Message.withText(allocator, .user, "test");
    defer msg.deinit();

    const result = try parallel.agent().process(msg);
    var response = try result.unwrap();
    defer response.deinit();

    const text = try response.contentAsText();
    try std.testing.expectEqualStrings("test, test", text);
}

test "ParallelAgent name and capabilities" {
    const allocator = std.testing.allocator;
    const EchoAgent = @import("../agent.zig").EchoAgent;

    var echo1 = try EchoAgent.init(allocator);
    defer echo1.agent().deinit();

    const agents = [_]Agent{echo1.agent()};
    var parallel = try ParallelAgent.init(allocator, &agents, "my_parallel", defaultAggregator);
    defer parallel.deinit();

    const agent_iface = parallel.agent();
    try std.testing.expectEqualStrings("my_parallel", agent_iface.name());

    const caps = try agent_iface.capabilities(allocator);
    defer allocator.free(caps);
    try std.testing.expect(caps.len > 0);
}
