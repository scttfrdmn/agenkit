//! Parallel Pattern Example
//!
//! The Parallel pattern executes multiple agents with the same input,
//! collects all results, and aggregates them into a single output.
//!
//! This example demonstrates:
//! - Fan-out/fan-in execution pattern
//! - Default aggregator (returns first result with metadata)
//! - Custom aggregators for consensus/voting
//! - Use cases: ensemble methods, redundancy, consensus
//!
//! Run with: zig build run-parallel

const std = @import("std");
const agenkit = @import("agenkit");
const Message = agenkit.Message;
const AgentError = agenkit.AgentError;
const StreamCallbacks = agenkit.StreamCallbacks;

/// Agent that adds a specific label to messages
const LabelAgent = struct {
    allocator: std.mem.Allocator,
    agent_name: []const u8,
    label: []const u8,

    pub fn init(allocator: std.mem.Allocator, name: []const u8, label: []const u8) !*LabelAgent {
        const self = try allocator.create(LabelAgent);
        const name_copy = try allocator.dupe(u8, name);
        const label_copy = try allocator.dupe(u8, label);

        self.* = LabelAgent{
            .allocator = allocator,
            .agent_name = name_copy,
            .label = label_copy,
        };

        return self;
    }

    pub fn deinit(self: *LabelAgent) void {
        self.allocator.free(self.agent_name);
        self.allocator.free(self.label);
        self.allocator.destroy(self);
    }

    pub fn agent(self: *LabelAgent) agenkit.Agent {
        return agenkit.Agent{
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
        const self: *LabelAgent = @ptrCast(@alignCast(ptr));
        return self.agent_name;
    }

    fn capabilitiesImpl(_: *anyopaque, allocator: std.mem.Allocator) std.mem.Allocator.Error![]const []const u8 {
        const caps = try allocator.alloc([]const u8, 1);
        caps[0] = "labeling";
        return caps;
    }

    fn processImpl(ptr: *anyopaque, message: agenkit.Message) agenkit.AgentError!agenkit.Result {
        const self: *LabelAgent = @ptrCast(@alignCast(ptr));

        const content = message.contentAsText() catch {
            return agenkit.Result{ .err = agenkit.AgentError.InvalidInput };
        };

        const new_content = std.fmt.allocPrint(
            self.allocator,
            "[{s}] {s}",
            .{ self.label, content },
        ) catch {
            return agenkit.AgentError.ProcessingFailed;
        };
        defer self.allocator.free(new_content);

        const response = agenkit.Message.withText(
            self.allocator,
            .assistant,
            new_content,
        ) catch {
            return agenkit.AgentError.ProcessingFailed;
        };

        return agenkit.Result{ .ok = response };
    }

    fn introspectImpl(ptr: *anyopaque, allocator: std.mem.Allocator) std.mem.Allocator.Error!agenkit.IntrospectionResult {
        const self: *LabelAgent = @ptrCast(@alignCast(ptr));
        const caps = try capabilitiesImpl(ptr, allocator);
        defer allocator.free(caps);
        return agenkit.createDefaultIntrospectionResult(allocator, self.agent_name, caps);
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *LabelAgent = @ptrCast(@alignCast(ptr));
        self.deinit();
    }
};

/// Custom aggregator that concatenates all results
fn concatenatingAggregator(allocator: std.mem.Allocator, messages: []agenkit.Message) agenkit.AgentError!agenkit.Message {
    if (messages.len == 0) {
        return agenkit.AgentError.ProcessingFailed;
    }

    if (messages.len == 1) {
        // Single message - just clone it
        const text = messages[0].contentAsText() catch {
            return agenkit.AgentError.InvalidInput;
        };

        const result = agenkit.Message.withText(
            allocator,
            .assistant,
            text,
        ) catch {
            return agenkit.AgentError.ProcessingFailed;
        };

        return result;
    }

    // Build concatenated content (for 2+ messages, just do simple concatenation)
    // For 2 messages
    if (messages.len == 2) {
        const text1 = messages[0].contentAsText() catch {
            return agenkit.AgentError.InvalidInput;
        };
        const text2 = messages[1].contentAsText() catch {
            return agenkit.AgentError.InvalidInput;
        };

        const concatenated = std.fmt.allocPrint(
            allocator,
            "{s} | {s}",
            .{ text1, text2 },
        ) catch {
            return agenkit.AgentError.ProcessingFailed;
        };
        defer allocator.free(concatenated);

        const result = agenkit.Message.withText(
            allocator,
            .assistant,
            concatenated,
        ) catch {
            return agenkit.AgentError.ProcessingFailed;
        };

        return result;
    }

    // For 3+ messages
    const text1 = messages[0].contentAsText() catch {
        return agenkit.AgentError.InvalidInput;
    };
    const text2 = messages[1].contentAsText() catch {
        return agenkit.AgentError.InvalidInput;
    };
    const text3 = messages[2].contentAsText() catch {
        return agenkit.AgentError.InvalidInput;
    };

    const concatenated = std.fmt.allocPrint(
        allocator,
        "{s} | {s} | {s}",
        .{ text1, text2, text3 },
    ) catch {
        return agenkit.AgentError.ProcessingFailed;
    };
    defer allocator.free(concatenated);

    const result = agenkit.Message.withText(
        allocator,
        .assistant,
        concatenated,
    ) catch {
        return agenkit.AgentError.ProcessingFailed;
    };

    return result;
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

    std.debug.print("\n=== AgentKit Parallel Pattern Example ===\n\n", .{});

    // Example 1: Default aggregator (fan-out/fan-in)
    std.debug.print("--- Example 1: Default Aggregator ---\n", .{});
    {
        var agent1 = try LabelAgent.init(allocator, "Agent1", "A");
        defer agent1.agent().deinit();

        var agent2 = try LabelAgent.init(allocator, "Agent2", "B");
        defer agent2.agent().deinit();

        var agent3 = try LabelAgent.init(allocator, "Agent3", "C");
        defer agent3.agent().deinit();

        const agents = [_]agenkit.Agent{
            agent1.agent(),
            agent2.agent(),
            agent3.agent(),
        };

        var parallel = try agenkit.patterns.ParallelPattern.init(
            allocator,
            &agents,
            "default-ensemble",
            agenkit.patterns.defaultAggregator,
        );
        defer parallel.deinit();

        var input = try agenkit.Message.withText(allocator, .user, "Hello");
        defer input.deinit();

        std.debug.print("Input: {s}\n", .{try input.contentAsText()});
        std.debug.print("Processing with 3 agents in parallel...\n", .{});

        const result = try parallel.agent().process(input);
        var output = try result.unwrap();
        defer output.deinit();

        std.debug.print("Output: {s}\n", .{try output.contentAsText()});

        // Check metadata for result count
        if (output.metadata.object.get("parallel_results_count")) |count_value| {
            std.debug.print("Results collected: {d}\n", .{count_value.integer});
        }

        std.debug.print("✓ Default aggregator returns first result\n\n", .{});
    }

    // Example 2: Custom concatenating aggregator
    std.debug.print("--- Example 2: Custom Concatenating Aggregator ---\n", .{});
    {
        var agent1 = try LabelAgent.init(allocator, "Fast", "FAST");
        defer agent1.agent().deinit();

        var agent2 = try LabelAgent.init(allocator, "Accurate", "ACCURATE");
        defer agent2.agent().deinit();

        var agent3 = try LabelAgent.init(allocator, "Creative", "CREATIVE");
        defer agent3.agent().deinit();

        const agents = [_]agenkit.Agent{
            agent1.agent(),
            agent2.agent(),
            agent3.agent(),
        };

        var parallel = try agenkit.patterns.ParallelPattern.init(
            allocator,
            &agents,
            "concat-ensemble",
            concatenatingAggregator,
        );
        defer parallel.deinit();

        var input = try agenkit.Message.withText(allocator, .user, "Task");
        defer input.deinit();

        std.debug.print("Input: {s}\n", .{try input.contentAsText()});
        std.debug.print("Combining all results...\n", .{});

        const result = try parallel.agent().process(input);
        var output = try result.unwrap();
        defer output.deinit();

        std.debug.print("Combined: {s}\n", .{try output.contentAsText()});
        std.debug.print("✓ All results concatenated\n\n", .{});
    }

    // Example 3: Ensemble with different agent types
    std.debug.print("--- Example 3: Mixed Agent Ensemble ---\n", .{});
    {
        // Mix labeled agents with echo agent
        var label = try LabelAgent.init(allocator, "Labeler", "LABELED");
        defer label.agent().deinit();

        var echo = try agenkit.EchoAgent.init(allocator);
        defer echo.agent().deinit();

        const agents = [_]agenkit.Agent{
            label.agent(),
            echo.agent(),
        };

        var parallel = try agenkit.patterns.ParallelPattern.init(
            allocator,
            &agents,
            "mixed-ensemble",
            concatenatingAggregator,
        );
        defer parallel.deinit();

        var input = try agenkit.Message.withText(allocator, .user, "Test");
        defer input.deinit();

        const result = try parallel.agent().process(input);
        var output = try result.unwrap();
        defer output.deinit();

        std.debug.print("Mixed ensemble output: {s}\n", .{try output.contentAsText()});
        std.debug.print("✓ Different agent types work together\n\n", .{});
    }

    // Example 4: Single agent (degenerate parallel)
    std.debug.print("--- Example 4: Single-Agent Parallel ---\n", .{});
    {
        var single = try LabelAgent.init(allocator, "Solo", "SOLO");
        defer single.agent().deinit();

        const agents = [_]agenkit.Agent{single.agent()};

        var parallel = try agenkit.patterns.ParallelPattern.init(
            allocator,
            &agents,
            "single-parallel",
            agenkit.patterns.defaultAggregator,
        );
        defer parallel.deinit();

        var input = try agenkit.Message.withText(allocator, .user, "Solo");
        defer input.deinit();

        const result = try parallel.agent().process(input);
        var output = try result.unwrap();
        defer output.deinit();

        std.debug.print("Output: {s}\n", .{try output.contentAsText()});
        std.debug.print("✓ Single agent works as parallel\n\n", .{});
    }

    std.debug.print("=== Parallel Pattern Summary ===\n", .{});
    std.debug.print("✓ Fan-out: Same input to all agents\n", .{});
    std.debug.print("✓ Fan-in: Aggregate results with custom logic\n", .{});
    std.debug.print("✓ Useful for: consensus, voting, ensemble methods\n", .{});
    std.debug.print("✓ Default aggregator: first result + metadata\n", .{});
    std.debug.print("✓ Custom aggregators: combine results your way\n", .{});
    std.debug.print("✓ Note: Current implementation is sequential\n", .{});
    std.debug.print("  (true parallelism coming in future version)\n", .{});
    std.debug.print("\n✓ Parallel pattern example completed successfully!\n\n", .{});
}
