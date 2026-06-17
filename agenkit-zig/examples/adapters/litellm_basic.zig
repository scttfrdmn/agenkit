/// LiteLLM adapter example (Universal LLM proxy)
///
/// This example demonstrates how to use the LiteLLM adapter to access 100+ LLM
/// providers through a unified OpenAI-compatible interface.
///
/// Setup:
///   1. Install LiteLLM: pip install litellm
///   2. Start proxy: litellm --port 4000
///   3. Or use Docker: docker run -p 4000:4000 ghcr.io/berriai/litellm:latest
///   4. Optional: Set LITELLM_API_KEY for authenticated deployments
///
/// Usage:
///   zig build run-litellm-basic

const std = @import("std");
const agenkit = @import("agenkit");
const LiteLLMLLM = agenkit.adapter.LiteLLMLLM;
const Message = agenkit.Message;
const Role = agenkit.Role;
const llm_mod = agenkit.adapter;

pub fn main() !void {
    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("\n=== LiteLLM Adapter Example (Universal Proxy) ===\n\n", .{});

    // Initialize LiteLLM adapter
    // Works with any model supported by LiteLLM:
    // - OpenAI: gpt-4, gpt-3.5-turbo
    // - Anthropic: claude-3-opus-20240229, claude-3-sonnet-20240229
    // - Cohere: command-r-plus
    // - Azure: azure/gpt-4
    // - And 100+ more!
    var llm_impl = LiteLLMLLM.init(
        allocator,
        "", // Empty for local proxy, or set LITELLM_API_KEY
        "gpt-3.5-turbo", // Any LiteLLM-supported model
        "http://localhost:4000",
    ) catch |err| {
        std.debug.print("Error: Failed to initialize LiteLLM adapter: {}\n", .{err});
        std.debug.print("Make sure LiteLLM proxy is running on port 4000.\n", .{});
        std.debug.print("Start with: litellm --port 4000\n", .{});
        std.debug.print("Or: docker run -p 4000:4000 ghcr.io/berriai/litellm:latest\n", .{});
        return err;
    };
    defer llm_impl.deinit();

    const llm = llm_impl.asLLM();

    std.debug.print("Model: {s}\n", .{llm.model()});
    std.debug.print("Provider: LiteLLM (Universal Proxy)\n", .{});
    std.debug.print("Proxy URL: http://localhost:4000\n\n", .{});

    // Example 1: Simple completion
    std.debug.print("--- Example 1: Simple Completion ---\n", .{});
    try simpleCompletion(allocator, llm);

    // Example 2: Model routing
    std.debug.print("\n--- Example 2: Model Routing ---\n", .{});
    try modelRouting(allocator);

    // Example 3: Error handling
    std.debug.print("\n--- Example 3: Cost-Aware Routing ---\n", .{});
    try costAwareRouting(allocator);

    std.debug.print("\n=== All Examples Complete ===\n", .{});
}

/// Example 1: Simple completion with default options
fn simpleCompletion(allocator: std.mem.Allocator, llm: llm_mod.LLM) !void {
    var msg = try Message.withText(allocator, .user, "What are the benefits of using a unified LLM proxy?");
    defer msg.deinit();

    const messages = [_]*Message{&msg};

    var options = llm_mod.CallOptions.init(allocator);
    defer options.deinit();

    std.debug.print("Request: {s}\n", .{msg.content.text});

    const response = llm.complete(allocator, &messages, &options) catch |err| {
        std.debug.print("Error: {}\n", .{err});
        std.debug.print("Check that LiteLLM proxy is running.\n", .{});
        return err;
    };
    defer response.deinit();

    std.debug.print("Response: {s}\n", .{response.content.text});

    // Show metadata
    if (response.getMetadata("model")) |model_val| {
        std.debug.print("Model Used: {}\n", .{model_val});
    }

    if (response.getMetadata("usage")) |usage| {
        std.debug.print("Token Usage: {}\n", .{usage});
    }
}

/// Example 2: Routing between different models
fn modelRouting(allocator: std.mem.Allocator) !void {
    std.debug.print("Demonstrates routing to different LLM providers...\n\n", .{});

    // Example: Try GPT-3.5 for fast responses
    std.debug.print("Using GPT-3.5-turbo (fast, cost-effective):\n", .{});

    var fast_llm_impl = LiteLLMLLM.init(
        allocator,
        "",
        "gpt-3.5-turbo",
        "http://localhost:4000",
    ) catch |err| {
        std.debug.print("Error: {}\n", .{err});
        return err;
    };
    defer fast_llm_impl.deinit();

    const fast_llm = fast_llm_impl.asLLM();

    var msg = try Message.withText(allocator, .user, "What is 2+2?");
    defer msg.deinit();

    const messages = [_]*Message{&msg};

    var options = llm_mod.CallOptions.init(allocator);
    defer options.deinit();
    options.withMaxTokens(50);

    const response = fast_llm.complete(allocator, &messages, &options) catch |err| {
        std.debug.print("Error: {}\n", .{err});
        return err;
    };
    defer response.deinit();

    std.debug.print("Response: {s}\n", .{response.content.text});

    // In production, you could route to different models based on:
    // - Task complexity (simple → gpt-3.5, complex → gpt-4)
    // - Cost constraints (cheap → mixtral, premium → claude-opus)
    // - Latency requirements (fast → local models, accuracy → cloud)
    // - Privacy needs (sensitive → local, general → cloud)
}

/// Example 3: Cost-aware routing strategy
fn costAwareRouting(allocator: std.mem.Allocator) !void {
    std.debug.print("Demonstrates cost-aware model selection...\n\n", .{});

    // Simulate routing based on query complexity
    const simple_query = "What is the capital of France?";
    const complex_query = "Explain quantum entanglement and its implications for computing.";

    std.debug.print("Simple Query (use cheap model): {s}\n", .{simple_query});

    // For simple queries, use cost-effective models
    var cheap_llm_impl = LiteLLMLLM.init(
        allocator,
        "",
        "gpt-3.5-turbo", // $0.0005/1K tokens
        "http://localhost:4000",
    ) catch |err| {
        std.debug.print("Error: {}\n", .{err});
        return err;
    };
    defer cheap_llm_impl.deinit();

    const cheap_llm = cheap_llm_impl.asLLM();

    var msg1 = try Message.withText(allocator, .user, simple_query);
    defer msg1.deinit();

    const messages1 = [_]*Message{&msg1};

    var options1 = llm_mod.CallOptions.init(allocator);
    defer options1.deinit();
    options1.withMaxTokens(100);

    const response1 = cheap_llm.complete(allocator, &messages1, &options1) catch |err| {
        std.debug.print("Error: {}\n", .{err});
        return err;
    };
    defer response1.deinit();

    std.debug.print("Response (gpt-3.5-turbo): {s}\n\n", .{response1.content.text});

    std.debug.print("Complex Query (would use premium model): {s}\n", .{complex_query});
    std.debug.print("(In production, this would route to gpt-4 or claude-opus)\n", .{});

    // Cost optimization strategies with LiteLLM:
    // 1. Query classification (simple → cheap, complex → expensive)
    // 2. Fallback chains (try cheap first, escalate if needed)
    // 3. Budget enforcement (track costs, switch models)
    // 4. A/B testing (compare quality vs cost)
}
