/// DurableAgent wraps agent with automatic checkpointing and resumption capability.
///
/// Features:
///   - Automatic checkpointing (every N steps or on demand)
///   - Resumption from latest checkpoint on startup
///   - State persistence across restarts
///   - Error recovery with checkpoint rollback
///
/// Example:
///   var storage = try FileStorage.init(allocator, "./checkpoints");
///   defer storage.deinit();
///
///   var durable = try DurableAgent.init(
///       allocator,
///       agent,
///       storage.storage(),
///       10,  // Checkpoint every 10 steps
///       true, // Auto-resumption
///   );
///   defer durable.deinit();
///
///   const response = try durable.process(message, "session-1");
const std = @import("std");
const Allocator = std.mem.Allocator;
const Message = @import("../../message.zig").Message;
const Agent = @import("../../agent.zig").Agent;
const AgentError = @import("../../agent.zig").AgentError;
const Result = @import("../../agent.zig").Result;
const StreamCallbacks = @import("../../agent.zig").StreamCallbacks;
const IntrospectionResult = @import("../../introspection.zig").IntrospectionResult;
const Checkpoint = @import("checkpoint.zig").Checkpoint;
const CheckpointStorage = @import("storage.zig").CheckpointStorage;
const CheckpointManager = @import("manager.zig").CheckpointManager;

/// SessionState tracks state for a single session
const SessionState = struct {
    state: std.json.ObjectMap,
    steps: usize,
    messages: std.ArrayList(Message),
    resumed: bool,

    fn init(allocator: Allocator) SessionState {
        _ = allocator; // containers start empty (unmanaged); allocator supplied at use sites
        return .{
            .state = std.json.ObjectMap.empty,
            .steps = 0,
            .messages = .empty,
            .resumed = false,
        };
    }

    fn deinit(self: *SessionState, allocator: Allocator) void {
        self.state.deinit(allocator);
        for (self.messages.items) |*msg| {
            msg.deinit();
        }
        self.messages.deinit(allocator);
    }
};

pub const DurableAgent = struct {
    allocator: Allocator,
    inner_agent: Agent,
    agent_name: []const u8,
    checkpoint_interval: usize,
    auto_resume: bool,
    manager: CheckpointManager,
    sessions: std.StringHashMap(SessionState),

    /// Create a new durable agent.
    ///
    /// Args:
    ///   allocator: Memory allocator
    ///   agent: Agent to wrap
    ///   storage: Checkpoint storage
    ///   checkpoint_interval: Checkpoint every N steps
    ///   auto_resume: Automatically restore from latest checkpoint on first call
    pub fn init(
        allocator: Allocator,
        wrapped_agent: Agent,
        storage: CheckpointStorage,
        checkpoint_interval: usize,
        auto_resume: bool,
    ) !DurableAgent {
        const agent_name = try allocator.dupe(u8, wrapped_agent.name());

        return .{
            .allocator = allocator,
            .inner_agent = wrapped_agent,
            .agent_name = agent_name,
            .checkpoint_interval = checkpoint_interval,
            .auto_resume = auto_resume,
            .manager = CheckpointManager.init(allocator, storage, checkpoint_interval),
            .sessions = std.StringHashMap(SessionState).init(allocator),
        };
    }

    pub fn deinit(self: *DurableAgent) void {
        self.allocator.free(self.agent_name);
        self.manager.deinit();

        // Free all sessions
        var iter = self.sessions.valueIterator();
        while (iter.next()) |session| {
            session.deinit(self.allocator);
        }
        self.sessions.deinit();
    }

    /// Process message with automatic checkpointing.
    ///
    /// Args:
    ///   message: Input message
    ///   session_id: Session identifier
    ///
    /// Returns:
    ///   Response message
    pub fn processWithSession(self: *DurableAgent, message: Message, session_id: []const u8) !Result {
        // Auto-restore on first call if enabled
        if (self.auto_resume) {
            const session = self.sessions.getPtr(session_id);
            if (session == null or !session.?.resumed) {
                _ = self.resumeFromCheckpoint(session_id, null) catch |err| {
                    std.log.warn("Failed to auto-restore: {}", .{err});
                };
                if (self.sessions.getPtr(session_id)) |s| {
                    s.resumed = true;
                }
            }
        }

        // Initialize session if needed
        if (!self.sessions.contains(session_id)) {
            try self.sessions.put(session_id, SessionState.init(self.allocator));
        }

        const session = self.sessions.getPtr(session_id).?;

        // Increment step
        session.steps += 1;
        const current_step = session.steps;

        // Add message to history (make a copy)
        const message_copy = try Message.withText(self.allocator, message.role, try message.contentAsText());
        try session.messages.append(self.allocator, message_copy);

        // Process message
        const result = self.inner_agent.process(message) catch |err| {
            std.log.err("Error processing message at step {d}: {}", .{ current_step, err });

            // Try to rollback to last checkpoint
            const latest = self.manager.getLatest(session_id) catch null;
            if (latest) |chkpt| {
                defer {
                    chkpt.deinit();
                    self.allocator.destroy(chkpt);
                }
                std.log.info("Rolling back to checkpoint at step {d}", .{chkpt.step_number});
                _ = self.resumeFromCheckpoint(session_id, chkpt.checkpoint_id) catch |resume_err| {
                    std.log.warn("Failed to rollback: {}", .{resume_err});
                };
            }

            return err;
        };

        const response = try result.unwrap();

        // Add response to history (make a copy)
        const response_copy = try Message.withText(self.allocator, response.role, try response.contentAsText());
        try session.messages.append(self.allocator, response_copy);

        // Update state
        try self.updateState(session_id, &message, &response);

        // Checkpoint if needed
        if (self.manager.shouldCheckpoint(session_id, current_step)) {
            if (self.checkpoint(session_id, null)) |checkpoint_id| {
                self.allocator.free(checkpoint_id);
            } else |err| {
                std.log.warn("Failed to create checkpoint: {}", .{err});
            }
        }

        return result;
    }

    /// Create checkpoint for current state.
    ///
    /// Args:
    ///   session_id: Session identifier
    ///   metadata: Optional metadata to attach
    ///
    /// Returns:
    ///   checkpoint_id: Unique checkpoint identifier
    pub fn checkpoint(self: *DurableAgent, session_id: []const u8, metadata: ?std.json.Value) ![]const u8 {
        const session = self.sessions.get(session_id) orelse return error.SessionNotFound;

        const checkpoint_id = try self.manager.createCheckpoint(
            session_id,
            self.agent_name,
            session.steps,
            std.json.Value{ .object = session.state },
            session.messages.items,
            metadata,
            null,
        );

        std.log.info("Checkpointed session {s} at step {d}", .{ session_id, session.steps });

        return checkpoint_id;
    }

    /// Restore from checkpoint.
    ///
    /// Args:
    ///   session_id: Session identifier
    ///   checkpoint_id: Specific checkpoint to restore from (null = latest)
    ///
    /// Returns:
    ///   Restored state or null if no checkpoint found
    pub fn resumeFromCheckpoint(self: *DurableAgent, session_id: []const u8, checkpoint_id: ?[]const u8) !?std.json.Value {
        // Load checkpoint
        const chkpt = if (checkpoint_id) |cid|
            try self.manager.loadCheckpoint(cid)
        else
            try self.manager.getLatest(session_id);

        if (chkpt == null) {
            std.log.info("No checkpoint found for {s}, starting fresh", .{session_id});
            return null;
        }

        defer {
            chkpt.?.deinit();
            self.allocator.destroy(chkpt.?);
        }

        // Get or create session
        const gop = try self.sessions.getOrPut(session_id);
        if (!gop.found_existing) {
            gop.value_ptr.* = SessionState.init(self.allocator);
        }

        const session = gop.value_ptr;

        // Clear old state
        session.state.deinit(self.allocator);
        session.state = std.json.ObjectMap.empty;

        // Restore state
        var iter = chkpt.?.state.object.iterator();
        while (iter.next()) |entry| {
            try session.state.put(self.allocator, entry.key_ptr.*, entry.value_ptr.*);
        }

        session.steps = chkpt.?.step_number;

        // Restore messages
        for (session.messages.items) |*msg| {
            msg.deinit();
        }
        session.messages.clearRetainingCapacity();

        for (chkpt.?.messages) |msg| {
            const msg_copy = try Message.withText(self.allocator, msg.role, try msg.contentAsText());
            try session.messages.append(self.allocator, msg_copy);
        }

        std.log.info("Resumed session {s} from checkpoint at step {d}", .{
            session_id,
            chkpt.?.step_number,
        });

        return std.json.Value{ .object = session.state };
    }

    /// Get current state for session.
    pub fn getState(self: *DurableAgent, session_id: []const u8) ?std.json.Value {
        const session = self.sessions.get(session_id) orelse return null;
        return std.json.Value{ .object = session.state };
    }

    /// Set state for session.
    pub fn setState(self: *DurableAgent, session_id: []const u8, state: std.json.ObjectMap) !void {
        const gop = try self.sessions.getOrPut(session_id);
        if (!gop.found_existing) {
            gop.value_ptr.* = SessionState.init(self.allocator);
        }

        const session = gop.value_ptr;
        session.state.deinit();
        session.state = state;
    }

    /// Get message history for session.
    pub fn getMessages(self: *DurableAgent, session_id: []const u8, allocator: Allocator) ![]Message {
        const session = self.sessions.get(session_id) orelse {
            return try allocator.alloc(Message, 0);
        };

        const messages = try allocator.alloc(Message, session.messages.items.len);
        for (session.messages.items, 0..) |msg, i| {
            messages[i] = try Message.withText(allocator, msg.role, try msg.contentAsText());
        }

        return messages;
    }

    /// Reset session (clear state and messages).
    pub fn resetSession(self: *DurableAgent, session_id: []const u8) void {
        if (self.sessions.getPtr(session_id)) |session| {
            session.deinit(self.allocator);
            _ = self.sessions.remove(session_id);
        }
    }

    /// Update session state (can be overridden for custom state tracking).
    ///
    /// Default implementation tracks message count and last message.
    fn updateState(self: *DurableAgent, session_id: []const u8, input_message: *const Message, output_message: *const Message) !void {
        const session = self.sessions.getPtr(session_id).?;

        // Update basic stats
        const message_count_val = session.state.get("message_count") orelse std.json.Value{ .integer = 0 };
        const message_count = if (message_count_val == .integer) @as(i64, message_count_val.integer) else 0;

        try session.state.put(self.allocator, "message_count", std.json.Value{ .integer = message_count + 1 });

        const input_text = try input_message.contentAsText();
        const output_text = try output_message.contentAsText();

        try session.state.put(self.allocator, "last_input", std.json.Value{ .string = input_text });
        try session.state.put(self.allocator, "last_output", std.json.Value{ .string = output_text });
    }

    /// List checkpoints for session.
    pub fn listCheckpoints(self: *DurableAgent, session_id: []const u8, limit: usize) ![]const *Checkpoint {
        return try self.manager.listCheckpoints(session_id, limit);
    }

    /// Delete all checkpoints for session.
    pub fn deleteCheckpoints(self: *DurableAgent, session_id: []const u8) !usize {
        const count = try self.manager.deleteSession(session_id);
        self.resetSession(session_id);
        return count;
    }

    /// Get statistics for session.
    pub fn getSessionStats(self: *DurableAgent, session_id: []const u8) !std.json.Value {
        var checkpoint_stats = try self.manager.getSessionStats(session_id);

        const session = self.sessions.get(session_id);
        if (session) |s| {
            try checkpoint_stats.object.put(self.allocator, "current_step", std.json.Value{ .integer = @intCast(s.steps) });
            try checkpoint_stats.object.put(self.allocator, "message_count", std.json.Value{ .integer = @intCast(s.messages.items.len) });
            try checkpoint_stats.object.put(self.allocator, "state_size", std.json.Value{ .integer = @intCast(s.state.count()) });
        }

        return checkpoint_stats;
    }

    /// Get agent interface for this durable agent.
    pub fn agent(self: *DurableAgent) Agent {
        return .{
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
        const self: *DurableAgent = @ptrCast(@alignCast(ptr));
        return self.agent_name;
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const []const u8 {
        const self: *DurableAgent = @ptrCast(@alignCast(ptr));
        return self.inner_agent.capabilities(allocator);
    }

    fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
        const self: *DurableAgent = @ptrCast(@alignCast(ptr));
        // Use a default session ID if not provided
        return self.processWithSession(message, "default") catch {
            return AgentError.ProcessingFailed;
        };
    }

    fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: StreamCallbacks) AgentError!void {
        const self: *DurableAgent = @ptrCast(@alignCast(ptr));
        return self.inner_agent.processStream(message, callbacks);
    }

    fn introspectImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error!IntrospectionResult {
        const self: *DurableAgent = @ptrCast(@alignCast(ptr));
        return self.inner_agent.introspect(allocator);
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *DurableAgent = @ptrCast(@alignCast(ptr));
        self.deinit();
    }
};

// Tests
test "DurableAgent creation" {
    const allocator = std.testing.allocator;
    const EchoAgent = @import("../../agent.zig").EchoAgent;
    const InMemoryStorage = @import("storage.zig").InMemoryStorage;

    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();

    var storage = InMemoryStorage.init(allocator);
    defer storage.deinit();

    var durable = try DurableAgent.init(
        allocator,
        echo.agent(),
        storage.storage(),
        5,
        true,
    );
    defer durable.deinit();

    try std.testing.expectEqualStrings("echo", durable.agent_name);
    try std.testing.expectEqual(@as(usize, 5), durable.checkpoint_interval);
}

test "DurableAgent checkpoint and resume" {
    const allocator = std.testing.allocator;
    const EchoAgent = @import("../../agent.zig").EchoAgent;
    const InMemoryStorage = @import("storage.zig").InMemoryStorage;

    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();

    var storage = InMemoryStorage.init(allocator);
    defer storage.deinit();

    var durable = try DurableAgent.init(
        allocator,
        echo.agent(),
        storage.storage(),
        0, // Manual checkpointing
        false,
    );
    defer durable.deinit();

    // Process a message
    var msg = try Message.withText(allocator, .user, "Hello");
    defer msg.deinit();

    const result = try durable.processWithSession(msg, "test-session");
    var response = try result.unwrap();
    defer response.deinit();

    // Create checkpoint
    const checkpoint_id = try durable.checkpoint("test-session", null);
    defer allocator.free(checkpoint_id);

    // Reset session
    durable.resetSession("test-session");

    // Restore from checkpoint
    const state = try durable.resumeFromCheckpoint("test-session", null);
    try std.testing.expect(state != null);

    // Verify state was restored
    const session = durable.sessions.get("test-session");
    try std.testing.expect(session != null);
    try std.testing.expectEqual(@as(usize, 1), session.?.steps);
}
