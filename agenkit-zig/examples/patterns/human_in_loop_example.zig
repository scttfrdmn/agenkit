//! Human-in-Loop Pattern Example
//!
//! This example demonstrates the Human-in-Loop pattern for adding human
//! approval gates to agent decisions based on confidence levels.
//!
//! Build: zig build
//! Run: zig build run-human-in-loop

const std = @import("std");
const agenkit = @import("agenkit");

const Agent = agenkit.Agent;
const Message = agenkit.Message;
const HumanInLoopAgent = agenkit.patterns.HumanInLoopAgent;
const HumanInLoopConfig = agenkit.patterns.HumanInLoopConfig;
const ApprovalRequest = agenkit.patterns.ApprovalRequest;
const ApprovalResponse = agenkit.patterns.ApprovalResponse;
const alwaysApprove = agenkit.patterns.alwaysApprove;

/// Mock agent that returns responses with varying confidence
const ConfidenceAgent = struct {
    allocator: std.mem.Allocator,
    name: []const u8,
    confidence: f32,

    pub fn init(allocator: std.mem.Allocator, name: []const u8, confidence: f32) !*ConfidenceAgent {
        const self = try allocator.create(ConfidenceAgent);
        self.* = .{
            .allocator = allocator,
            .name = try allocator.dupe(u8, name),
            .confidence = confidence,
        };
        return self;
    }

    pub fn agent(self: *ConfidenceAgent) Agent {
        return Agent{
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
        const self: *ConfidenceAgent = @ptrCast(@alignCast(ptr));
        return self.name;
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: std.mem.Allocator) std.mem.Allocator.Error![]const []const u8 {
        _ = ptr;
        const caps = try allocator.alloc([]const u8, 1);
        caps[0] = try allocator.dupe(u8, "mock");
        return caps;
    }

    fn processImpl(ptr: *anyopaque, message: Message) agenkit.AgentError!agenkit.Result {
        const self: *ConfidenceAgent = @ptrCast(@alignCast(ptr));

        const content = message.contentAsText() catch return agenkit.AgentError.ProcessingFailed;

        // Build response with confidence indicator
        const response = std.fmt.allocPrint(
            self.allocator,
            "Processed: {s} (confidence: {d:.2})",
            .{ content, self.confidence },
        ) catch return agenkit.AgentError.ProcessingFailed;
        defer self.allocator.free(response);

        const response_msg = Message.withText(self.allocator, .assistant, response) catch return agenkit.AgentError.ProcessingFailed;

        // TODO: In full implementation, would add confidence to metadata
        return agenkit.Result{ .ok = response_msg };
    }

    fn introspectImpl(ptr: *anyopaque, allocator: std.mem.Allocator) std.mem.Allocator.Error!agenkit.IntrospectionResult {
        const self: *ConfidenceAgent = @ptrCast(@alignCast(ptr));
        const caps = try capabilitiesImpl(ptr, allocator);
        defer allocator.free(caps);
        return agenkit.createDefaultIntrospectionResult(allocator, self.name, caps);
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *ConfidenceAgent = @ptrCast(@alignCast(ptr));
        self.deinit();
    }

    pub fn deinit(self: *ConfidenceAgent) void {
        self.allocator.free(self.name);
        self.allocator.destroy(self);
    }
};

/// Simple approval function that logs and approves
fn loggingApprovalFn(request: ApprovalRequest) agenkit.AgentError!ApprovalResponse {
    const content = request.message.contentAsText() catch "Unable to extract content";
    std.debug.print("  [APPROVAL REQUESTED] Confidence: {d:.2}\n", .{request.confidence});
    std.debug.print("  [APPROVAL REQUESTED] Content: {s}\n", .{content});
    std.debug.print("  [DECISION] APPROVED\n", .{});

    return ApprovalResponse{
        .approved = true,
        .feedback = null,
        .modified_message = null,
    };
}

/// Approval function that rejects low confidence
fn strictApprovalFn(request: ApprovalRequest) agenkit.AgentError!ApprovalResponse {
    const content = request.message.contentAsText() catch "Unable to extract content";
    std.debug.print("  [APPROVAL REQUESTED] Confidence: {d:.2}\n", .{request.confidence});
    std.debug.print("  [APPROVAL REQUESTED] Content: {s}\n", .{content});

    if (request.confidence < 0.6) {
        std.debug.print("  [DECISION] REJECTED (confidence too low)\n", .{});
        return ApprovalResponse{
            .approved = false,
            .feedback = null,
            .modified_message = null,
        };
    }

    std.debug.print("  [DECISION] APPROVED\n", .{});
    return ApprovalResponse{
        .approved = true,
        .feedback = null,
        .modified_message = null,
    };
}

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("\n=== Human-in-Loop Pattern Example ===\n\n", .{});

    // ========================================================================
    // Example 1: High Confidence - Bypass Approval
    // ========================================================================
    std.debug.print("Example 1: High Confidence - Automatic Approval\n", .{});
    std.debug.print("------------------------------------------------\n", .{});

    var high_conf_agent = try ConfidenceAgent.init(allocator, "HighConfAgent", 0.95);
    defer high_conf_agent.deinit();

    const high_conf_config = HumanInLoopConfig{
        .agent = high_conf_agent.agent(),
        .approval_threshold = 0.8,
        .approval_fn = loggingApprovalFn,
        .confidence_key = "confidence",
    };

    var hitl1 = try HumanInLoopAgent.init(allocator, high_conf_config, "HITL1");
    defer hitl1.deinit();

    std.debug.print("\nInput: Approve large transaction\n", .{});
    std.debug.print("Agent confidence: 0.95 (above threshold 0.8)\n", .{});
    std.debug.print("Expected: Automatic approval without human review\n\n", .{});

    var msg1 = try Message.withText(allocator, .user, "Approve large transaction");
    defer msg1.deinit();

    const result1 = hitl1.agent().process(msg1) catch |err| {
        std.debug.print("Error: {}\n", .{err});
        return;
    };

    switch (result1) {
        .ok => |response| {
            var mutable_response = response;
            defer mutable_response.deinit();
            const response_text = mutable_response.contentAsText() catch "No content";
            std.debug.print("Result: {s}\n", .{response_text});
            std.debug.print("Status: Bypassed approval (high confidence)\n", .{});
        },
        .err => |e| {
            std.debug.print("Error: {}\n", .{e});
        },
    }

    // ========================================================================
    // Example 2: Low Confidence - Require Approval
    // ========================================================================
    std.debug.print("\n\nExample 2: Low Confidence - Human Approval Required\n", .{});
    std.debug.print("----------------------------------------------------\n", .{});

    var low_conf_agent = try ConfidenceAgent.init(allocator, "LowConfAgent", 0.65);
    defer low_conf_agent.deinit();

    const low_conf_config = HumanInLoopConfig{
        .agent = low_conf_agent.agent(),
        .approval_threshold = 0.8,
        .approval_fn = loggingApprovalFn,
        .confidence_key = "confidence",
    };

    var hitl2 = try HumanInLoopAgent.init(allocator, low_conf_config, "HITL2");
    defer hitl2.deinit();

    std.debug.print("\nInput: Deploy to production\n", .{});
    std.debug.print("Agent confidence: 0.65 (below threshold 0.8)\n", .{});
    std.debug.print("Expected: Human approval required\n\n", .{});

    var msg2 = try Message.withText(allocator, .user, "Deploy to production");
    defer msg2.deinit();

    const result2 = hitl2.agent().process(msg2) catch |err| {
        std.debug.print("Error: {}\n", .{err});
        std.debug.print("\n=== Human-in-Loop Pattern Complete ===\n\n", .{});
        return;
    };

    switch (result2) {
        .ok => |response| {
            var mutable_response = response;
            defer mutable_response.deinit();
            const response_text = mutable_response.contentAsText() catch "No content";
            std.debug.print("Result: {s}\n", .{response_text});
            std.debug.print("Status: Approved after human review\n", .{});
        },
        .err => |e| {
            std.debug.print("Error: {}\n", .{e});
        },
    }

    // ========================================================================
    // Example 3: Very Low Confidence - Strict Rejection
    // ========================================================================
    std.debug.print("\n\nExample 3: Very Low Confidence - Strict Approval Policy\n", .{});
    std.debug.print("--------------------------------------------------------\n", .{});

    var very_low_conf_agent = try ConfidenceAgent.init(allocator, "VeryLowConfAgent", 0.45);
    defer very_low_conf_agent.deinit();

    const strict_config = HumanInLoopConfig{
        .agent = very_low_conf_agent.agent(),
        .approval_threshold = 0.8,
        .approval_fn = strictApprovalFn,
        .confidence_key = "confidence",
    };

    var hitl3 = try HumanInLoopAgent.init(allocator, strict_config, "HITL3");
    defer hitl3.deinit();

    std.debug.print("\nInput: Execute critical operation\n", .{});
    std.debug.print("Agent confidence: 0.45 (far below threshold 0.8)\n", .{});
    std.debug.print("Expected: Rejection due to low confidence\n\n", .{});

    var msg3 = try Message.withText(allocator, .user, "Execute critical operation");
    defer msg3.deinit();

    const result3 = hitl3.agent().process(msg3) catch |err| {
        std.debug.print("\nResult: Operation rejected ({})\n", .{err});
        std.debug.print("Status: Confidence too low for approval\n", .{});
        std.debug.print("\n=== Human-in-Loop Pattern Complete ===\n\n", .{});
        return;
    };

    switch (result3) {
        .ok => |response| {
            var mutable_response = response;
            defer mutable_response.deinit();
            const response_text = mutable_response.contentAsText() catch "No content";
            std.debug.print("Result: {s}\n", .{response_text});
        },
        .err => |e| {
            std.debug.print("Error: {}\n", .{e});
        },
    }

    std.debug.print("\n=== Human-in-Loop Pattern Complete ===\n\n", .{});
}
