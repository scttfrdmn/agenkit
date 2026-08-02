///! Agent composition patterns.
///!
///! Simple, lightweight building blocks for composing agents:
///! - Sequential: Execute agents in order (pipeline)
///! - Parallel: Execute agents concurrently (ensemble)
///! - Conditional: Route to different agents based on conditions
///! - Fallback: Try agents in order until one succeeds (fault tolerance)
///!
///! These are minimal composition primitives. For richer agent patterns
///! with advanced features, see the `patterns` module.
pub mod conditional;
pub mod fallback;
pub mod parallel;
pub mod sequential;

pub use conditional::{
    and_conditions, content_contains, metadata_equals, metadata_has_key, not_condition,
    or_conditions, role_equals, Condition, ConditionalAgent, ConditionalRoute,
};
pub use fallback::FallbackAgent;
pub use parallel::{AgentResult, ParallelAgent};
pub use sequential::SequentialAgent;
