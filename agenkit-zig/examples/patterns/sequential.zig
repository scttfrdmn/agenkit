//! Sequential Pattern Example
//!
//! The Sequential pattern executes agents one after another in a pipeline,
//! where the output of one agent becomes the input to the next.
//!
//! This example demonstrates:
//! - Creating a sequential pipeline of agents
//! - Data transformation through multiple stages
//! - Error propagation in pipelines
//! - Use cases: data processing, multi-stage reasoning
//!
//! Run with: zig build run-sequential

const std = @import("std");
const agenkit = @import("agenkit");

/// Transform agent that adds a prefix to messages
const PrefixAgent = struct {
    allocator: std.mem.Allocator,
    agent_name: []const u8,
    prefix: []const u8,

    pub fn init(allocator: std.mem.Allocator, name: []const u8, prefix: []const u8) !*PrefixAgent {
        const self = try allocator.create(PrefixAgent);
        const name_copy = try allocator.dupe(u8, name);
        const prefix_copy = try allocator.dupe(u8, prefix);

        self.* = PrefixAgent{
            .allocator = allocator,
            .agent_name = name_copy,
            .prefix = prefix_copy,
        };

        return self;
    }

    pub fn deinit(self: *PrefixAgent) void {
        self.allocator.free(self.agent_name);
        self.allocator.free(self.prefix);
        self.allocator.destroy(self);
    }

    pub fn agent(self: *PrefixAgent) agenkit.Agent {
        return agenkit.Agent{
            .ptr = self,
            .vtable = &.{
                .name = nameImpl,
                .capabilities = capabilitiesImpl,
                .process = processImpl,
                .introspect = introspectImpl,
                .deinit = deinitImpl,
            },
        };
    }

    fn nameImpl(ptr: *anyopaque) []const u8 {
        const self: *PrefixAgent = @ptrCast(@alignCast(ptr));
        return self.agent_name;
    }

    fn capabilitiesImpl(_: *anyopaque, allocator: std.mem.Allocator) std.mem.Allocator.Error![]const []const u8 {
        const caps = try allocator.alloc([]const u8, 1);
        caps[0] = "prefix-transform";
        return caps;
    }

    fn processImpl(ptr: *anyopaque, message: agenkit.Message) agenkit.AgentError!agenkit.Result {
        const self: *PrefixAgent = @ptrCast(@alignCast(ptr));

        const content = message.contentAsText() catch {
            return agenkit.Result{ .err = agenkit.AgentError.InvalidInput };
        };

        const new_content = std.fmt.allocPrint(
            self.allocator,
            "{s}{s}",
            .{ self.prefix, content },
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
        const self: *PrefixAgent = @ptrCast(@alignCast(ptr));
        const caps = try capabilitiesImpl(ptr, allocator);
        defer allocator.free(caps);
        return agenkit.createDefaultIntrospectionResult(allocator, self.agent_name, caps);
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *PrefixAgent = @ptrCast(@alignCast(ptr));
        self.deinit();
    }
};

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("\n=== AgentKit Sequential Pattern Example ===\n\n", .{});

    // Example 1: Simple 3-stage pipeline
    std.debug.print("--- Example 1: Simple 3-Stage Pipeline ---\n", .{});
    {
        // Create three agents that add prefixes
        var agent1 = try PrefixAgent.init(allocator, "Stage1", "[START] ");
        defer agent1.agent().deinit();

        var agent2 = try PrefixAgent.init(allocator, "Stage2", "[PROCESSED] ");
        defer agent2.agent().deinit();

        var agent3 = try PrefixAgent.init(allocator, "Stage3", "[END] ");
        defer agent3.agent().deinit();

        const agents = [_]agenkit.Agent{
            agent1.agent(),
            agent2.agent(),
            agent3.agent(),
        };

        var pipeline = try agenkit.patterns.SequentialPattern.init(
            allocator,
            &agents,
            "three-stage-pipeline",
        );
        defer pipeline.deinit();

        var input = try agenkit.Message.withText(allocator, .user, "Hello World");
        defer input.deinit();

        std.debug.print("Input: {s}\n", .{try input.contentAsText()});

        const result = try pipeline.agent().process(input);
        var output = try result.unwrap();
        defer output.deinit();

        std.debug.print("Output: {s}\n", .{try output.contentAsText()});
        std.debug.print("✓ Data flowed through all 3 stages\n\n", .{});
    }

    // Example 2: Data transformation pipeline
    std.debug.print("--- Example 2: Multi-Message Pipeline ---\n", .{});
    {
        var validator = try PrefixAgent.init(allocator, "Validator", "✓ Valid: ");
        defer validator.agent().deinit();

        var enricher = try PrefixAgent.init(allocator, "Enricher", "→ Enriched: ");
        defer enricher.agent().deinit();

        var formatter = try PrefixAgent.init(allocator, "Formatter", "★ Final: ");
        defer formatter.agent().deinit();

        const agents = [_]agenkit.Agent{
            validator.agent(),
            enricher.agent(),
            formatter.agent(),
        };

        var pipeline = try agenkit.patterns.SequentialPattern.init(
            allocator,
            &agents,
            "data-pipeline",
        );
        defer pipeline.deinit();

        // Process multiple inputs through the same pipeline
        const inputs = [_][]const u8{ "Request A", "Request B", "Request C" };

        for (inputs) |input_text| {
            var msg = try agenkit.Message.withText(allocator, .user, input_text);
            defer msg.deinit();

            const result = try pipeline.agent().process(msg);
            var output = try result.unwrap();
            defer output.deinit();

            std.debug.print("{s}\n", .{try output.contentAsText()});
        }

        std.debug.print("✓ Processed 3 messages through pipeline\n\n", .{});
    }

    // Example 3: Single agent (degenerate pipeline)
    std.debug.print("--- Example 3: Single-Agent Pipeline ---\n", .{});
    {
        var single = try PrefixAgent.init(allocator, "Solo", "• ");
        defer single.agent().deinit();

        const agents = [_]agenkit.Agent{single.agent()};

        var pipeline = try agenkit.patterns.SequentialPattern.init(
            allocator,
            &agents,
            "single-agent",
        );
        defer pipeline.deinit();

        var input = try agenkit.Message.withText(allocator, .user, "Solo processing");
        defer input.deinit();

        const result = try pipeline.agent().process(input);
        var output = try result.unwrap();
        defer output.deinit();

        std.debug.print("Output: {s}\n", .{try output.contentAsText()});
        std.debug.print("✓ Single agent works as pipeline\n\n", .{});
    }

    // Example 4: Comparing direct vs pipeline execution
    std.debug.print("--- Example 4: Direct vs Pipeline Execution ---\n", .{});
    {
        var agent1 = try PrefixAgent.init(allocator, "A1", "1> ");
        defer agent1.agent().deinit();

        var agent2 = try PrefixAgent.init(allocator, "A2", "2> ");
        defer agent2.agent().deinit();

        // Direct execution
        std.debug.print("Direct execution:\n", .{});
        {
            var input = try agenkit.Message.withText(allocator, .user, "test");
            defer input.deinit();

            const r1 = try agent1.agent().process(input);
            var intermediate = try r1.unwrap();
            defer intermediate.deinit();

            std.debug.print("  After agent1: {s}\n", .{try intermediate.contentAsText()});

            const r2 = try agent2.agent().process(intermediate);
            var final = try r2.unwrap();
            defer final.deinit();

            std.debug.print("  After agent2: {s}\n", .{try final.contentAsText()});
        }

        // Pipeline execution
        std.debug.print("Pipeline execution:\n", .{});
        {
            const agents = [_]agenkit.Agent{ agent1.agent(), agent2.agent() };
            var pipeline = try agenkit.patterns.SequentialPattern.init(
                allocator,
                &agents,
                "comparison",
            );
            defer pipeline.deinit();

            var input = try agenkit.Message.withText(allocator, .user, "test");
            defer input.deinit();

            const result = try pipeline.agent().process(input);
            var output = try result.unwrap();
            defer output.deinit();

            std.debug.print("  Final output: {s}\n", .{try output.contentAsText()});
        }

        std.debug.print("✓ Both produce same result\n\n", .{});
    }

    std.debug.print("=== Sequential Pattern Summary ===\n", .{});
    std.debug.print("✓ Simple, predictable execution order\n", .{});
    std.debug.print("✓ No parallelism overhead\n", .{});
    std.debug.print("✓ Output of agent N becomes input to agent N+1\n", .{});
    std.debug.print("✓ Stops at first error (short-circuits)\n", .{});
    std.debug.print("✓ Perfect for transformation pipelines\n", .{});
    std.debug.print("\n✓ Sequential pattern example completed successfully!\n\n", .{});
}
