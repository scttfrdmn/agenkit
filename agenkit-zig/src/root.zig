/// Agenkit - The foundation layer for AI agents in Zig
///
/// This is the root module for the Agenkit Zig implementation.
/// It provides core types and interfaces for building AI agents.
///
/// ## Design Philosophy
///
/// The Zig implementation follows these principles:
/// - **Explicit is better than implicit**: No hidden memory allocations or control flow
/// - **Error handling first**: All fallible operations return error unions
/// - **Zero overhead abstractions**: Interface-based design with compile-time dispatch where possible
/// - **Memory safety**: Explicit allocator management prevents memory leaks
///
/// ## Getting Started
///
/// ```zig
/// const agenkit = @import("agenkit");
/// const std = @import("std");
///
/// pub fn main() !void {
///     var gpa = std.heap.GeneralPurposeAllocator(.{}){};
///     defer _ = gpa.deinit();
///     const allocator = gpa.allocator();
///
///     // Create a message
///     var msg = try agenkit.Message.withText(allocator, .user, "Hello, agent!");
///     defer msg.deinit();
///
///     // Create an agent
///     var echo = try agenkit.EchoAgent.init(allocator);
///     defer echo.agent().deinit();
///
///     // Process the message
///     const result = try echo.agent().process(msg);
///     var response = try result.unwrap();
///     defer response.deinit();
///
///     // Get the response text
///     const text = try response.contentAsText();
///     std.debug.print("Response: {s}\n", .{text});
/// }
/// ```
///
/// ## Cross-Language Compatibility
///
/// This Zig implementation maintains API compatibility with:
/// - Python (agenkit)
/// - Go (agenkit-go)
/// - TypeScript (@agenkit/core)
/// - C++ (agenkit-cpp)
/// - Rust (agenkit-rs)
///
/// All implementations share the same core concepts:
/// - Messages with role, content, and metadata
/// - Agents with process() interface
/// - Result types for error handling
/// - Composable patterns
const std = @import("std");

// Core types
pub const Message = @import("message.zig").Message;
pub const Role = @import("message.zig").Role;
pub const Content = @import("message.zig").Content;

// Agent interface and implementations
pub const Agent = @import("agent.zig").Agent;
pub const AgentError = @import("agent.zig").AgentError;
pub const Result = @import("agent.zig").Result;
pub const EchoAgent = @import("agent.zig").EchoAgent;

// Patterns
pub const patterns = struct {
    // Sequential pattern
    pub const SequentialPattern = @import("patterns/sequential.zig").SequentialPattern;

    // Parallel pattern
    pub const ParallelPattern = @import("patterns/parallel.zig").ParallelPattern;
    pub const defaultAggregator = @import("patterns/parallel.zig").defaultAggregator;
    pub const Aggregator = @import("patterns/parallel.zig").Aggregator;

    // Reflection pattern
    pub const ReflectionAgent = @import("patterns/reflection.zig").ReflectionAgent;
    pub const ReflectionStep = @import("patterns/reflection.zig").ReflectionStep;
    pub const StopReason = @import("patterns/reflection.zig").StopReason;
    pub const CritiqueFormat = @import("patterns/reflection.zig").CritiqueFormat;

    // Agents-as-Tools pattern
    pub const AgentTool = @import("patterns/agents_as_tools.zig").AgentTool;
    pub const SupervisorAgent = @import("patterns/agents_as_tools.zig").SupervisorAgent;
    pub const agentAsTool = @import("patterns/agents_as_tools.zig").agentAsTool;
    pub const OutputFormat = @import("patterns/agents_as_tools.zig").OutputFormat;
};

// Version information
pub const version = "0.39.0";
pub const zig_version = @import("builtin").zig_version;

test {
    std.testing.refAllDecls(@This());
    // Also test patterns
    _ = @import("patterns/sequential.zig");
    _ = @import("patterns/parallel.zig");
    _ = @import("patterns/reflection.zig");
    _ = @import("patterns/agents_as_tools.zig");
}
