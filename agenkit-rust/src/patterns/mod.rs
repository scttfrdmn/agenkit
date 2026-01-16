//! Agent Patterns
//!
//! This module provides reusable patterns for composing and orchestrating agents.
//!
//! Available patterns:
//! - **Reflection**: Iterative self-critique and refinement
//! - **Agents as Tools**: Hierarchical agent delegation
//! - **Orchestration**: Sequential and parallel composition
//! - **ReAct**: Reasoning and acting with tool use
//! - **Planning**: Task decomposition and execution
//! - **Conversational**: Multi-turn dialogue management
//! - **Task**: One-shot execution with lifecycle management
//! - **Multiagent**: Multi-agent collaboration and consensus
//! - **Autonomous**: Goal-directed self-organizing agents
//! - **Memory Hierarchy**: Three-tier memory system
//! - **Reasoning with Tools**: Interleaved reasoning and tool usage
//! - **Sequential**: Pipeline-style agent composition
//! - **Parallel**: Concurrent agent execution with aggregation
//! - **Supervisor**: Hierarchical coordination with specialists
//! - **Router**: Conditional agent selection based on classification
//! - **Collaborative**: Peer-to-peer iterative refinement
//! - **Human-in-Loop**: Agent execution with human approval
//! - **Fallback**: Sequential retry with error recovery

pub mod agents_as_tools;
pub mod autonomous;
pub mod collaborative;
pub mod conversational;
pub mod fallback;
pub mod human_in_loop;
pub mod memory;
pub mod multiagent;
pub mod orchestration;
pub mod parallel;
pub mod planning;
pub mod react;
pub mod reasoning_with_tools;
pub mod reflection;
pub mod router;
pub mod sequential;
pub mod supervisor;
pub mod task;

pub use agents_as_tools::{agent_as_tool, AgentTool};
pub use autonomous::{
    create_goal, AutonomousAgent, AutonomousResult, Goal, GoalStatus, GoalWorker, StopCondition,
};
pub use collaborative::{
    CollaborativeAgent, CollaborativeConfig, ConsensusFunc, DefaultConsensusFunc, DefaultMergeFunc,
    MergeFunc,
};
pub use conversational::{ConversationalAgent, ConversationalConfig};
pub use fallback::{DefaultRecovery, FallbackAgent, RecoveryAgent, RecoveryFunc};
pub use human_in_loop::{
    confidence_based_approval_func, simple_approval_func, ApprovalFunc, ApprovalRequest,
    ApprovalResponse, HumanInLoopAgent, HumanInLoopConfig,
};
pub use memory::{
    create_memory_entry, LongTermMemory, MemoryEntry, MemoryHierarchy, ShortTermMemory,
    WorkingMemory,
};
pub use multiagent::{
    AgentTask, ConsensusAgent, MultiAgentOrchestrator, OrchestrationStrategy, TaskStatus,
    VotingStrategy,
};
pub use orchestration::{ParallelPattern, SequentialPattern};
pub use parallel::{AggregatorFunc, DefaultAggregators, ParallelAgent};
pub use planning::{
    DefaultStepExecutor, Plan, PlanStep, PlanningAgent, PlanningConfig, StepExecutor, StepStatus,
};
pub use react::{ReActAgent, ReActConfig, ReActStep, StopReason as ReActStopReason};
pub use reasoning_with_tools::{
    ReasoningStep, ReasoningStepType, ReasoningTrace, ReasoningWithToolsAgent,
    ReasoningWithToolsConfig,
};
pub use reflection::{
    CritiqueFormat, ReflectionAgent, ReflectionConfig, ReflectionStep, StopReason,
};
pub use router::{ClassifierAgent, LLMClassifier, RouterAgent, RouterConfig, SimpleClassifier};
pub use sequential::SequentialAgent;
pub use supervisor::{PlannerAgent, SimplePlanner, Subtask, SupervisorAgent};
pub use task::{execute_task, Task, TaskConfig};
