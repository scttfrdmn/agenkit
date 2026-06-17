/// Conversational Agent with Memory Example
///
/// This example demonstrates:
/// - Integrating memory with a conversational agent
/// - Maintaining context across multiple interactions
/// - Using memory to inform responses
/// - Practical memory management in conversations
///
/// Run with: zig build run-conversational-memory

const std = @import("std");
const agenkit = @import("agenkit");

const Message = agenkit.Message;
const MemoryEntry = agenkit.infrastructure.memory.MemoryEntry;
const HierarchyMemory = agenkit.infrastructure.memory.HierarchyMemory;
const Role = agenkit.infrastructure.memory.Role;

/// A simple conversational agent that uses memory to maintain context
const MemoryAwareAgent = struct {
    allocator: std.mem.Allocator,
    memory: *HierarchyMemory,
    session_id: []const u8,

    pub fn init(
        allocator: std.mem.Allocator,
        memory: *HierarchyMemory,
        session_id: []const u8,
    ) MemoryAwareAgent {
        return .{
            .allocator = allocator,
            .memory = memory,
            .session_id = session_id,
        };
    }

    /// Process a user message with context from memory
    pub fn chat(self: *MemoryAwareAgent, user_input: []const u8) ![]const u8 {
        // Store user message in memory
        var user_entry = try MemoryEntry.init(
            self.allocator,
            self.session_id,
            .user,
            user_input,
        );
        user_entry.setImportance(0.7); // User messages are important
        try self.memory.store(&user_entry);
        user_entry.deinit();

        // Retrieve recent context (last 5 messages)
        const context = try self.memory.retrieve(self.session_id, 5);
        defer {
            for (context) |e| {
                e.deinit();
                self.allocator.destroy(e);
            }
            self.allocator.free(context);
        }

        // Generate response based on context
        const response = try self.generateResponse(user_input, context);

        // Store assistant response in memory
        var assistant_entry = try MemoryEntry.init(
            self.allocator,
            self.session_id,
            .assistant,
            response,
        );
        assistant_entry.setImportance(0.6); // Assistant responses moderately important
        try self.memory.store(&assistant_entry);
        assistant_entry.deinit();

        return response;
    }

    /// Generate response using simple pattern matching and context awareness
    fn generateResponse(
        self: *MemoryAwareAgent,
        input: []const u8,
        context: []const *MemoryEntry,
    ) ![]const u8 {
        // Check if this is a follow-up question
        const is_followup = std.mem.indexOf(u8, input, "what about") != null or
            std.mem.indexOf(u8, input, "and") != null or
            std.mem.indexOf(u8, input, "also") != null or
            std.mem.indexOf(u8, input, "too") != null;

        // Build context summary
        var has_topic = false;
        var previous_topic: []const u8 = "";

        for (context) |entry| {
            if (entry.role == .user) {
                if (std.mem.indexOf(u8, entry.content, "Zig") != null or
                    std.mem.indexOf(u8, entry.content, "programming") != null)
                {
                    has_topic = true;
                    previous_topic = "Zig programming";
                } else if (std.mem.indexOf(u8, entry.content, "memory") != null) {
                    has_topic = true;
                    previous_topic = "memory management";
                }
            }
        }

        // Generate context-aware response
        if (is_followup and has_topic) {
            return std.fmt.allocPrint(
                self.allocator,
                "Regarding {s} (which we discussed earlier), {s}",
                .{ previous_topic, input },
            );
        }

        // Topic-based responses
        if (std.mem.indexOf(u8, input, "Zig") != null) {
            return self.allocator.dupe(u8, "Zig is a general-purpose programming language focused on robustness, optimality, and clarity.");
        } else if (std.mem.indexOf(u8, input, "memory") != null) {
            return self.allocator.dupe(u8, "Memory management in Zig is explicit and uses allocators to prevent leaks and enable custom allocation strategies.");
        } else if (std.mem.indexOf(u8, input, "hello") != null or std.mem.indexOf(u8, input, "hi") != null) {
            if (context.len > 2) {
                return self.allocator.dupe(u8, "Hello again! How can I help you today?");
            } else {
                return self.allocator.dupe(u8, "Hello! I'm a memory-aware conversational agent. How can I assist you?");
            }
        } else {
            return std.fmt.allocPrint(
                self.allocator,
                "I understand you're asking about: {s}. Let me help with that!",
                .{input},
            );
        }
    }

    /// Get conversation summary
    pub fn getSummary(self: *MemoryAwareAgent) ![]const u8 {
        return self.memory.summarize(self.session_id, 20);
    }
};

pub fn main() !void {
    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("\n=== Conversational Agent with Memory ===\n\n", .{});

    // Initialize memory system
    var memory = HierarchyMemory.init(allocator, .{
        .working_capacity = 10,
        .short_term_capacity = 50,
        .long_term_summary_threshold = 100,
        .importance_threshold = 0.3,
    });
    defer memory.deinit();

    const session_id = "demo-conversation";

    // Create memory-aware agent
    var agent = MemoryAwareAgent.init(allocator, &memory, session_id);

    // Simulate a conversation
    const conversation = [_][]const u8{
        "Hello!",
        "What is Zig?",
        "Tell me about memory management",
        "What about error handling?",
        "Can you remind me what we talked about regarding memory?",
        "Thanks for the help!",
    };

    std.debug.print("Starting conversation...\n\n", .{});

    for (conversation, 1..) |user_input, turn| {
        std.debug.print("Turn {d}\n", .{turn});
        std.debug.print("──────────────────────────────\n", .{});
        std.debug.print("User: {s}\n", .{user_input});

        const response = try agent.chat(user_input);
        defer allocator.free(response);

        std.debug.print("Agent: {s}\n\n", .{response});

        // Show memory status every few turns
        if (turn % 3 == 0) {
            std.debug.print("📝 Memory Status:\n", .{});
            const entries = try memory.retrieve(session_id, 0);
            defer {
                for (entries) |e| {
                    e.deinit();
                    allocator.destroy(e);
                }
                allocator.free(entries);
            }
            std.debug.print("  Total entries in memory: {d}\n\n", .{entries.len});
        }
    }

    // Display full conversation summary
    std.debug.print("═══════════════════════════════\n", .{});
    std.debug.print("📊 Conversation Summary\n", .{});
    std.debug.print("═══════════════════════════════\n\n", .{});

    const summary = try agent.getSummary();
    defer allocator.free(summary);
    std.debug.print("{s}\n", .{summary});

    // Demonstrate context persistence
    std.debug.print("\n═══════════════════════════════\n", .{});
    std.debug.print("🔍 Context Retrieval Test\n", .{});
    std.debug.print("═══════════════════════════════\n\n", .{});

    std.debug.print("Asking a question that requires earlier context...\n\n", .{});

    const followup = "What did you say about Zig earlier?";
    std.debug.print("User: {s}\n", .{followup});

    const context = try memory.retrieve(session_id, 0);
    defer {
        for (context) |e| {
            e.deinit();
            allocator.destroy(e);
        }
        allocator.free(context);
    }

    var found_zig_mention = false;
    std.debug.print("\nSearching through {d} stored entries...\n", .{context.len});
    for (context) |entry| {
        if (entry.role == .assistant and std.mem.indexOf(u8, entry.content, "Zig") != null) {
            std.debug.print("✓ Found: {s}\n", .{entry.content});
            found_zig_mention = true;
            break;
        }
    }

    if (!found_zig_mention) {
        std.debug.print("✗ No mention of Zig found in memory\n", .{});
    }

    // Show memory benefits
    std.debug.print("\n═══════════════════════════════\n", .{});
    std.debug.print("💡 Benefits of Memory\n", .{});
    std.debug.print("═══════════════════════════════\n\n", .{});

    std.debug.print("1. Context Preservation: Agent remembers earlier topics\n", .{});
    std.debug.print("2. Natural Follow-ups: Can reference previous discussion\n", .{});
    std.debug.print("3. Personalization: Adapts based on conversation history\n", .{});
    std.debug.print("4. Efficient Storage: Hierarchical memory manages capacity\n", .{});
    std.debug.print("5. Importance Weighting: Key information retained longer\n", .{});

    std.debug.print("\n=== Example Complete ===\n", .{});
}
