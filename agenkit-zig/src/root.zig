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
pub const StreamCallbacks = @import("agent.zig").StreamCallbacks;
pub const Result = @import("agent.zig").Result;
pub const EchoAgent = @import("agent.zig").EchoAgent;

// Introspection
pub const IntrospectionResult = @import("introspection.zig").IntrospectionResult;
pub const createDefaultIntrospectionResult = @import("introspection.zig").createDefaultIntrospectionResult;

// Tools
pub const Tool = @import("tool.zig").Tool;
pub const ToolError = @import("tool.zig").ToolError;
pub const ToolResult = @import("tool.zig").ToolResult;
pub const EchoTool = @import("tool.zig").EchoTool;

// Composition (minimal building blocks)
pub const composition = struct {
    pub const SequentialAgent = @import("composition.zig").SequentialAgent;
    pub const FallbackAgent = @import("composition.zig").FallbackAgent;
};

// Patterns
pub const patterns = struct {
    // Sequential pattern
    pub const SequentialAgent = @import("patterns/sequential.zig").SequentialAgent;
    pub const SequentialPattern = SequentialAgent; // DEPRECATED: Use SequentialAgent

    // Parallel pattern
    pub const ParallelAgent = @import("patterns/parallel.zig").ParallelAgent;
    pub const ParallelPattern = ParallelAgent; // DEPRECATED: Use ParallelAgent
    pub const defaultAggregator = @import("patterns/parallel.zig").defaultAggregator;
    pub const Aggregator = @import("patterns/parallel.zig").Aggregator;

    // Reflection pattern
    pub const ReflectionAgent = @import("patterns/reflection.zig").ReflectionAgent;
    pub const ReflectionStep = @import("patterns/reflection.zig").ReflectionStep;
    pub const StopReason = @import("patterns/reflection.zig").StopReason;
    pub const CritiqueFormat = @import("patterns/reflection.zig").CritiqueFormat;

    // Agents-as-Tools pattern
    pub const AgentTool = @import("patterns/agents_as_tools.zig").AgentTool;
    pub const ToolCoordinator = @import("patterns/agents_as_tools.zig").ToolCoordinator;
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
    pub const MemoryEntry = @import("patterns/memory.zig").MemoryEntry;
    pub const WorkingMemory = @import("patterns/memory.zig").WorkingMemory;
    pub const ShortTermMemory = @import("patterns/memory.zig").ShortTermMemory;
    pub const LongTermMemory = @import("patterns/memory.zig").LongTermMemory;
    pub const MemoryHierarchy = @import("patterns/memory.zig").MemoryHierarchy;

    // Router pattern
    pub const RouterAgent = @import("patterns/router.zig").RouterAgent;
    pub const SimpleClassifier = @import("patterns/router.zig").SimpleClassifier;
    pub const Classifier = @import("patterns/router.zig").Classifier;

    // Fallback pattern
    pub const FallbackAgent = @import("patterns/fallback.zig").FallbackAgent;
    pub const AttemptResult = @import("patterns/fallback.zig").AttemptResult;

    // Collaborative pattern
    pub const CollaborativeAgent = @import("patterns/collaborative.zig").CollaborativeAgent;
    pub const CollaborativeConfig = @import("patterns/collaborative.zig").CollaborativeConfig;
    pub const ConsensusFn = @import("patterns/collaborative.zig").ConsensusFn;
    pub const MergeFn = @import("patterns/collaborative.zig").MergeFn;
    pub const exactMatchConsensus = @import("patterns/collaborative.zig").exactMatchConsensus;
    pub const majorityAgreementConsensus = @import("patterns/collaborative.zig").majorityAgreementConsensus;
    pub const concatenateMerge = @import("patterns/collaborative.zig").concatenateMerge;
    pub const firstMerge = @import("patterns/collaborative.zig").firstMerge;

    // Human-in-Loop pattern
    pub const HumanInLoopAgent = @import("patterns/human_in_loop.zig").HumanInLoopAgent;
    pub const HumanInLoopConfig = @import("patterns/human_in_loop.zig").HumanInLoopConfig;
    pub const ApprovalRequest = @import("patterns/human_in_loop.zig").ApprovalRequest;
    pub const ApprovalResponse = @import("patterns/human_in_loop.zig").ApprovalResponse;
    pub const ApprovalFn = @import("patterns/human_in_loop.zig").ApprovalFn;
    pub const alwaysApprove = @import("patterns/human_in_loop.zig").alwaysApprove;
    pub const confidenceBasedApprove = @import("patterns/human_in_loop.zig").confidenceBasedApprove;

    // Supervisor pattern
    pub const SupervisorAgent = @import("patterns/supervisor.zig").SupervisorAgent;
    pub const Subtask = @import("patterns/supervisor.zig").Subtask;
    pub const Planner = @import("patterns/supervisor.zig").Planner;
    pub const SimplePlanner = @import("patterns/supervisor.zig").SimplePlanner;

    // Orchestration patterns (organizational module)
    pub const orchestration = @import("patterns/orchestration.zig");

    // Reasoning with Tools pattern
    pub const ReasoningWithToolsAgent = @import("patterns/reasoning_with_tools.zig").ReasoningWithToolsAgent;
    pub const ReasoningStepType = @import("patterns/reasoning_with_tools.zig").ReasoningStepType;
    pub const ReasoningStep = @import("patterns/reasoning_with_tools.zig").ReasoningStep;
    pub const ReasoningConfig = @import("patterns/reasoning_with_tools.zig").ReasoningConfig;
};

// LLM Adapters
pub const adapter = struct {
    // Base LLM interface
    pub const LLM = @import("adapter/llm.zig").LLM;
    pub const CallOptions = @import("adapter/llm.zig").CallOptions;
    pub const StreamIterator = @import("adapter/llm.zig").StreamIterator;
    pub const LLMError = @import("adapter/llm.zig").LLMError;

    // OpenAI adapter
    pub const OpenAILLM = @import("adapter/openai.zig").OpenAILLM;

    // Ollama adapter
    pub const OllamaLLM = @import("adapter/ollama.zig").OllamaLLM;

    // Gemini adapter
    pub const GeminiLLM = @import("adapter/gemini.zig").GeminiLLM;

    // Anthropic adapter
    pub const AnthropicLLM = @import("adapter/anthropic.zig").AnthropicLLM;

    // LiteLLM adapter
    pub const LiteLLMLLM = @import("adapter/litellm.zig").LiteLLMLLM;

    // AWS Bedrock adapter
    pub const BedrockLLM = @import("adapter/bedrock.zig").BedrockLLM;

    // OpenAI-compatible adapter (vLLM, llama.cpp, SGLang, etc.)
    pub const OpenAICompatibleLLM = @import("adapter/openai_compatible.zig").OpenAICompatibleLLM;
};

// Evaluation framework
pub const evaluation = @import("evaluation/mod.zig");

// Observability framework
pub const observability = @import("observability/mod.zig");

// Safety framework
pub const safety = @import("safety.zig");

// Middleware
pub const middleware = @import("middleware/mod.zig");

// Infrastructure for production systems
pub const infrastructure = @import("infrastructure/mod.zig");

// Techniques
pub const techniques = struct {
    // Reasoning techniques
    pub const reasoning = struct {
        pub const SelfConsistencyAgent = @import("techniques/reasoning/self_consistency.zig").SelfConsistencyAgent;
        pub const VotingStrategy = @import("techniques/reasoning/self_consistency.zig").VotingStrategy;
        pub const AnswerExtractor = @import("techniques/reasoning/self_consistency.zig").AnswerExtractor;
        pub const defaultAnswerExtractor = @import("techniques/reasoning/self_consistency.zig").defaultAnswerExtractor;

        pub const ChainOfThoughtAgent = @import("techniques/reasoning/chain_of_thought.zig").ChainOfThoughtAgent;
        pub const ChainOfThoughtConfig = @import("techniques/reasoning/chain_of_thought.zig").ChainOfThoughtConfig;

        pub const LeastToMostAgent = @import("techniques/reasoning/least_to_most.zig").LeastToMostAgent;
        pub const LeastToMostConfig = @import("techniques/reasoning/least_to_most.zig").LeastToMostConfig;
        pub const Subproblem = @import("techniques/reasoning/least_to_most.zig").Subproblem;
        pub const DecomposerFunc = @import("techniques/reasoning/least_to_most.zig").DecomposerFunc;

        pub const TreeOfThoughtAgent = @import("techniques/reasoning/tree_of_thought.zig").TreeOfThoughtAgent;
        pub const TreeOfThoughtConfig = @import("techniques/reasoning/tree_of_thought.zig").TreeOfThoughtConfig;
        pub const SearchStrategy = @import("techniques/reasoning/tree_of_thought.zig").SearchStrategy;
        pub const EvaluatorFunc = @import("techniques/reasoning/tree_of_thought.zig").EvaluatorFunc;
        pub const defaultEvaluator = @import("techniques/reasoning/tree_of_thought.zig").defaultEvaluator;

        pub const ReasoningTree = @import("techniques/reasoning/reasoning_tree.zig").ReasoningTree;
        pub const ReasoningNode = @import("techniques/reasoning/reasoning_tree.zig").ReasoningNode;
        pub const NodeState = @import("techniques/reasoning/reasoning_tree.zig").NodeState;
        pub const TreeStatistics = @import("techniques/reasoning/reasoning_tree.zig").TreeStatistics;
    };
};

// Version information
pub const version = "0.56.1";
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
    _ = @import("patterns/memory.zig");
    _ = @import("patterns/router.zig");
    _ = @import("patterns/fallback.zig");
    _ = @import("patterns/collaborative.zig");
    _ = @import("patterns/human_in_loop.zig");
    _ = @import("patterns/supervisor.zig");
    _ = @import("patterns/orchestration.zig");
    _ = @import("patterns/reasoning_with_tools.zig");
    // Also test adapters
    _ = @import("adapter/llm.zig");
    _ = @import("adapter/openai.zig");
    _ = @import("adapter/ollama.zig");
    _ = @import("adapter/gemini.zig");
    _ = @import("adapter/anthropic.zig");
    _ = @import("adapter/litellm.zig");
    _ = @import("adapter/bedrock.zig");
    _ = @import("adapter/openai_compatible.zig");
    // Also test observability
    _ = @import("observability/mod.zig");
    // Also test safety
    _ = @import("safety.zig");
    // Also test middleware
    _ = @import("middleware/mod.zig");
    // Also test infrastructure
    _ = @import("infrastructure/mod.zig");
    // Also test techniques
    _ = @import("techniques/reasoning/self_consistency.zig");
    _ = @import("techniques/reasoning/chain_of_thought.zig");
    _ = @import("techniques/reasoning/least_to_most.zig");
    _ = @import("techniques/reasoning/reasoning_tree.zig");
    _ = @import("techniques/reasoning/tree_of_thought.zig");
}
