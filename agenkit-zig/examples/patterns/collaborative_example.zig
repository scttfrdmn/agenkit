//! Collaborative Pattern Example
//!
//! This example demonstrates the Collaborative pattern for peer-to-peer
//! collaboration with iterative refinement. Multiple agents work together,
//! refining their responses until consensus is reached.
//!
//! Build: zig build
//! Run: zig build run-collaborative

const std = @import("std");
const agenkit = @import("agenkit");

const Agent = agenkit.Agent;
const StreamCallbacks = agenkit.StreamCallbacks;
const AgentError = agenkit.AgentError;
const Message = agenkit.Message;
const CollaborativeAgent = agenkit.patterns.CollaborativeAgent;
const CollaborativeConfig = agenkit.patterns.CollaborativeConfig;
const concatenateMerge = agenkit.patterns.concatenateMerge;
const firstMerge = agenkit.patterns.firstMerge;
const exactMatchConsensus = agenkit.patterns.exactMatchConsensus;

/// Mock reviewer agent that provides feedback
const ReviewerAgent = struct {
    allocator: std.mem.Allocator,
    name: []const u8,
    perspective: []const u8,
    round_count: u32 = 0,

    pub fn init(allocator: std.mem.Allocator, name: []const u8, perspective: []const u8) !*ReviewerAgent {
        const self = try allocator.create(ReviewerAgent);
        self.* = .{
            .allocator = allocator,
            .name = try allocator.dupe(u8, name),
            .perspective = try allocator.dupe(u8, perspective),
            .round_count = 0,
        };
        return self;
    }

    pub fn agent(self: *ReviewerAgent) Agent {
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
        const self: *ReviewerAgent = @ptrCast(@alignCast(ptr));
        return self.name;
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: std.mem.Allocator) std.mem.Allocator.Error![]const []const u8 {
        const self: *ReviewerAgent = @ptrCast(@alignCast(ptr));
        const caps = try allocator.alloc([]const u8, 1);
        caps[0] = try allocator.dupe(u8, self.perspective);
        return caps;
    }

    fn processImpl(ptr: *anyopaque, message: Message) agenkit.AgentError!agenkit.Result {
        const self: *ReviewerAgent = @ptrCast(@alignCast(ptr));

        self.round_count += 1;

        const content = message.contentAsText() catch return agenkit.AgentError.ProcessingFailed;

        // Build response based on perspective
        const response = std.fmt.allocPrint(
            self.allocator,
            "{s} review (round {d}): {s} perspective on '{s}'",
            .{ self.name, self.round_count, self.perspective, content },
        ) catch return agenkit.AgentError.ProcessingFailed;
        defer self.allocator.free(response);

        const response_msg = Message.withText(self.allocator, .assistant, response) catch return agenkit.AgentError.ProcessingFailed;
        return agenkit.Result{ .ok = response_msg };
    }

    fn introspectImpl(ptr: *anyopaque, allocator: std.mem.Allocator) std.mem.Allocator.Error!agenkit.IntrospectionResult {
        const self: *ReviewerAgent = @ptrCast(@alignCast(ptr));
        const caps = try capabilitiesImpl(ptr, allocator);
        defer allocator.free(caps);
        return agenkit.createDefaultIntrospectionResult(allocator, self.name, caps);
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *ReviewerAgent = @ptrCast(@alignCast(ptr));
        self.deinit();
    }

    pub fn deinit(self: *ReviewerAgent) void {
        self.allocator.free(self.name);
        self.allocator.free(self.perspective);
        self.allocator.destroy(self);
    }
};


fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: StreamCallbacks) AgentError!void {
    _ = ptr;
    _ = message;
    callbacks.onError(AgentError.NotImplemented);
}
pub fn main() !void {
    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("\n=== Collaborative Pattern Example ===\n\n", .{});

    // ========================================================================
    // Example 1: Code Review Collaboration
    // ========================================================================
    std.debug.print("Example 1: Multi-Perspective Code Review\n", .{});
    std.debug.print("-----------------------------------------\n", .{});

    // Create reviewer agents with different perspectives
    var security_reviewer = try ReviewerAgent.init(allocator, "SecurityReviewer", "Security");
    defer security_reviewer.deinit();

    var performance_reviewer = try ReviewerAgent.init(allocator, "PerformanceReviewer", "Performance");
    defer performance_reviewer.deinit();

    var maintainability_reviewer = try ReviewerAgent.init(allocator, "MaintainabilityReviewer", "Maintainability");
    defer maintainability_reviewer.deinit();

    // Create collaborative agent
    const review_agents = [_]Agent{
        security_reviewer.agent(),
        performance_reviewer.agent(),
        maintainability_reviewer.agent(),
    };

    const review_config = CollaborativeConfig{
        .agents = &review_agents,
        .max_rounds = 2,
        .consensus_fn = null, // No consensus check, run all rounds
        .merge_fn = concatenateMerge,
    };

    var code_review = try CollaborativeAgent.init(allocator, review_config, "CodeReviewTeam");
    defer code_review.deinit();

    std.debug.print("\nInput: Review this authentication function\n", .{});

    var msg1 = try Message.withText(allocator, .user, "Review this authentication function");
    defer msg1.deinit();

    const result1 = code_review.agent().process(msg1) catch |err| {
        std.debug.print("Error: {}\n", .{err});
        return;
    };

    switch (result1) {
        .ok => |response| {
            var mutable_response = response;
            defer mutable_response.deinit();
            const response_text = mutable_response.contentAsText() catch "No content";
            std.debug.print("\nCollaborative Review:\n{s}\n", .{response_text});
        },
        .err => |e| {
            std.debug.print("Error: {}\n", .{e});
        },
    }

    // ========================================================================
    // Example 2: Consensus-Driven Decision Making
    // ========================================================================
    std.debug.print("\n\nExample 2: Consensus-Driven Analysis\n", .{});
    std.debug.print("-------------------------------------\n", .{});

    // Create agents that converge on consensus
    var analyst1 = try ReviewerAgent.init(allocator, "Analyst1", "Data");
    defer analyst1.deinit();

    var analyst2 = try ReviewerAgent.init(allocator, "Analyst2", "Statistical");
    defer analyst2.deinit();

    const analyst_agents = [_]Agent{
        analyst1.agent(),
        analyst2.agent(),
    };

    const consensus_config = CollaborativeConfig{
        .agents = &analyst_agents,
        .max_rounds = 3,
        .consensus_fn = exactMatchConsensus, // Stop when responses match
        .merge_fn = firstMerge,
    };

    var analysts = try CollaborativeAgent.init(allocator, consensus_config, "AnalystTeam");
    defer analysts.deinit();

    std.debug.print("\nInput: Analyze quarterly results\n", .{});

    var msg2 = try Message.withText(allocator, .user, "Analyze quarterly results");
    defer msg2.deinit();

    const result2 = analysts.agent().process(msg2) catch |err| {
        std.debug.print("Error: {}\n", .{err});
        std.debug.print("\n=== Collaborative Pattern Complete ===\n\n", .{});
        return;
    };

    switch (result2) {
        .ok => |response| {
            var mutable_response = response;
            defer mutable_response.deinit();
            const response_text = mutable_response.contentAsText() catch "No content";
            std.debug.print("\nAnalysis Result:\n{s}\n", .{response_text});
            std.debug.print("\nNote: Consensus would stop iteration early if responses match\n", .{});
        },
        .err => |e| {
            std.debug.print("Error: {}\n", .{e});
        },
    }

    // ========================================================================
    // Example 3: Iterative Refinement
    // ========================================================================
    std.debug.print("\n\nExample 3: Iterative Improvement\n", .{});
    std.debug.print("---------------------------------\n", .{});

    // Create agents for iterative improvement
    var drafter = try ReviewerAgent.init(allocator, "Drafter", "Initial");
    defer drafter.deinit();

    var editor = try ReviewerAgent.init(allocator, "Editor", "Refinement");
    defer editor.deinit();

    const improvement_agents = [_]Agent{
        drafter.agent(),
        editor.agent(),
    };

    const improvement_config = CollaborativeConfig{
        .agents = &improvement_agents,
        .max_rounds = 3,
        .consensus_fn = null,
        .merge_fn = concatenateMerge,
    };

    var writers = try CollaborativeAgent.init(allocator, improvement_config, "WritingTeam");
    defer writers.deinit();

    std.debug.print("\nInput: Write product description\n", .{});

    var msg3 = try Message.withText(allocator, .user, "Write product description");
    defer msg3.deinit();

    const result3 = writers.agent().process(msg3) catch |err| {
        std.debug.print("Error: {}\n", .{err});
        std.debug.print("\n=== Collaborative Pattern Complete ===\n\n", .{});
        return;
    };

    switch (result3) {
        .ok => |response| {
            var mutable_response = response;
            defer mutable_response.deinit();
            const response_text = mutable_response.contentAsText() catch "No content";
            std.debug.print("\nIterative Improvement Process:\n{s}\n", .{response_text});
            std.debug.print("\nNote: Multiple rounds allow for progressive refinement\n", .{});
        },
        .err => |e| {
            std.debug.print("Error: {}\n", .{e});
        },
    }

    std.debug.print("\n=== Collaborative Pattern Complete ===\n\n", .{});
}
