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

pub mod reflection;
pub mod agents_as_tools;
pub mod orchestration;
pub mod react;
pub mod planning;
pub mod conversational;
pub mod task;
pub mod multiagent;
pub mod autonomous;

pub use reflection::{ReflectionAgent, ReflectionConfig, ReflectionStep, StopReason, CritiqueFormat};
pub use agents_as_tools::{AgentTool, agent_as_tool};
pub use orchestration::{SequentialPattern, ParallelPattern};
pub use react::{ReActAgent, ReActConfig, ReActStep, StopReason as ReActStopReason};
pub use planning::{PlanningAgent, PlanningConfig, Plan, PlanStep, StepStatus, StepExecutor, DefaultStepExecutor};
pub use conversational::{ConversationalAgent, ConversationalConfig};
pub use task::{Task, TaskConfig, execute_task};
pub use multiagent::{MultiAgentOrchestrator, ConsensusAgent, OrchestrationStrategy, VotingStrategy, AgentTask, TaskStatus};
pub use autonomous::{AutonomousAgent, AutonomousResult, Goal, GoalStatus, StopCondition, GoalWorker, create_goal};
