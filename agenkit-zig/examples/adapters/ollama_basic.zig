/// Ollama adapter example
///
/// This example demonstrates how to use the Ollama LLM adapter with local models.
/// Ollama allows running LLMs locally without API keys.
///
/// Setup:
///   1. Install Ollama: https://ollama.ai/download
///   2. Pull a model: ollama pull llama2
///   3. Start Ollama (usually runs automatically)
///
/// Usage:
///   zig build run-ollama-basic

const std = @import("std");
const agenkit = @import("agenkit");
const OllamaLLM = agenkit.adapter.OllamaLLM;
const Message = agenkit.Message;
const Role = agenkit.Role;
const llm_mod = agenkit.adapter;

pub fn main() !void {
    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("\n=== Ollama LLM Adapter Example ===\n\n", .{});

    // Initialize Ollama adapter (defaults to localhost:11434)
    var llm_impl = OllamaLLM.init(allocator, "llama2", "http://localhost:11434") catch |err| {
        std.debug.print("Error: Failed to initialize Ollama adapter: {}\n", .{err});
        std.debug.print("Make sure Ollama is installed and running.\n", .{});
        std.debug.print("Visit: https://ollama.ai/download\n", .{});
        return err;
    };
    defer llm_impl.deinit();

    const llm = llm_impl.asLLM();

    std.debug.print("Model: {s}\n", .{llm.model()});
    std.debug.print("Server: http://localhost:11434\n\n", .{});

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
    var msg = try Message.withText(allocator, .user, "What is Zig programming language?");
    defer msg.deinit();

    const messages = [_]*Message{&msg};

    var options = llm_mod.CallOptions.init(allocator);
    defer options.deinit();

    std.debug.print("Request: {s}\n", .{msg.content.text});

    const response = llm.complete(allocator, &messages, &options) catch |err| {
        std.debug.print("Error: {}\n", .{err});
        std.debug.print("Make sure Ollama is running and llama2 is pulled.\n", .{});
        return err;
    };
    defer response.deinit();

    std.debug.print("Response: {s}\n", .{response.content.text});

    // Show metadata
    if (response.getMetadata("model")) |model| {
        std.debug.print("Model: {s}\n", .{model.string});
    }

    if (response.getMetadata("total_duration")) |duration| {
        const ms = @as(f64, @floatFromInt(duration.integer)) / 1_000_000.0;
        std.debug.print("Duration: {d:.2}ms\n", .{ms});
    }
}

/// Example 2: Creative writing with higher temperature
fn creativeWriting(allocator: std.mem.Allocator, llm: llm_mod.LLM) !void {
    var system = try Message.withText(
        allocator,
        .system,
        "You are a creative writer specializing in short fiction.",
    );
    defer system.deinit();

    var user = try Message.withText(
        allocator,
        .user,
        "Write a two-sentence story about a programmer discovering a bug.",
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
        "You are a Zig programming expert. Provide concise, correct code.",
    );
    defer system.deinit();

    var user = try Message.withText(
        allocator,
        .user,
        "Write a Zig function to calculate factorial recursively.",
    );
    defer user.deinit();

    const messages = [_]*Message{ &system, &user };

    var options = llm_mod.CallOptions.init(allocator);
    defer options.deinit();
    options.withTemperature(0.2); // Low temp for accuracy

    std.debug.print("Request: {s}\n", .{user.content.text});
    std.debug.print("Temperature: 0.2 (precise)\n", .{});

    const response = llm.complete(allocator, &messages, &options) catch |err| {
        std.debug.print("Error: {}\n", .{err});
        return err;
    };
    defer response.deinit();

    std.debug.print("\nCode:\n{s}\n", .{response.content.text});
}
