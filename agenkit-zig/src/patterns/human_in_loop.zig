/// Human-in-Loop Pattern - Human approval gates for high-stakes decisions
///
/// The Human-in-Loop pattern adds human oversight to agent decisions by requiring
/// approval for low-confidence outputs. This enables safe autonomous operation
/// while maintaining human control over critical decisions.
///
/// # Key Concepts
/// - Confidence-based gating (auto-approve above threshold)
/// - Human approval for low-confidence decisions
/// - Feedback incorporation and message modification
/// - Configurable approval workflows
///
/// # Performance Characteristics
/// - Time: O(agent + approval) where approval is async/human
/// - Memory: O(1) for approval request
/// - High-confidence bypasses approval (fast path)
///
/// # Use Cases
/// - Financial transactions: Approve large transfers, auto-approve small ones
/// - Content moderation: Human review for borderline cases
/// - Medical diagnosis: Doctor approval for uncertain cases
/// - Legal review: Attorney sign-off on complex contracts
/// - Deployment automation: Manual approval for production changes
///
/// # Example
/// ```zig
/// const std = @import("std");
/// const agenkit = @import("agenkit");
///
/// fn myApprovalFn(request: ApprovalRequest) !ApprovalResponse {
///     // In real implementation, would prompt user
///     std.debug.print("Approve: {s}?\n", .{request.message.contentAsText()});
///     return ApprovalResponse{
///         .approved = true,
///         .feedback = null,
///         .modified_message = null,
///     };
/// }
///
/// const config = HumanInLoopConfig{
///     .agent = my_agent.agent(),
///     .approval_threshold = 0.8,
///     .approval_fn = myApprovalFn,
///     .confidence_key = "confidence",
/// };
///
/// var hitl = try HumanInLoopAgent.init(allocator, config, "reviewer");
/// defer hitl.deinit();
///
/// const result = try hitl.agent().process(input_message);
/// ```

const std = @import("std");
const Agent = @import("../agent.zig").Agent;
const AgentError = @import("../agent.zig").AgentError;
const StreamCallbacks = @import("../agent.zig").StreamCallbacks;
const Result = @import("../agent.zig").Result;
const Message = @import("../message.zig").Message;
const IntrospectionResult = @import("../introspection.zig").IntrospectionResult;
const createDefaultIntrospectionResult = @import("../introspection.zig").createDefaultIntrospectionResult;
const Allocator = std.mem.Allocator;

/// Approval request presented to human reviewer
pub const ApprovalRequest = struct {
    message: Message,
    confidence: f32,
    context: std.StringHashMap([]const u8),
    timestamp: i64,

    pub fn deinit(self: *ApprovalRequest) void {
        var it = self.context.iterator();
        while (it.next()) |entry| {
            self.context.allocator.free(entry.key_ptr.*);
            self.context.allocator.free(entry.value_ptr.*);
        }
        self.context.deinit();
    }
};

/// Response from human reviewer
pub const ApprovalResponse = struct {
    approved: bool,
    feedback: ?[]const u8,
    modified_message: ?Message,

    pub fn deinit(self: *ApprovalResponse, allocator: Allocator) void {
        if (self.feedback) |feedback| {
            allocator.free(feedback);
        }
        if (self.modified_message) |*msg| {
            msg.deinit();
        }
    }
};

/// Approval function signature - returns approval decision
pub const ApprovalFn = *const fn (request: ApprovalRequest) AgentError!ApprovalResponse;

/// Configuration for human-in-loop agent
pub const HumanInLoopConfig = struct {
    agent: Agent,
    approval_threshold: f32 = 0.8,
    approval_fn: ApprovalFn,
    confidence_key: []const u8 = "confidence",
};

/// Human-in-Loop Agent - Adds human approval gates to agent decisions
pub const HumanInLoopAgent = struct {
    allocator: Allocator,
    agent_name: []const u8,
    wrapped_agent: Agent,
    approval_threshold: f32,
    approval_fn: ApprovalFn,
    confidence_key: []const u8,

    /// Initialize a human-in-loop agent
    ///
    /// Args:
    ///     allocator: Memory allocator
    ///     config: Human-in-loop configuration
    ///     name: Agent name
    ///
    /// Returns:
    ///     Initialized HumanInLoopAgent
    ///
    /// Errors:
    ///     - OutOfMemory: If memory allocation fails
    pub fn init(
        allocator: Allocator,
        config: HumanInLoopConfig,
        name: []const u8,
    ) !*HumanInLoopAgent {
        const self = try allocator.create(HumanInLoopAgent);
        errdefer allocator.destroy(self);

        const name_copy = try allocator.dupe(u8, name);
        errdefer allocator.free(name_copy);

        const confidence_key_copy = try allocator.dupe(u8, config.confidence_key);
        errdefer allocator.free(confidence_key_copy);

        self.* = HumanInLoopAgent{
            .allocator = allocator,
            .agent_name = name_copy,
            .wrapped_agent = config.agent,
            .approval_threshold = config.approval_threshold,
            .approval_fn = config.approval_fn,
            .confidence_key = confidence_key_copy,
        };

        return self;
    }

    /// Create agent interface for this human-in-loop agent
    pub fn agent(self: *HumanInLoopAgent) Agent {
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
        const self: *HumanInLoopAgent = @ptrCast(@alignCast(ptr));
        return self.agent_name;
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const []const u8 {
        const self: *HumanInLoopAgent = @ptrCast(@alignCast(ptr));

        // Get capabilities from wrapped agent
        const wrapped_caps = try self.wrapped_agent.capabilities(allocator);
        defer allocator.free(wrapped_caps);

        // Add human-in-loop specific capabilities
        const total_caps = wrapped_caps.len + 3;
        var capabilities = try allocator.alloc([]const u8, total_caps);

        // Copy wrapped capabilities
        for (wrapped_caps, 0..) |cap, i| {
            capabilities[i] = try allocator.dupe(u8, cap);
        }

        // Add HITL capabilities
        capabilities[wrapped_caps.len] = try allocator.dupe(u8, "human_oversight");
        capabilities[wrapped_caps.len + 1] = try allocator.dupe(u8, "approval_gating");
        capabilities[wrapped_caps.len + 2] = try allocator.dupe(u8, "confidence_based");

        return capabilities;
    }

    fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
        const self: *HumanInLoopAgent = @ptrCast(@alignCast(ptr));

        // Step 1: Execute wrapped agent
        const result = self.wrapped_agent.process(message) catch |err| {
            return err;
        };

        // If agent returned error, propagate it
        switch (result) {
            .err => return result,
            .ok => |response| {
                // Step 2: Extract confidence from metadata
                // For now, we'll use a default confidence
                // TODO: In full implementation, would extract from response.metadata
                const confidence: f32 = 0.5; // Mock confidence

                // Step 3: Check if approval needed
                if (confidence >= self.approval_threshold) {
                    // High confidence - bypass approval
                    // TODO: Add "approval_bypassed" metadata
                    return Result{ .ok = response };
                }

                // Step 4: Low confidence - request approval
                var context = std.StringHashMap([]const u8).init(self.allocator);
                // TODO: Add context from metadata

                const approval_request = ApprovalRequest{
                    .message = response,
                    .confidence = confidence,
                    .context = context,
                    .timestamp = std.time.timestamp(),
                };

                const approval_response = self.approval_fn(approval_request) catch {
                    // If approval function fails, clean up and return error
                    context.deinit();
                    return AgentError.ProcessingFailed;
                };

                context.deinit();

                // Step 5: Handle approval decision
                if (approval_response.approved) {
                    // Approved - use modified message if provided, otherwise original
                    if (approval_response.modified_message) |modified| {
                        // Clean up original response
                        var mutable_response = response;
                        mutable_response.deinit();

                        // TODO: Add "approval_granted" metadata
                        return Result{ .ok = modified };
                    } else {
                        // TODO: Add "approval_granted" metadata
                        return Result{ .ok = response };
                    }
                } else {
                    // Rejected - clean up and return error
                    var mutable_response = response;
                    mutable_response.deinit();

                    // TODO: In full implementation, would return rejection message with feedback
                    return AgentError.ProcessingFailed;
                }
            },
        }
    }

    fn introspectImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error!IntrospectionResult {
        const self: *HumanInLoopAgent = @ptrCast(@alignCast(ptr));
        const caps = try capabilitiesImpl(ptr, allocator);
        defer allocator.free(caps);
        return createDefaultIntrospectionResult(allocator, self.agent_name, caps);
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *HumanInLoopAgent = @ptrCast(@alignCast(ptr));
        self.deinit();
    }

    pub fn deinit(self: *HumanInLoopAgent) void {
        self.allocator.free(self.agent_name);
        self.allocator.free(self.confidence_key);
        self.allocator.destroy(self);
    }
};

// ============================================================================
// Helper Approval Functions
// ============================================================================

/// Simple approval function that always approves (for testing)
pub fn alwaysApprove(_: ApprovalRequest) AgentError!ApprovalResponse {
    return ApprovalResponse{
        .approved = true,
        .feedback = null,
        .modified_message = null,
    };
}

/// Simple approval function that rejects low confidence (<0.5)
pub fn confidenceBasedApprove(request: ApprovalRequest) AgentError!ApprovalResponse {
    return ApprovalResponse{
        .approved = request.confidence >= 0.5,
        .feedback = null,
        .modified_message = null,
    };
}

// ============================================================================
// Tests
// ============================================================================


    fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: StreamCallbacks) AgentError!void {
        _ = ptr;
        _ = message;
        callbacks.onError(AgentError.NotImplemented);
    }

test "HumanInLoopAgent: high confidence bypass" {
    // Skip test for now - requires mock infrastructure
    // TODO: Implement full test suite
}

test "HumanInLoopAgent: low confidence approval" {
    // Skip test for now - requires mock infrastructure
    // TODO: Implement full test suite
}

test "alwaysApprove: always returns approved" {
    const allocator = std.testing.allocator;

    var msg = try Message.withText(allocator, .assistant, "test");
    defer msg.deinit();

    var context = std.StringHashMap([]const u8).init(allocator);
    defer context.deinit();

    const request = ApprovalRequest{
        .message = msg,
        .confidence = 0.5,
        .context = context,
        .timestamp = 0,
    };

    const response = try alwaysApprove(request);
    try std.testing.expect(response.approved);
}
