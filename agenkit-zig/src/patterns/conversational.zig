/// Conversational Pattern - Multi-turn Dialogue Management
///
/// The Conversational pattern maintains context across multiple turns of conversation,
/// managing message history and ensuring responses take into account previous exchanges.
///
/// # Key Concepts
///
/// - **Message History**: Stores previous messages for context
/// - **Context Window**: Limits how many messages to retain
/// - **Automatic Pruning**: Removes oldest messages when limit exceeded
/// - **System Prompt Preservation**: Always keeps system messages
///
/// # Use Cases
///
/// - Chatbots and virtual assistants
/// - Customer support agents
/// - Interactive tutoring systems
/// - Any multi-turn conversation requiring context
///
/// # Example
///
/// ```zig
/// const std = @import("std");
/// const agenkit = @import("agenkit");
///
/// pub fn main() !void {
///     var gpa = std.heap.GeneralPurposeAllocator(.{}){};
///     defer _ = gpa.deinit();
///     const allocator = gpa.allocator();
///
///     var agent = try agenkit.patterns.ConversationalAgent.init(
///         allocator,
///         10, // max_history
///         "You are a helpful assistant.",
///     );
///     defer agent.deinit();
///
///     // First turn
///     var msg1 = try agenkit.Message.withText(allocator, .user, "My name is Alice");
///     defer msg1.deinit();
///     const result1 = try agent.agent().process(msg1);
///     var response1 = try result1.unwrap();
///     defer response1.deinit();
///
///     // Second turn - agent remembers the name
///     var msg2 = try agenkit.Message.withText(allocator, .user, "What's my name?");
///     defer msg2.deinit();
///     const result2 = try agent.agent().process(msg2);
///     var response2 = try result2.unwrap();
///     defer response2.deinit();
/// }
/// ```

const std = @import("std");
const Allocator = std.mem.Allocator;
const Agent = @import("../agent.zig").Agent;
const AgentError = @import("../agent.zig").AgentError;
const Message = @import("../message.zig").Message;
const Role = @import("../message.zig").Role;
const Result = @import("../agent.zig").Result;

/// Helper function to clone a message
fn cloneMessage(allocator: Allocator, msg: Message) !Message {
    const text = try msg.contentAsText();
    return try Message.withText(allocator, msg.role, text);
}

/// Agent that maintains conversation history for context-aware responses
pub const ConversationalAgent = struct {
    allocator: Allocator,
    max_history: usize,
    system_prompt: ?[]const u8,
    include_system: bool,
    history: std.ArrayList(Message),
    agent_name: []const u8,

    pub fn init(
        allocator: Allocator,
        max_history: usize,
        system_prompt: ?[]const u8,
    ) !ConversationalAgent {
        if (max_history == 0) {
            return AgentError.InvalidInput;
        }

        var history = std.ArrayList(Message){};

        // Add system prompt to history if provided
        const system_prompt_copy = if (system_prompt) |prompt|
            try allocator.dupe(u8, prompt)
        else
            null;

        if (system_prompt_copy) |prompt| {
            const sys_msg = try Message.withText(allocator, .system, prompt);
            try history.append(allocator, sys_msg);
        }

        return ConversationalAgent{
            .allocator = allocator,
            .max_history = max_history,
            .system_prompt = system_prompt_copy,
            .include_system = true,
            .history = history,
            .agent_name = try allocator.dupe(u8, "ConversationalAgent"),
        };
    }

    pub fn deinit(self: *ConversationalAgent) void {
        for (self.history.items) |*msg| {
            msg.deinit();
        }
        self.history.deinit(self.allocator);

        if (self.system_prompt) |prompt| {
            self.allocator.free(prompt);
        }

        self.allocator.free(self.agent_name);
    }

    /// Prune history to stay within max_history limit
    /// System messages are preserved, and oldest user/assistant messages are removed first
    fn pruneHistory(self: *ConversationalAgent) !void {
        if (self.history.items.len <= self.max_history) {
            return;
        }

        // Separate system messages from conversation
        var system_messages = std.ArrayList(Message){};
        defer system_messages.deinit(self.allocator);

        var conversation_messages = std.ArrayList(Message){};
        defer conversation_messages.deinit(self.allocator);

        for (self.history.items) |msg| {
            if (msg.role == .system) {
                try system_messages.append(self.allocator, try cloneMessage(self.allocator, msg));
            } else {
                try conversation_messages.append(self.allocator, try cloneMessage(self.allocator, msg));
            }
        }

        // Keep only the most recent conversation messages
        const messages_to_keep = if (self.max_history > system_messages.items.len)
            self.max_history - system_messages.items.len
        else
            0;

        // Clear old history
        for (self.history.items) |*msg| {
            msg.deinit();
        }
        self.history.clearRetainingCapacity();

        // Add system messages back
        for (system_messages.items) |msg| {
            try self.history.append(self.allocator, msg);
        }

        // Add most recent conversation messages
        if (conversation_messages.items.len > messages_to_keep) {
            const skip_count = conversation_messages.items.len - messages_to_keep;
            for (conversation_messages.items[skip_count..]) |msg| {
                try self.history.append(self.allocator, msg);
            }
            // Free skipped messages
            for (conversation_messages.items[0..skip_count]) |*msg| {
                msg.deinit();
            }
        } else {
            for (conversation_messages.items) |msg| {
                try self.history.append(self.allocator, msg);
            }
        }
    }

    /// Clear conversation history
    pub fn clearHistory(self: *ConversationalAgent, keep_system: bool) !void {
        // Free all messages
        for (self.history.items) |*msg| {
            msg.deinit();
        }
        self.history.clearRetainingCapacity();

        // Re-add system prompt if requested
        if (keep_system and self.system_prompt != null) {
            const sys_msg = try Message.withText(self.allocator, .system, self.system_prompt.?);
            try self.history.append(self.allocator, sys_msg);
        }
    }

    /// Get current number of messages in history
    pub fn historyLength(self: *const ConversationalAgent) usize {
        return self.history.items.len;
    }

    /// Simulate LLM response (mock implementation)
    fn simulateLLMResponse(self: *ConversationalAgent, user_input: []const u8) ![]const u8 {
        // Simple mock: echo with context awareness
        if (std.mem.indexOf(u8, user_input, "my name") != null or std.mem.indexOf(u8, user_input, "What's my name") != null) {
            // Look for a name in previous messages
            for (self.history.items) |msg| {
                const content = try msg.contentAsText();
                if (std.mem.indexOf(u8, content, "name is ") != null) {
                    const start = std.mem.indexOf(u8, content, "name is ").? + 8;
                    var end = start;
                    while (end < content.len and !std.ascii.isWhitespace(content[end])) : (end += 1) {}
                    const name = content[start..end];
                    return std.fmt.allocPrint(self.allocator, "Your name is {s}.", .{name});
                }
            }
        }

        // Default response
        return std.fmt.allocPrint(self.allocator, "I heard you say: {s}", .{user_input});
    }

    /// Get the Agent interface for this ConversationalAgent
    pub fn agent(self: *ConversationalAgent) Agent {
        return Agent{
            .ptr = self,
            .vtable = &.{
                .process = processImpl,
                .deinit = deinitImpl,
                .name = nameImpl,
                .capabilities = capabilitiesImpl,
            },
        };
    }

    fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
        const self: *ConversationalAgent = @ptrCast(@alignCast(ptr));

        // Add user message to history
        const msg_clone = cloneMessage(self.allocator, message) catch {
            return AgentError.ProcessingFailed;
        };
        self.history.append(self.allocator, msg_clone) catch {
            return AgentError.ProcessingFailed;
        };

        // Prune history if needed
        self.pruneHistory() catch {
            return AgentError.ProcessingFailed;
        };

        // Get user input
        const user_input = message.contentAsText() catch {
            return AgentError.InvalidInput;
        };

        // Simulate LLM response with context
        const response_text = self.simulateLLMResponse(user_input) catch {
            return AgentError.ProcessingFailed;
        };
        defer self.allocator.free(response_text);

        // Create response message
        const response = Message.withText(self.allocator, .assistant, response_text) catch {
            return AgentError.ProcessingFailed;
        };

        // Add response to history
        const response_clone = cloneMessage(self.allocator, response) catch {
            return AgentError.ProcessingFailed;
        };
        self.history.append(self.allocator, response_clone) catch {
            return AgentError.ProcessingFailed;
        };

        // Prune again after adding response
        self.pruneHistory() catch {
            return AgentError.ProcessingFailed;
        };

        return Result{ .ok = response };
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *ConversationalAgent = @ptrCast(@alignCast(ptr));
        self.deinit();
    }

    fn nameImpl(ptr: *anyopaque) []const u8 {
        const self: *ConversationalAgent = @ptrCast(@alignCast(ptr));
        return self.agent_name;
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const []const u8 {
        _ = ptr;
        const caps = [_][]const u8{ "conversational", "history_management" };
        const result = try allocator.alloc([]const u8, caps.len);
        for (caps, 0..) |cap, i| {
            result[i] = try allocator.dupe(u8, cap);
        }
        return result;
    }
};

// Tests
const testing = std.testing;

test "ConversationalAgent creation" {
    const allocator = testing.allocator;

    var agent = try ConversationalAgent.init(allocator, 10, "You are a helpful assistant.");
    defer agent.deinit();

    try testing.expectEqualStrings("ConversationalAgent", agent.agent_name);
    try testing.expectEqual(@as(usize, 10), agent.max_history);
    try testing.expectEqual(@as(usize, 1), agent.historyLength()); // System message
}

test "ConversationalAgent validation" {
    const allocator = testing.allocator;

    // Test max_history = 0
    const result = ConversationalAgent.init(allocator, 0, null);
    try testing.expectError(AgentError.InvalidInput, result);
}

test "ConversationalAgent history management" {
    const allocator = testing.allocator;

    var agent = try ConversationalAgent.init(allocator, 5, null);
    defer agent.deinit();

    try testing.expectEqual(@as(usize, 0), agent.historyLength());

    // Add user message
    var msg1 = try Message.withText(allocator, .user, "Hello");
    defer msg1.deinit();

    const result1 = try agent.agent().process(msg1);
    var response1 = try result1.unwrap();
    defer response1.deinit();

    // History should have user message + assistant response
    try testing.expectEqual(@as(usize, 2), agent.historyLength());
}

test "ConversationalAgent clearHistory" {
    const allocator = testing.allocator;

    var agent = try ConversationalAgent.init(allocator, 10, "System prompt");
    defer agent.deinit();

    try testing.expectEqual(@as(usize, 1), agent.historyLength());

    var msg = try Message.withText(allocator, .user, "Test");
    defer msg.deinit();

    const result = try agent.agent().process(msg);
    var response = try result.unwrap();
    defer response.deinit();

    try testing.expect(agent.historyLength() > 1);

    try agent.clearHistory(true);
    try testing.expectEqual(@as(usize, 1), agent.historyLength()); // System message remains

    try agent.clearHistory(false);
    try testing.expectEqual(@as(usize, 0), agent.historyLength()); // All cleared
}

test "ConversationalAgent context awareness" {
    const allocator = testing.allocator;

    var agent = try ConversationalAgent.init(allocator, 10, null);
    defer agent.deinit();

    // First turn: user introduces themselves
    var msg1 = try Message.withText(allocator, .user, "My name is Alice");
    defer msg1.deinit();

    const result1 = try agent.agent().process(msg1);
    var response1 = try result1.unwrap();
    defer response1.deinit();

    // Second turn: ask about name
    var msg2 = try Message.withText(allocator, .user, "What's my name?");
    defer msg2.deinit();

    const result2 = try agent.agent().process(msg2);
    var response2 = try result2.unwrap();
    defer response2.deinit();

    const content = try response2.contentAsText();
    try testing.expect(std.mem.indexOf(u8, content, "Alice") != null);
}

test "ConversationalAgent pruning" {
    const allocator = testing.allocator;

    var agent = try ConversationalAgent.init(allocator, 3, "System");
    defer agent.deinit();

    // Add 4 messages (will exceed max_history of 3)
    var msg1 = try Message.withText(allocator, .user, "Message 1");
    defer msg1.deinit();
    const result1 = try agent.agent().process(msg1);
    var response1 = try result1.unwrap();
    defer response1.deinit();

    var msg2 = try Message.withText(allocator, .user, "Message 2");
    defer msg2.deinit();
    const result2 = try agent.agent().process(msg2);
    var response2 = try result2.unwrap();
    defer response2.deinit();

    // Should prune but keep system message
    // After processing 2 messages, we should have system + up to 2 messages within limit
    try testing.expect(agent.historyLength() <= 3);

    // Verify system message is still present if history is not empty
    if (agent.historyLength() > 0) {
        try testing.expectEqual(Role.system, agent.history.items[0].role);
    }
}
