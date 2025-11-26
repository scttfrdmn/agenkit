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

pub mod reflection;
pub mod agents_as_tools;
pub mod orchestration;
pub mod react;
pub mod planning;

pub use reflection::{ReflectionAgent, ReflectionConfig, ReflectionStep, StopReason, CritiqueFormat};
pub use agents_as_tools::{AgentTool, agent_as_tool};
pub use orchestration::{SequentialPattern, ParallelPattern};
pub use react::{ReActAgent, ReActConfig, ReActStep, StopReason as ReActStopReason};
pub use planning::{PlanningAgent, PlanningConfig, Plan, PlanStep, StepStatus, StepExecutor, DefaultStepExecutor};
