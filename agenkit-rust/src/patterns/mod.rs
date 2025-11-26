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

pub mod reflection;
pub mod agents_as_tools;
pub mod orchestration;
pub mod react;
pub mod conversational;

// These patterns use tokio-specific features, only available in native builds
#[cfg(feature = "native")]
pub mod planning;
#[cfg(feature = "native")]
pub mod task;
#[cfg(feature = "native")]
pub mod multiagent;
#[cfg(feature = "native")]
pub mod autonomous;
#[cfg(feature = "native")]
pub mod memory;
#[cfg(feature = "native")]
pub mod reasoning_with_tools;

pub use reflection::{ReflectionAgent, ReflectionConfig, ReflectionStep, StopReason, CritiqueFormat};
pub use agents_as_tools::{AgentTool, agent_as_tool};
pub use orchestration::{SequentialPattern, ParallelPattern};
pub use react::{ReActAgent, ReActConfig, ReActStep, StopReason as ReActStopReason};
pub use conversational::{ConversationalAgent, ConversationalConfig};

#[cfg(feature = "native")]
pub use planning::{PlanningAgent, PlanningConfig, Plan, PlanStep, StepStatus, StepExecutor, DefaultStepExecutor};
#[cfg(feature = "native")]
pub use task::{Task, TaskConfig, execute_task};
#[cfg(feature = "native")]
pub use multiagent::{MultiAgentOrchestrator, ConsensusAgent, OrchestrationStrategy, VotingStrategy, AgentTask, TaskStatus};
#[cfg(feature = "native")]
pub use autonomous::{AutonomousAgent, AutonomousResult, Goal, GoalStatus, StopCondition, GoalWorker, create_goal};
#[cfg(feature = "native")]
pub use memory::{MemoryHierarchy, WorkingMemory, ShortTermMemory, LongTermMemory, MemoryEntry, create_memory_entry};
#[cfg(feature = "native")]
pub use reasoning_with_tools::{ReasoningWithToolsAgent, ReasoningWithToolsConfig, ReasoningStep, ReasoningStepType, ReasoningTrace};
