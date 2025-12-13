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

    // ReAct pattern
    pub const ReActAgent = @import("patterns/react.zig").ReActAgent;
    pub const ReActStep = @import("patterns/react.zig").ReActStep;
    pub const Tool = @import("patterns/react.zig").Tool;
    pub const ToolRegistry = @import("patterns/react.zig").ToolRegistry;
    pub const ToolResult = @import("patterns/react.zig").ToolResult;

    // Planning pattern
    pub const PlanningAgent = @import("patterns/planning.zig").PlanningAgent;
    pub const Plan = @import("patterns/planning.zig").Plan;
    pub const PlanStep = @import("patterns/planning.zig").PlanStep;
    pub const StepStatus = @import("patterns/planning.zig").StepStatus;
    pub const StepExecutorFn = @import("patterns/planning.zig").StepExecutorFn;
    pub const defaultStepExecutor = @import("patterns/planning.zig").defaultStepExecutor;

    // Conversational pattern
    pub const ConversationalAgent = @import("patterns/conversational.zig").ConversationalAgent;

    // Task pattern
    pub const Task = @import("patterns/task.zig").Task;
    pub const TaskConfig = @import("patterns/task.zig").TaskConfig;
    pub const TaskState = @import("patterns/task.zig").TaskState;

    // Multiagent pattern
    pub const MultiAgentOrchestrator = @import("patterns/multiagent.zig").MultiAgentOrchestrator;
    pub const AgentTask = @import("patterns/multiagent.zig").AgentTask;
    pub const OrchestrationStrategy = @import("patterns/multiagent.zig").OrchestrationStrategy;
    pub const TaskStatus = @import("patterns/multiagent.zig").TaskStatus;

    // Autonomous pattern
    pub const AutonomousAgent = @import("patterns/autonomous.zig").AutonomousAgent;
    pub const Goal = @import("patterns/autonomous.zig").Goal;
    pub const GoalStatus = @import("patterns/autonomous.zig").GoalStatus;
    pub const AutonomousResult = @import("patterns/autonomous.zig").AutonomousResult;
    pub const GoalWorkerFn = @import("patterns/autonomous.zig").GoalWorkerFn;
    pub const defaultWorker = @import("patterns/autonomous.zig").defaultWorker;

    // Memory Hierarchy pattern
    pub const MemoryEntry = @import("patterns/memory_hierarchy.zig").MemoryEntry;
    pub const WorkingMemory = @import("patterns/memory_hierarchy.zig").WorkingMemory;
    pub const ShortTermMemory = @import("patterns/memory_hierarchy.zig").ShortTermMemory;
    pub const LongTermMemory = @import("patterns/memory_hierarchy.zig").LongTermMemory;
    pub const MemoryHierarchy = @import("patterns/memory_hierarchy.zig").MemoryHierarchy;

    // Router pattern
    pub const RouterAgent = @import("patterns/router.zig").RouterAgent;
    pub const SimpleClassifier = @import("patterns/router.zig").SimpleClassifier;
    pub const Classifier = @import("patterns/router.zig").Classifier;

    // Fallback pattern
    pub const FallbackAgent = @import("patterns/fallback.zig").FallbackAgent;
    pub const AttemptResult = @import("patterns/fallback.zig").AttemptResult;
};

// Version information
pub const version = "0.40.0";
pub const zig_version = @import("builtin").zig_version;

test {
    std.testing.refAllDecls(@This());
    // Also test patterns
    _ = @import("patterns/sequential.zig");
    _ = @import("patterns/parallel.zig");
    _ = @import("patterns/reflection.zig");
    _ = @import("patterns/agents_as_tools.zig");
    _ = @import("patterns/react.zig");
    _ = @import("patterns/planning.zig");
    _ = @import("patterns/conversational.zig");
    _ = @import("patterns/task.zig");
    _ = @import("patterns/multiagent.zig");
    _ = @import("patterns/autonomous.zig");
    _ = @import("patterns/memory_hierarchy.zig");
    _ = @import("patterns/router.zig");
    _ = @import("patterns/fallback.zig");
}
