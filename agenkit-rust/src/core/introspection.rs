//! Introspection capability for examining agent internal state.
//!
//! This module provides introspection support - the ability for agents to examine
//! their own internal state, memory, and capabilities. This is distinct from the
//! Reflection pattern, which is about analyzing past performance.
//!
//! Key distinctions:
//! - Introspection (this module): "What do I know?" - State examination
//! - Reflection (pattern): "How did I do?" - Performance analysis
//!
//! # References
//! - Issue #301: Add Introspection Capability to Agent Interface
//! - ArXiv: Introspection of Thought Helps AI Agents (https://arxiv.org/abs/2507.08664)
//! - Biswas & Talukdar: Building Agentic AI Systems

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Result of agent introspection - a snapshot of internal state.
///
/// This provides a structured view into an agent's current state, including
/// its capabilities, memory contents, and any agent-specific internal state.
///
/// Design decisions:
/// - timestamp: UTC timestamp for when this snapshot was taken
/// - agent_name: Which agent was introspected
/// - capabilities: What the agent can do
/// - memory_state: Contents of agent's memory (None if no memory)
/// - internal_state: Agent-specific state information
/// - metadata: Extension point for additional information
///
/// # Example
/// ```
/// use agenkit::core::IntrospectionResult;
/// use std::collections::HashMap;
///
/// let result = IntrospectionResult::new(
///     "my-agent".to_string(),
///     vec!["reasoning".to_string(), "planning".to_string()],
///     None,
///     HashMap::new(),
///     HashMap::new(),
/// );
///
/// println!("Agent: {}", result.agent_name);
/// println!("Capabilities: {:?}", result.capabilities);
/// ```
///
/// Introspection is useful for:
/// - Debugging: Examine agent state during development
/// - Monitoring: Track agent state in production
/// - Coordination: Agents can inspect each other's capabilities
/// - Testing: Verify agent state in tests
/// - Explainability: Understand what an agent "knows"
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IntrospectionResult {
    /// UTC timestamp when introspection was performed
    pub timestamp: DateTime<Utc>,

    /// Name of the agent that was introspected
    pub agent_name: String,

    /// List of capability strings this agent supports
    pub capabilities: Vec<String>,

    /// Agent's memory contents (None if no memory)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub memory_state: Option<HashMap<String, serde_json::Value>>,

    /// Agent-specific internal state
    pub internal_state: HashMap<String, serde_json::Value>,

    /// Additional introspection metadata
    #[serde(default)]
    pub metadata: HashMap<String, serde_json::Value>,
}

impl IntrospectionResult {
    /// Create a new introspection result.
    ///
    /// # Arguments
    /// * `agent_name` - Name of the agent
    /// * `capabilities` - List of capabilities
    /// * `memory_state` - Optional memory state
    /// * `internal_state` - Agent-specific internal state
    /// * `metadata` - Additional metadata
    ///
    /// # Returns
    /// A new IntrospectionResult with current UTC timestamp
    ///
    /// # Panics
    /// Panics if `agent_name` is empty
    pub fn new(
        agent_name: String,
        capabilities: Vec<String>,
        memory_state: Option<HashMap<String, serde_json::Value>>,
        internal_state: HashMap<String, serde_json::Value>,
        metadata: HashMap<String, serde_json::Value>,
    ) -> Self {
        if agent_name.is_empty() {
            panic!("agent_name cannot be empty");
        }

        Self {
            timestamp: Utc::now(),
            agent_name,
            capabilities,
            memory_state,
            internal_state,
            metadata,
        }
    }

    /// Validate an introspection result.
    ///
    /// Checks that:
    /// - agent_name is not empty
    ///
    /// # Returns
    /// Ok(()) if valid, Err with description if invalid
    pub fn validate(&self) -> Result<(), String> {
        if self.agent_name.is_empty() {
            return Err("agent_name cannot be empty".to_string());
        }
        Ok(())
    }
}

/// Create a default introspection result for an agent.
///
/// This is a helper function that creates an introspection result with default
/// values for agents that don't have custom memory or internal state.
///
/// # Arguments
/// * `name` - Agent name
/// * `capabilities` - Agent capabilities
///
/// # Returns
/// IntrospectionResult with basic information
///
/// # Example
/// ```
/// use agenkit::core::create_default_introspection_result;
///
/// let result = create_default_introspection_result(
///     "my-agent".to_string(),
///     vec!["test".to_string()],
/// );
///
/// assert_eq!(result.agent_name, "my-agent");
/// assert_eq!(result.capabilities, vec!["test"]);
/// assert!(result.memory_state.is_none());
/// assert!(result.internal_state.is_empty());
/// ```
pub fn create_default_introspection_result(
    name: String,
    capabilities: Vec<String>,
) -> IntrospectionResult {
    IntrospectionResult::new(
        name,
        capabilities,
        None,
        HashMap::new(),
        HashMap::new(),
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn test_introspection_result_new() {
        let result = IntrospectionResult::new(
            "test-agent".to_string(),
            vec!["test".to_string(), "demo".to_string()],
            None,
            HashMap::new(),
            HashMap::new(),
        );

        assert_eq!(result.agent_name, "test-agent");
        assert_eq!(result.capabilities, vec!["test", "demo"]);
        assert!(result.memory_state.is_none());
        assert!(result.internal_state.is_empty());
        assert!(result.metadata.is_empty());
    }

    #[test]
    fn test_introspection_result_with_memory() {
        let mut memory = HashMap::new();
        memory.insert("short_term_count".to_string(), json!(5));
        memory.insert("long_term_count".to_string(), json!(10));

        let result = IntrospectionResult::new(
            "memory-agent".to_string(),
            vec!["memory".to_string()],
            Some(memory),
            HashMap::new(),
            HashMap::new(),
        );

        assert!(result.memory_state.is_some());
        let mem = result.memory_state.as_ref().unwrap();
        assert_eq!(mem.get("short_term_count"), Some(&json!(5)));
        assert_eq!(mem.get("long_term_count"), Some(&json!(10)));
    }

    #[test]
    fn test_introspection_result_with_internal_state() {
        let mut state = HashMap::new();
        state.insert("message_count".to_string(), json!(42));
        state.insert("has_context".to_string(), json!(true));

        let result = IntrospectionResult::new(
            "stateful-agent".to_string(),
            vec![],
            None,
            state,
            HashMap::new(),
        );

        assert_eq!(result.internal_state.get("message_count"), Some(&json!(42)));
        assert_eq!(result.internal_state.get("has_context"), Some(&json!(true)));
    }

    #[test]
    fn test_introspection_result_with_metadata() {
        let mut metadata = HashMap::new();
        metadata.insert("version".to_string(), json!("1.0"));
        metadata.insert("custom".to_string(), json!("data"));

        let result = IntrospectionResult::new(
            "test".to_string(),
            vec![],
            None,
            HashMap::new(),
            metadata,
        );

        assert_eq!(result.metadata.get("version"), Some(&json!("1.0")));
        assert_eq!(result.metadata.get("custom"), Some(&json!("data")));
    }

    #[test]
    #[should_panic(expected = "agent_name cannot be empty")]
    fn test_introspection_result_empty_name() {
        IntrospectionResult::new(
            "".to_string(),
            vec![],
            None,
            HashMap::new(),
            HashMap::new(),
        );
    }

    #[test]
    fn test_validate_success() {
        let result = IntrospectionResult::new(
            "test".to_string(),
            vec![],
            None,
            HashMap::new(),
            HashMap::new(),
        );

        assert!(result.validate().is_ok());
    }

    #[test]
    fn test_create_default_introspection_result() {
        let result = create_default_introspection_result(
            "simple-agent".to_string(),
            vec!["test".to_string(), "demo".to_string()],
        );

        assert_eq!(result.agent_name, "simple-agent");
        assert_eq!(result.capabilities, vec!["test", "demo"]);
        assert!(result.memory_state.is_none());
        assert!(result.internal_state.is_empty());
        assert!(result.metadata.is_empty());
    }

    #[test]
    fn test_timestamp_is_recent() {
        let before = Utc::now();
        let result = create_default_introspection_result("test".to_string(), vec![]);
        let after = Utc::now();

        assert!(result.timestamp >= before);
        assert!(result.timestamp <= after);
    }

    #[test]
    fn test_serialization() {
        let result = IntrospectionResult::new(
            "test".to_string(),
            vec!["cap1".to_string()],
            None,
            HashMap::new(),
            HashMap::new(),
        );

        let json = serde_json::to_string(&result).unwrap();
        let deserialized: IntrospectionResult = serde_json::from_str(&json).unwrap();

        assert_eq!(result.agent_name, deserialized.agent_name);
        assert_eq!(result.capabilities, deserialized.capabilities);
    }
}
