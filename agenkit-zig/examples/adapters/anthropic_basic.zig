/// Anthropic adapter example (Claude models)
///
/// This example demonstrates how to use the Anthropic LLM adapter with Claude models
/// (Opus, Sonnet, Haiku).
///
/// Setup:
///   1. Get API key from: https://console.anthropic.com/
///   2. Set environment variable: export ANTHROPIC_API_KEY=your-key
///   3. Or pass API key directly to init()
///
/// Usage:
///   zig build run-anthropic-basic

const std = @import("std");
const agenkit = @import("agenkit");
const AnthropicLLM = agenkit.adapter.AnthropicLLM;
const Message = agenkit.Message;
const Role = agenkit.Role;
const llm_mod = agenkit.adapter;

pub fn main() !void {
    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("\n=== Anthropic LLM Adapter Example (Claude) ===\n\n", .{});

    // Initialize Anthropic adapter
    // API key can be passed directly or via ANTHROPIC_API_KEY environment variable
    // Available models: claude-3-opus-20240229, claude-3-sonnet-20240229, claude-3-haiku-20240307
    var llm_impl = AnthropicLLM.init(allocator, "", "claude-3-sonnet-20240229") catch |err| {
        std.debug.print("Error: Failed to initialize Anthropic adapter: {}\n", .{err});
        std.debug.print("Make sure to set ANTHROPIC_API_KEY environment variable.\n", .{});
        std.debug.print("Get your API key at: https://console.anthropic.com/\n", .{});
        return err;
    };
    defer llm_impl.deinit();

    const llm = llm_impl.asLLM();

    std.debug.print("Model: {s}\n", .{llm.model()});
    std.debug.print("Provider: Anthropic (Claude)\n\n", .{});

    // Example 1: Simple completion
    std.debug.print("--- Example 1: Simple Completion ---\n", .{});
    try simpleCompletion(allocator, llm);

    // Example 2: System message usage
    std.debug.print("\n--- Example 2: System Message Usage ---\n", .{});
    try systemMessageExample(allocator, llm);

    // Example 3: Creative writing
    std.debug.print("\n--- Example 3: Creative Writing ---\n", .{});
    try creativeWriting(allocator, llm);

    std.debug.print("\n=== All Examples Complete ===\n", .{});
}

/// Example 1: Simple completion with default options
fn simpleCompletion(allocator: std.mem.Allocator, llm: llm_mod.LLM) !void {
    var msg = try Message.withText(allocator, .user, "Explain what makes Claude different from other AI assistants in 2-3 sentences.");
    defer msg.deinit();

    const messages = [_]*Message{&msg};

    var options = llm_mod.CallOptions.init(allocator);
    defer options.deinit();
    options.withMaxTokens(300); // max_tokens is required for Anthropic

    std.debug.print("Request: {s}\n", .{msg.content.text});

    const response = llm.complete(allocator, &messages, &options) catch |err| {
        std.debug.print("Error: {}\n", .{err});
        std.debug.print("Check your ANTHROPIC_API_KEY and internet connection.\n", .{});
        return err;
    };
    defer response.deinit();

    std.debug.print("Response: {s}\n", .{response.content.text});

    // Show metadata
    if (response.getMetadata("stop_reason")) |stop_reason| {
        std.debug.print("Stop Reason: {}\n", .{stop_reason});
    }

    if (response.getMetadata("usage")) |usage| {
        std.debug.print("Usage: {}\n", .{usage});
    }
}

/// Example 2: Using system messages (Anthropic's special handling)
fn systemMessageExample(allocator: std.mem.Allocator, llm: llm_mod.LLM) !void {
    // Anthropic handles system messages separately from the messages array
    var system = try Message.withText(
        allocator,
        .system,
        "You are a technical documentation expert. Provide clear, concise explanations.",
    );
    defer system.deinit();

    var user = try Message.withText(
        allocator,
        .user,
        "What is memory safety in programming languages?",
    );
    defer user.deinit();

    const messages = [_]*Message{ &system, &user };

    var options = llm_mod.CallOptions.init(allocator);
    defer options.deinit();
    options.withMaxTokens(500);
    options.withTemperature(0.3); // Lower temp for technical accuracy

    std.debug.print("System: {s}\n", .{system.content.text});
    std.debug.print("Request: {s}\n", .{user.content.text});
    std.debug.print("Temperature: 0.3 (precise)\n", .{});

    const response = llm.complete(allocator, &messages, &options) catch |err| {
        std.debug.print("Error: {}\n", .{err});
        return err;
    };
    defer response.deinit();

    std.debug.print("\nResponse:\n{s}\n", .{response.content.text});
}

/// Example 3: Creative writing with higher temperature
fn creativeWriting(allocator: std.mem.Allocator, llm: llm_mod.LLM) !void {
    var system = try Message.withText(
        allocator,
        .system,
        "You are a creative writer who specializes in thought-provoking short fiction.",
    );
    defer system.deinit();

    var user = try Message.withText(
        allocator,
        .user,
        "Write a three-sentence story about a robot learning to appreciate art.",
    );
    defer user.deinit();

    const messages = [_]*Message{ &system, &user };

    var options = llm_mod.CallOptions.init(allocator);
    defer options.deinit();
    options.withMaxTokens(500);
    options.withTemperature(0.9); // Higher temp for creativity
    options.withTopP(0.95);

    std.debug.print("Request: {s}\n", .{user.content.text});
    std.debug.print("Temperature: 0.9 (creative)\n", .{});
    std.debug.print("Top-P: 0.95\n", .{});

    const response = llm.complete(allocator, &messages, &options) catch |err| {
        std.debug.print("Error: {}\n", .{err});
        return err;
    };
    defer response.deinit();

    std.debug.print("\nStory:\n{s}\n", .{response.content.text});

    // Show token usage
    if (response.getMetadata("usage")) |usage| {
        std.debug.print("\nToken Usage: {}\n", .{usage});
    }
}
