//! Reflection Pattern Example
//!
//! The Reflection pattern enables agents to iteratively improve their outputs
//! through cycles of generation, critique, and refinement.
//!
//! This example demonstrates:
//! - Generator and critic agent roles
//! - Iterative refinement loops
//! - Quality scoring and thresholds
//! - Different stopping conditions
//! - Reflection history tracking
//!
//! Run with: zig build run-reflection

const std = @import("std");
const agenkit = @import("agenkit");

/// Simple generator that improves text with each iteration
const SimpleGenerator = struct {
    allocator: std.mem.Allocator,
    agent_name: []const u8,
    iteration_count: *usize,

    pub fn init(allocator: std.mem.Allocator) !*SimpleGenerator {
        const self = try allocator.create(SimpleGenerator);
        const name = try allocator.dupe(u8, "Generator");
        const counter = try allocator.create(usize);
        counter.* = 0;

        self.* = SimpleGenerator{
            .allocator = allocator,
            .agent_name = name,
            .iteration_count = counter,
        };

        return self;
    }

    pub fn deinit(self: *SimpleGenerator) void {
        self.allocator.free(self.agent_name);
        self.allocator.destroy(self.iteration_count);
        self.allocator.destroy(self);
    }

    pub fn agent(self: *SimpleGenerator) agenkit.Agent {
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
        const self: *SimpleGenerator = @ptrCast(@alignCast(ptr));
        return self.agent_name;
    }

    fn capabilitiesImpl(_: *anyopaque, allocator: std.mem.Allocator) std.mem.Allocator.Error![]const []const u8 {
        const caps = try allocator.alloc([]const u8, 1);
        caps[0] = "generation";
        return caps;
    }

    fn processImpl(ptr: *anyopaque, message: agenkit.Message) agenkit.AgentError!agenkit.Result {
        const self: *SimpleGenerator = @ptrCast(@alignCast(ptr));
        self.iteration_count.* += 1;

        const content = message.contentAsText() catch {
            return agenkit.Result{ .err = agenkit.AgentError.InvalidInput };
        };

        // Each iteration adds more detail
        const improved = std.fmt.allocPrint(
            self.allocator,
            "{s} [refined v{d}]",
            .{ content, self.iteration_count.* },
        ) catch {
            return agenkit.AgentError.ProcessingFailed;
        };
        defer self.allocator.free(improved);

        const response = agenkit.Message.withText(
            self.allocator,
            .assistant,
            improved,
        ) catch {
            return agenkit.AgentError.ProcessingFailed;
        };

        return agenkit.Result{ .ok = response };
    }

    fn introspectImpl(ptr: *anyopaque, allocator: std.mem.Allocator) std.mem.Allocator.Error!agenkit.IntrospectionResult {
        const self: *SimpleGenerator = @ptrCast(@alignCast(ptr));
        const caps = try capabilitiesImpl(ptr, allocator);
        defer allocator.free(caps);
        return agenkit.createDefaultIntrospectionResult(allocator, self.agent_name, caps);
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *SimpleGenerator = @ptrCast(@alignCast(ptr));
        self.deinit();
    }
};

/// Mock critic that provides scores and feedback
const MockCritic = struct {
    allocator: std.mem.Allocator,
    agent_name: []const u8,
    scores: []const f32,
    current_index: *usize,

    pub fn init(allocator: std.mem.Allocator, scores: []const f32) !*MockCritic {
        const self = try allocator.create(MockCritic);
        const name = try allocator.dupe(u8, "Critic");
        const index = try allocator.create(usize);
        index.* = 0;

        // Copy scores
        const scores_copy = try allocator.alloc(f32, scores.len);
        @memcpy(scores_copy, scores);

        self.* = MockCritic{
            .allocator = allocator,
            .agent_name = name,
            .scores = scores_copy,
            .current_index = index,
        };

        return self;
    }

    pub fn deinit(self: *MockCritic) void {
        self.allocator.free(self.agent_name);
        self.allocator.free(self.scores);
        self.allocator.destroy(self.current_index);
        self.allocator.destroy(self);
    }

    pub fn agent(self: *MockCritic) agenkit.Agent {
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
        const self: *MockCritic = @ptrCast(@alignCast(ptr));
        return self.agent_name;
    }

    fn capabilitiesImpl(_: *anyopaque, allocator: std.mem.Allocator) std.mem.Allocator.Error![]const []const u8 {
        const caps = try allocator.alloc([]const u8, 1);
        caps[0] = "critique";
        return caps;
    }

    fn processImpl(ptr: *anyopaque, _: agenkit.Message) agenkit.AgentError!agenkit.Result {
        const self: *MockCritic = @ptrCast(@alignCast(ptr));

        const score = if (self.current_index.* < self.scores.len)
            self.scores[self.current_index.*]
        else
            0.95;

        self.current_index.* += 1;

        // Return structured JSON critique
        const critique = std.fmt.allocPrint(
            self.allocator,
            "{{\"score\": {d:.2}, \"feedback\": \"Iteration {d} feedback\"}}",
            .{ score, self.current_index.* },
        ) catch {
            return agenkit.AgentError.ProcessingFailed;
        };
        defer self.allocator.free(critique);

        const response = agenkit.Message.withText(
            self.allocator,
            .assistant,
            critique,
        ) catch {
            return agenkit.AgentError.ProcessingFailed;
        };

        return agenkit.Result{ .ok = response };
    }

    fn introspectImpl(ptr: *anyopaque, allocator: std.mem.Allocator) std.mem.Allocator.Error!agenkit.IntrospectionResult {
        const self: *MockCritic = @ptrCast(@alignCast(ptr));
        const caps = try capabilitiesImpl(ptr, allocator);
        defer allocator.free(caps);
        return agenkit.createDefaultIntrospectionResult(allocator, self.agent_name, caps);
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *MockCritic = @ptrCast(@alignCast(ptr));
        self.deinit();
    }
};


fn processStreamImpl(ptr: *anyopaque, message: agenkit.Message, callbacks: agenkit.StreamCallbacks) agenkit.AgentError!void {
    _ = ptr;
    _ = message;
    callbacks.onError(agenkit.AgentError.NotImplemented);
}
pub fn main() !void {
    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("\n=== AgentKit Reflection Pattern Example ===\n\n", .{});

    // Example 1: Basic reflection with quality threshold
    std.debug.print("--- Example 1: Quality Threshold (0.8) ---\n", .{});
    {
        var generator = try SimpleGenerator.init(allocator);
        defer generator.agent().deinit();

        // Scores: 0.5, 0.7, 0.85 -> stops at 0.85 (exceeds 0.8)
        const scores = [_]f32{ 0.5, 0.7, 0.85 };
        var critic = try MockCritic.init(allocator, &scores);
        defer critic.agent().deinit();

        var reflection = try agenkit.patterns.ReflectionAgent.init(
            allocator,
            generator.agent(),
            critic.agent(),
            5, // max_iterations
            0.8, // quality_threshold
            0.05, // improvement_threshold
            .structured, // critique_format
            false, // verbose
        );
        defer reflection.deinit();

        var input = try agenkit.Message.withText(allocator, .user, "Initial draft");
        defer input.deinit();

        const result = try reflection.agent().process(input);
        var output = try result.unwrap();
        defer output.deinit();

        std.debug.print("Final output: {s}\n", .{try output.contentAsText()});
        std.debug.print("Iterations: {d}\n", .{reflection.history.items.len});
        if (reflection.history.items.len > 0) {
            const last = reflection.history.items[reflection.history.items.len - 1];
            std.debug.print("Final score: {d:.2}\n", .{last.quality_score});
        }
        std.debug.print("✓ Stopped when quality threshold exceeded\n\n", .{});
    }

    // Example 2: Max iterations reached
    std.debug.print("--- Example 2: Max Iterations (3) ---\n", .{});
    {
        var generator = try SimpleGenerator.init(allocator);
        defer generator.agent().deinit();

        // Low scores - won't reach threshold
        const scores = [_]f32{ 0.3, 0.4, 0.5 };
        var critic = try MockCritic.init(allocator, &scores);
        defer critic.agent().deinit();

        var reflection = try agenkit.patterns.ReflectionAgent.init(
            allocator,
            generator.agent(),
            critic.agent(),
            3, // max_iterations (limit)
            0.9, // high quality_threshold (won't reach)
            0.05,
            .structured,
            false,
        );
        defer reflection.deinit();

        var input = try agenkit.Message.withText(allocator, .user, "Draft");
        defer input.deinit();

        const result = try reflection.agent().process(input);
        var output = try result.unwrap();
        defer output.deinit();

        std.debug.print("Final output: {s}\n", .{try output.contentAsText()});
        std.debug.print("Iterations: {d}\n", .{reflection.history.items.len});
        std.debug.print("✓ Stopped at max iterations\n\n", .{});
    }

    // Example 3: Minimal improvement threshold
    std.debug.print("--- Example 3: Minimal Improvement (0.1) ---\n", .{});
    {
        var generator = try SimpleGenerator.init(allocator);
        defer generator.agent().deinit();

        // Plateauing scores: 0.5, 0.6, 0.62 (only +0.02 improvement)
        const scores = [_]f32{ 0.5, 0.6, 0.62 };
        var critic = try MockCritic.init(allocator, &scores);
        defer critic.agent().deinit();

        var reflection = try agenkit.patterns.ReflectionAgent.init(
            allocator,
            generator.agent(),
            critic.agent(),
            5,
            0.9, // won't reach
            0.1, // improvement_threshold (0.02 < 0.1)
            .structured,
            false,
        );
        defer reflection.deinit();

        var input = try agenkit.Message.withText(allocator, .user, "Content");
        defer input.deinit();

        const result = try reflection.agent().process(input);
        var output = try result.unwrap();
        defer output.deinit();

        std.debug.print("Final output: {s}\n", .{try output.contentAsText()});
        std.debug.print("Iterations: {d}\n", .{reflection.history.items.len});
        std.debug.print("✓ Stopped due to minimal improvement\n\n", .{});
    }

    // Example 4: Perfect score achieved
    std.debug.print("--- Example 4: Perfect Score (1.0) ---\n", .{});
    {
        var generator = try SimpleGenerator.init(allocator);
        defer generator.agent().deinit();

        // Scores reach perfect: 0.7, 1.0
        const scores = [_]f32{ 0.7, 1.0 };
        var critic = try MockCritic.init(allocator, &scores);
        defer critic.agent().deinit();

        var reflection = try agenkit.patterns.ReflectionAgent.init(
            allocator,
            generator.agent(),
            critic.agent(),
            5,
            0.8,
            0.05,
            .structured,
            false,
        );
        defer reflection.deinit();

        var input = try agenkit.Message.withText(allocator, .user, "Text");
        defer input.deinit();

        const result = try reflection.agent().process(input);
        var output = try result.unwrap();
        defer output.deinit();

        std.debug.print("Final output: {s}\n", .{try output.contentAsText()});
        std.debug.print("Iterations: {d}\n", .{reflection.history.items.len});
        std.debug.print("✓ Stopped at perfect score\n\n", .{});
    }

    std.debug.print("=== Reflection Pattern Summary ===\n", .{});
    std.debug.print("✓ Iterative refinement through critique\n", .{});
    std.debug.print("✓ Multiple stopping conditions:\n", .{});
    std.debug.print("  - Quality threshold exceeded\n", .{});
    std.debug.print("  - Max iterations reached\n", .{});
    std.debug.print("  - Minimal improvement detected\n", .{});
    std.debug.print("  - Perfect score achieved\n", .{});
    std.debug.print("✓ Useful for: code review, content editing, error correction\n", .{});
    std.debug.print("\n✓ Reflection pattern example completed successfully!\n\n", .{});
}
