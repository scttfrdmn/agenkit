/// OpenAI adapter example
///
/// This example demonstrates how to use the OpenAI LLM adapter with GPT models.
/// It shows basic completion requests with various options.
///
/// Setup:
///   1. Set OPENAI_API_KEY environment variable:
///      export OPENAI_API_KEY="sk-..."
///
///   2. Or create a .env file with:
///      OPENAI_API_KEY=sk-...
///
/// Usage:
///   zig build run-openai-basic

const std = @import("std");
const agenkit = @import("agenkit");
const OpenAILLM = agenkit.adapter.OpenAILLM;
const Message = agenkit.Message;
const Role = agenkit.Role;
const llm_mod = agenkit.adapter;

pub fn main() !void {
    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("\n=== OpenAI LLM Adapter Example ===\n\n", .{});

    // Initialize OpenAI adapter
    // API key is read from OPENAI_API_KEY environment variable
    var llm_impl = OpenAILLM.init(allocator, "", "gpt-4-turbo") catch |err| {
        std.debug.print("Error: Failed to initialize OpenAI adapter: {}\n", .{err});
        std.debug.print("Make sure OPENAI_API_KEY environment variable is set.\n", .{});
        return err;
    };
    defer llm_impl.deinit();

    const llm = llm_impl.asLLM();

    std.debug.print("Model: {s}\n\n", .{llm.model()});

    // Example 1: Simple completion
    std.debug.print("--- Example 1: Simple Completion ---\n", .{});
    try simpleCompletion(allocator, llm);

    // Example 2: Completion with options
    std.debug.print("\n--- Example 2: Completion with Options ---\n", .{});
    try completionWithOptions(allocator, llm);

    // Example 3: Multi-turn conversation
    std.debug.print("\n--- Example 3: Multi-turn Conversation ---\n", .{});
    try multiTurnConversation(allocator, llm);

    // Example 4: Code generation
    std.debug.print("\n--- Example 4: Code Generation ---\n", .{});
    try codeGeneration(allocator, llm);

    std.debug.print("\n=== All Examples Complete ===\n", .{});
}

/// Example 1: Simple completion with default options
fn simpleCompletion(allocator: std.mem.Allocator, llm: llm_mod.LLM) !void {
    var msg = try Message.withText(allocator, .user, "What is the capital of France?");
    defer msg.deinit();

    const messages = [_]*Message{&msg};

    var options = llm_mod.CallOptions.init(allocator);
    defer options.deinit();

    std.debug.print("Request: {s}\n", .{msg.content.text});

    const response = llm.complete(allocator, &messages, &options) catch |err| {
        std.debug.print("Error: {}\n", .{err});
        return err;
    };
    defer response.deinit();

    std.debug.print("Response: {s}\n", .{response.content.text});

    // Show metadata
    if (response.getMetadata("model")) |model| {
        std.debug.print("Model used: {s}\n", .{model.string});
    }

    if (response.getMetadata("usage")) |usage| {
        const usage_obj = usage.object;
        if (usage_obj.get("total_tokens")) |total| {
            std.debug.print("Total tokens: {d}\n", .{total.integer});
        }
    }
}

/// Example 2: Completion with temperature and max_tokens
fn completionWithOptions(allocator: std.mem.Allocator, llm: llm_mod.LLM) !void {
    var msg = try Message.withText(allocator, .user, "Write a haiku about programming.");
    defer msg.deinit();

    const messages = [_]*Message{&msg};

    var options = llm_mod.CallOptions.init(allocator);
    defer options.deinit();
    try options.withTemperature(0.9); // Higher temp for creative output
    try options.withMaxTokens(100);

    std.debug.print("Request: {s}\n", .{msg.content.text});
    std.debug.print("Options: temperature=0.9, max_tokens=100\n", .{});

    const response = llm.complete(allocator, &messages, &options) catch |err| {
        std.debug.print("Error: {}\n", .{err});
        return err;
    };
    defer response.deinit();

    std.debug.print("Response:\n{s}\n", .{response.content.text});
}

/// Example 3: Multi-turn conversation with context
fn multiTurnConversation(allocator: std.mem.Allocator, llm: llm_mod.LLM) !void {
    var system = try Message.withText(allocator, .system, "You are a helpful math tutor.");
    defer system.deinit();

    var user1 = try Message.withText(allocator, .user, "What is 15 * 7?");
    defer user1.deinit();

    var assistant1 = try Message.withText(allocator, .assistant, "15 * 7 = 105");
    defer assistant1.deinit();

    var user2 = try Message.withText(allocator, .user, "Now add 23 to that result.");
    defer user2.deinit();

    const messages = [_]*Message{ &system, &user1, &assistant1, &user2 };

    var options = llm_mod.CallOptions.init(allocator);
    defer options.deinit();
    try options.withTemperature(0.2); // Low temp for factual responses

    std.debug.print("Conversation:\n", .{});
    std.debug.print("System: {s}\n", .{system.content.text});
    std.debug.print("User: {s}\n", .{user1.content.text});
    std.debug.print("Assistant: {s}\n", .{assistant1.content.text});
    std.debug.print("User: {s}\n", .{user2.content.text});

    const response = llm.complete(allocator, &messages, &options) catch |err| {
        std.debug.print("Error: {}\n", .{err});
        return err;
    };
    defer response.deinit();

    std.debug.print("Assistant: {s}\n", .{response.content.text});
}

/// Example 4: Code generation with specific instructions
fn codeGeneration(allocator: std.mem.Allocator, llm: llm_mod.LLM) !void {
    var system = try Message.withText(
        allocator,
        .system,
        "You are an expert Zig programmer. Provide concise, well-commented code.",
    );
    defer system.deinit();

    var user = try Message.withText(
        allocator,
        .user,
        "Write a Zig function that checks if a number is prime.",
    );
    defer user.deinit();

    const messages = [_]*Message{ &system, &user };

    var options = llm_mod.CallOptions.init(allocator);
    defer options.deinit();
    try options.withTemperature(0.2); // Low temp for code
    try options.withMaxTokens(500);

    std.debug.print("Request: {s}\n", .{user.content.text});

    const response = llm.complete(allocator, &messages, &options) catch |err| {
        std.debug.print("Error: {}\n", .{err});
        return err;
    };
    defer response.deinit();

    std.debug.print("Response:\n{s}\n", .{response.content.text});

    // Show finish reason
    if (response.getMetadata("finish_reason")) |finish_reason| {
        std.debug.print("\nFinish reason: {s}\n", .{finish_reason.string});
    }
}
