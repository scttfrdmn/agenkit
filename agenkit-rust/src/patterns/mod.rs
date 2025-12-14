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

pub mod reflection;
pub mod agents_as_tools;
pub mod orchestration;
pub mod react;
pub mod conversational;
pub mod planning;
pub mod task;
pub mod multiagent;
pub mod autonomous;
pub mod memory;
pub mod reasoning_with_tools;
pub mod sequential;
pub mod parallel;
pub mod supervisor;
pub mod router;
pub mod collaborative;
pub mod human_in_loop;
pub mod fallback;

pub use reflection::{ReflectionAgent, ReflectionConfig, ReflectionStep, StopReason, CritiqueFormat};
pub use agents_as_tools::{AgentTool, agent_as_tool};
pub use orchestration::{SequentialPattern, ParallelPattern};
pub use react::{ReActAgent, ReActConfig, ReActStep, StopReason as ReActStopReason};
pub use conversational::{ConversationalAgent, ConversationalConfig};
pub use planning::{PlanningAgent, PlanningConfig, Plan, PlanStep, StepStatus, StepExecutor, DefaultStepExecutor};
pub use task::{Task, TaskConfig, execute_task};
pub use multiagent::{MultiAgentOrchestrator, ConsensusAgent, OrchestrationStrategy, VotingStrategy, AgentTask, TaskStatus};
pub use autonomous::{AutonomousAgent, AutonomousResult, Goal, GoalStatus, StopCondition, GoalWorker, create_goal};
pub use memory::{MemoryHierarchy, WorkingMemory, ShortTermMemory, LongTermMemory, MemoryEntry, create_memory_entry};
pub use reasoning_with_tools::{ReasoningWithToolsAgent, ReasoningWithToolsConfig, ReasoningStep, ReasoningStepType, ReasoningTrace};
pub use sequential::SequentialAgent;
pub use parallel::{ParallelAgent, AggregatorFunc, DefaultAggregators};
pub use supervisor::{SupervisorAgent, PlannerAgent, SimplePlanner, Subtask};
pub use router::{RouterAgent, RouterConfig, ClassifierAgent, SimpleClassifier, LLMClassifier};
pub use collaborative::{CollaborativeAgent, CollaborativeConfig, ConsensusFunc, MergeFunc, DefaultConsensusFunc, DefaultMergeFunc};
pub use human_in_loop::{HumanInLoopAgent, HumanInLoopConfig, ApprovalRequest, ApprovalResponse, ApprovalFunc, simple_approval_func, confidence_based_approval_func};
pub use fallback::{FallbackAgent, RecoveryAgent, RecoveryFunc, DefaultRecovery};
