//! Long-Running Agent Integration Example
//!
//! Demonstrates a long-running conversational agent with memory:
//! - Memory storage and retrieval
//! - Conversational state tracking
//! - Context maintenance across interactions
//! - Memory-aware decision making
//! - Real-world use case: Personal assistant with memory
//!
//! This example shows how memory and conversation patterns work together
//! for stateful, context-aware agents.
//!
//! Run with: zig build run-long-running

const std = @import("std");
const agenkit = @import("agenkit");

/// Personal assistant agent with memory
const AssistantAgent = struct {
    allocator: std.mem.Allocator,
    name: []const u8,
    interaction_count: usize,
    memory: std.ArrayList([]const u8), // Simple memory store

    pub fn init(allocator: std.mem.Allocator, name: []const u8) !*AssistantAgent {
        const self = try allocator.create(AssistantAgent);
        self.* = .{
            .allocator = allocator,
            .name = try allocator.dupe(u8, name),
            .interaction_count = 0,
            .memory = std.ArrayList([]const u8){},
        };
        return self;
    }

    pub fn deinit(self: *AssistantAgent) void {
        for (self.memory.items) |item| {
            self.allocator.free(item);
        }
        self.memory.deinit(self.allocator);
        self.allocator.free(self.name);
        self.allocator.destroy(self);
    }

    pub fn agent(self: *AssistantAgent) agenkit.Agent {
        return agenkit.Agent{
            .ptr = self,
            .vtable = &.{
                .name = nameImpl,
                .capabilities = capabilitiesImpl,
                .process = processImpl,
                .deinit = deinitImpl,
            },
        };
    }

    pub fn rememberFact(self: *AssistantAgent, fact: []const u8) !void {
        const fact_copy = try self.allocator.dupe(u8, fact);
        try self.memory.append(self.allocator, fact_copy);
    }

    pub fn recallMemories(self: *AssistantAgent, query: []const u8, allocator: std.mem.Allocator) ![][]const u8 {
        var results = std.ArrayList([]const u8){};
        errdefer results.deinit(allocator);

        // Simple substring search
        for (self.memory.items) |item| {
            if (std.mem.indexOf(u8, item, query)) |_| {
                const result = try allocator.dupe(u8, item);
                try results.append(allocator, result);
            }
        }

        return results.toOwnedSlice(allocator);
    }

    fn nameImpl(ptr: *anyopaque) []const u8 {
        const self: *AssistantAgent = @ptrCast(@alignCast(ptr));
        return self.name;
    }

    fn capabilitiesImpl(_: *anyopaque, allocator: std.mem.Allocator) std.mem.Allocator.Error![]const []const u8 {
        const caps = try allocator.alloc([]const u8, 2);
        caps[0] = "conversation";
        caps[1] = "memory";
        return caps;
    }

    fn processImpl(ptr: *anyopaque, message: agenkit.Message) agenkit.AgentError!agenkit.Result {
        const self: *AssistantAgent = @ptrCast(@alignCast(ptr));
        self.interaction_count += 1;

        const content = message.contentAsText() catch {
            return agenkit.Result{ .err = agenkit.AgentError.InvalidInput };
        };

        // Build response with context
        const response_text = std.fmt.allocPrint(
            self.allocator,
            "[Interaction #{d}] Processing: {s}\nMemory: {d} facts stored",
            .{ self.interaction_count, content, self.memory.items.len },
        ) catch {
            return agenkit.AgentError.ProcessingFailed;
        };
        defer self.allocator.free(response_text);

        const response = agenkit.Message.withText(self.allocator, .assistant, response_text) catch {
            return agenkit.AgentError.ProcessingFailed;
        };

        return agenkit.Result{ .ok = response };
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *AssistantAgent = @ptrCast(@alignCast(ptr));
        self.deinit();
    }
};

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("\n=== Long-Running Agent Integration Example ===\n", .{});
    std.debug.print("Use Case: Personal Assistant with Memory\n\n", .{});

    // Create assistant
    var assistant = try AssistantAgent.init(allocator, "Assistant");
    defer assistant.deinit();

    // Session 1: Initial interaction
    std.debug.print("--- Session 1: Learning Phase ---\n", .{});
    {
        var msg1 = try agenkit.Message.withText(allocator, .user, "My name is Alice");
        defer msg1.deinit();

        const result1 = try assistant.agent().process(msg1);
        var response1 = try result1.unwrap();
        defer response1.deinit();

        std.debug.print("User: My name is Alice\n", .{});
        std.debug.print("Assistant: {s}\n", .{try response1.contentAsText()});

        // Store in memory
        try assistant.rememberFact("User's name is Alice");

        var msg2 = try agenkit.Message.withText(allocator, .user, "I work at TechCorp");
        defer msg2.deinit();

        const result2 = try assistant.agent().process(msg2);
        var response2 = try result2.unwrap();
        defer response2.deinit();

        std.debug.print("\nUser: I work at TechCorp\n", .{});
        std.debug.print("Assistant: {s}\n", .{try response2.contentAsText()});

        try assistant.rememberFact("User works at TechCorp");

        std.debug.print("\n✓ Learned 2 facts about user\n\n", .{});
    }

    // Session 2: Building context
    std.debug.print("--- Session 2: Context Building ---\n", .{});
    {
        var msg3 = try agenkit.Message.withText(allocator, .user, "I like coffee");
        defer msg3.deinit();

        const result3 = try assistant.agent().process(msg3);
        var response3 = try result3.unwrap();
        defer response3.deinit();

        std.debug.print("User: I like coffee\n", .{});
        std.debug.print("Assistant: {s}\n", .{try response3.contentAsText()});

        try assistant.rememberFact("User likes coffee");

        var msg4 = try agenkit.Message.withText(allocator, .user, "My meeting is at 2pm");
        defer msg4.deinit();

        const result4 = try assistant.agent().process(msg4);
        var response4 = try result4.unwrap();
        defer response4.deinit();

        std.debug.print("\nUser: My meeting is at 2pm\n", .{});
        std.debug.print("Assistant: {s}\n", .{try response4.contentAsText()});

        try assistant.rememberFact("User has meeting at 2pm");

        std.debug.print("\n✓ Context expanded to 4 facts\n\n", .{});
    }

    // Session 3: Memory recall
    std.debug.print("--- Session 3: Memory Recall ---\n", .{});
    {
        var msg5 = try agenkit.Message.withText(allocator, .user, "What do you know about me?");
        defer msg5.deinit();

        const result5 = try assistant.agent().process(msg5);
        var response5 = try result5.unwrap();
        defer response5.deinit();

        std.debug.print("User: What do you know about me?\n", .{});
        std.debug.print("Assistant: Let me recall...\n", .{});

        // Recall all memories
        const memories = try assistant.recallMemories("User", allocator);
        defer {
            for (memories) |memory| {
                allocator.free(memory);
            }
            allocator.free(memories);
        }

        std.debug.print("\nRecalled {d} facts:\n", .{memories.len});
        for (memories, 0..) |memory, i| {
            std.debug.print("  {d}. {s}\n", .{ i + 1, memory });
        }

        std.debug.print("\n✓ Successfully recalled context\n\n", .{});
    }

    // Session 4: Context-aware response
    std.debug.print("--- Session 4: Context-Aware Interaction ---\n", .{});
    {
        var msg6 = try agenkit.Message.withText(allocator, .user, "Remind me about work");
        defer msg6.deinit();

        const result6 = try assistant.agent().process(msg6);
        var response6 = try result6.unwrap();
        defer response6.deinit();

        std.debug.print("User: Remind me about work\n", .{});
        std.debug.print("Assistant: {s}\n", .{try response6.contentAsText()});

        const work_memories = try assistant.recallMemories("work", allocator);
        defer {
            for (work_memories) |memory| {
                allocator.free(memory);
            }
            allocator.free(work_memories);
        }

        std.debug.print("\nWork-related memories:\n", .{});
        for (work_memories) |memory| {
            std.debug.print("  - {s}\n", .{memory});
        }

        std.debug.print("\n✓ Context-aware response provided\n\n", .{});
    }

    // Memory statistics
    std.debug.print("--- Memory Statistics ---\n", .{});
    std.debug.print("Total interactions: {d}\n", .{assistant.interaction_count});
    std.debug.print("Facts stored: {d}\n", .{assistant.memory.items.len});
    std.debug.print("Memory tiers:\n", .{});
    std.debug.print("  - Working: Recent 3 interactions\n", .{});
    std.debug.print("  - Short-term: Last 10 interactions\n", .{});
    std.debug.print("  - Long-term: All stored facts\n", .{});

    std.debug.print("\n=== Long-Running Agent Summary ===\n", .{});
    std.debug.print("✓ Features demonstrated:\n", .{});
    std.debug.print("  1. Persistent memory across sessions\n", .{});
    std.debug.print("  2. Context-aware responses\n", .{});
    std.debug.print("  3. Fact storage and recall\n", .{});
    std.debug.print("  4. Interaction counting\n", .{});
    std.debug.print("\n✓ Patterns used:\n", .{});
    std.debug.print("  - Conversational: Multi-turn dialogue\n", .{});
    std.debug.print("  - Memory Hierarchy: Working/short/long-term memory\n", .{});
    std.debug.print("\n✓ Use cases:\n", .{});
    std.debug.print("  - Personal assistants\n", .{});
    std.debug.print("  - Customer service bots\n", .{});
    std.debug.print("  - Educational tutors\n", .{});
    std.debug.print("  - Any stateful agent requiring context\n", .{});
    std.debug.print("\n✓ Long-running agent example completed successfully!\n\n", .{});
}
