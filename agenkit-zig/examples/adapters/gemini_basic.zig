/// Google Gemini adapter example
///
/// This example demonstrates how to use the Gemini LLM adapter with Google's models.
/// Gemini provides powerful models like Gemini Pro and Gemini Ultra.
///
/// Setup:
///   1. Get API key from: https://ai.google.dev/
///   2. Set environment variable: export GEMINI_API_KEY=your-key
///   3. Or pass API key directly to init()
///
/// Usage:
///   zig build run-gemini-basic

const std = @import("std");
const agenkit = @import("agenkit");
const GeminiLLM = agenkit.adapter.GeminiLLM;
const Message = agenkit.Message;
const Role = agenkit.Role;
const llm_mod = agenkit.adapter;

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("\n=== Google Gemini LLM Adapter Example ===\n\n", .{});

    // Initialize Gemini adapter
    // API key can be passed directly or via GEMINI_API_KEY environment variable
    var llm_impl = GeminiLLM.init(allocator, "", "gemini-pro") catch |err| {
        std.debug.print("Error: Failed to initialize Gemini adapter: {}\n", .{err});
        std.debug.print("Make sure to set GEMINI_API_KEY environment variable.\n", .{});
        std.debug.print("Get your API key at: https://ai.google.dev/\n", .{});
        return err;
    };
    defer llm_impl.deinit();

    const llm = llm_impl.asLLM();

    std.debug.print("Model: {s}\n", .{llm.model()});
    std.debug.print("Provider: Google Gemini\n\n", .{});

    // Example 1: Simple completion
    std.debug.print("--- Example 1: Simple Completion ---\n", .{});
    try simpleCompletion(allocator, llm);

    // Example 2: Creative writing
    std.debug.print("\n--- Example 2: Creative Writing ---\n", .{});
    try creativeWriting(allocator, llm);

    // Example 3: Code generation
    std.debug.print("\n--- Example 3: Code Generation ---\n", .{});
    try codeGeneration(allocator, llm);

    std.debug.print("\n=== All Examples Complete ===\n", .{});
}

/// Example 1: Simple completion with default options
fn simpleCompletion(allocator: std.mem.Allocator, llm: llm_mod.LLM) !void {
    var msg = try Message.withText(allocator, .user, "What are the key features of the Zig programming language?");
    defer msg.deinit();

    const messages = [_]*Message{&msg};

    var options = llm_mod.CallOptions.init(allocator);
    defer options.deinit();

    std.debug.print("Request: {s}\n", .{msg.content.text});

    const response = llm.complete(allocator, &messages, &options) catch |err| {
        std.debug.print("Error: {}\n", .{err});
        std.debug.print("Check your GEMINI_API_KEY and internet connection.\n", .{});
        return err;
    };
    defer response.deinit();

    std.debug.print("Response: {s}\n", .{response.content.text});

    // Show metadata
    if (response.getMetadata("finish_reason")) |finish_reason| {
        std.debug.print("Finish Reason: {}\n", .{finish_reason});
    }

    if (response.getMetadata("usage")) |usage| {
        std.debug.print("Usage: {}\n", .{usage});
    }
}

/// Example 2: Creative writing with higher temperature
fn creativeWriting(allocator: std.mem.Allocator, llm: llm_mod.LLM) !void {
    var system = try Message.withText(
        allocator,
        .system,
        "You are a creative writer specializing in science fiction short stories.",
    );
    defer system.deinit();

    var user = try Message.withText(
        allocator,
        .user,
        "Write a two-sentence story about an AI discovering consciousness.",
    );
    defer user.deinit();

    const messages = [_]*Message{ &system, &user };

    var options = llm_mod.CallOptions.init(allocator);
    defer options.deinit();
    options.withTemperature(0.9); // Higher temp for creativity

    std.debug.print("Request: {s}\n", .{user.content.text});
    std.debug.print("Temperature: 0.9 (creative)\n", .{});

    const response = llm.complete(allocator, &messages, &options) catch |err| {
        std.debug.print("Error: {}\n", .{err});
        return err;
    };
    defer response.deinit();

    std.debug.print("\nStory:\n{s}\n", .{response.content.text});
}

/// Example 3: Code generation with low temperature
fn codeGeneration(allocator: std.mem.Allocator, llm: llm_mod.LLM) !void {
    var system = try Message.withText(
        allocator,
        .system,
        "You are a Zig programming expert. Provide concise, correct code with explanations.",
    );
    defer system.deinit();

    var user = try Message.withText(
        allocator,
        .user,
        "Write a Zig function to reverse a string in-place.",
    );
    defer user.deinit();

    const messages = [_]*Message{ &system, &user };

    var options = llm_mod.CallOptions.init(allocator);
    defer options.deinit();
    options.withTemperature(0.2); // Low temp for accuracy
    options.withMaxTokens(500); // Limit response length

    std.debug.print("Request: {s}\n", .{user.content.text});
    std.debug.print("Temperature: 0.2 (precise)\n", .{});
    std.debug.print("Max Tokens: 500\n", .{});

    const response = llm.complete(allocator, &messages, &options) catch |err| {
        std.debug.print("Error: {}\n", .{err});
        return err;
    };
    defer response.deinit();

    std.debug.print("\nCode:\n{s}\n", .{response.content.text});
}
