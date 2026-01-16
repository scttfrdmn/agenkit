//! Tests for introspection capability.

use super::agent::{Agent, AgentError};
use super::introspection::{create_default_introspection_result, IntrospectionResult};
use super::message::Message;
use async_trait::async_trait;
use serde_json::json;
use std::collections::HashMap;
use std::sync::{Arc, Mutex};

// Test agent implementations

struct SimpleAgent {
    name: String,
    capabilities: Vec<String>,
}

#[async_trait]
impl Agent for SimpleAgent {
    fn name(&self) -> &str {
        &self.name
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        Ok(Message::with_text(
            "assistant",
            format!("Processed: {}", message.content_as_str().unwrap_or("")),
        ))
    }

    fn capabilities(&self) -> Vec<String> {
        self.capabilities.clone()
    }

    fn introspect(&self) -> IntrospectionResult {
        create_default_introspection_result(self.name().to_string(), self.capabilities())
    }
}

struct AgentWithMemory {
    name: String,
    capabilities: Vec<String>,
    memory: Arc<Mutex<MemoryState>>,
    message_count: Arc<Mutex<usize>>,
}

struct MemoryState {
    short_term: Vec<String>,
    long_term: Vec<String>,
}

impl AgentWithMemory {
    fn new(name: String, capabilities: Vec<String>) -> Self {
        let memory = MemoryState {
            short_term: vec!["item1".to_string(), "item2".to_string()],
            long_term: vec!["memory1".to_string()],
        };

        Self {
            name,
            capabilities,
            memory: Arc::new(Mutex::new(memory)),
            message_count: Arc::new(Mutex::new(0)),
        }
    }
}

#[async_trait]
impl Agent for AgentWithMemory {
    fn name(&self) -> &str {
        &self.name
    }

    async fn process(&self, _message: Message) -> Result<Message, AgentError> {
        let mut count = self.message_count.lock().unwrap();
        *count += 1;

        Ok(Message::with_text("assistant", "Processed"))
    }

    fn capabilities(&self) -> Vec<String> {
        self.capabilities.clone()
    }

    fn introspect(&self) -> IntrospectionResult {
        let memory = self.memory.lock().unwrap();
        let count = self.message_count.lock().unwrap();

        let mut memory_state = HashMap::new();
        memory_state.insert(
            "short_term_count".to_string(),
            json!(memory.short_term.len()),
        );
        memory_state.insert("long_term_count".to_string(), json!(memory.long_term.len()));

        let mut internal_state = HashMap::new();
        internal_state.insert("message_count".to_string(), json!(*count));
        internal_state.insert("has_memory".to_string(), json!(true));

        IntrospectionResult::new(
            self.name().to_string(),
            self.capabilities(),
            Some(memory_state),
            internal_state,
            HashMap::new(),
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_introspection_result_creation() {
        let result = IntrospectionResult::new(
            "test".to_string(),
            vec!["test".to_string()],
            None,
            HashMap::new(),
            HashMap::new(),
        );

        assert_eq!(result.agent_name, "test");
        assert_eq!(result.capabilities, vec!["test"]);
        assert!(result.memory_state.is_none());
        assert!(result.internal_state.is_empty());
    }

    #[test]
    fn test_introspection_result_validation() {
        let valid_result = IntrospectionResult::new(
            "test".to_string(),
            vec!["test".to_string()],
            None,
            HashMap::new(),
            HashMap::new(),
        );

        assert!(valid_result.validate().is_ok());
    }

    #[test]
    #[should_panic(expected = "agent_name cannot be empty")]
    fn test_introspection_result_empty_name() {
        IntrospectionResult::new("".to_string(), vec![], None, HashMap::new(), HashMap::new());
    }

    #[test]
    fn test_simple_agent_introspection() {
        let agent = SimpleAgent {
            name: "simple".to_string(),
            capabilities: vec!["test".to_string(), "simple".to_string()],
        };

        let result = agent.introspect();

        assert_eq!(result.agent_name, "simple");
        assert_eq!(result.capabilities, vec!["test", "simple"]);
        assert!(result.memory_state.is_none());
        assert!(result.internal_state.is_empty());
    }

    #[test]
    fn test_simple_agent_has_recent_timestamp() {
        let agent = SimpleAgent {
            name: "simple".to_string(),
            capabilities: vec![],
        };

        let before = chrono::Utc::now();
        let result = agent.introspect();
        let after = chrono::Utc::now();

        assert!(result.timestamp >= before);
        assert!(result.timestamp <= after);
    }

    #[test]
    fn test_agent_with_memory_introspection() {
        let agent = AgentWithMemory::new(
            "memory_agent".to_string(),
            vec!["memory".to_string(), "stateful".to_string()],
        );

        let result = agent.introspect();

        assert_eq!(result.agent_name, "memory_agent");
        assert_eq!(result.capabilities, vec!["memory", "stateful"]);
        assert!(result.memory_state.is_some());

        let memory = result.memory_state.as_ref().unwrap();
        assert_eq!(memory.get("short_term_count"), Some(&json!(2)));
        assert_eq!(memory.get("long_term_count"), Some(&json!(1)));

        assert_eq!(result.internal_state.get("message_count"), Some(&json!(0)));
        assert_eq!(result.internal_state.get("has_memory"), Some(&json!(true)));
    }

    #[tokio::test]
    async fn test_agent_with_memory_reflects_state_changes() {
        let agent = AgentWithMemory::new("memory_agent".to_string(), vec![]);

        // Initial state
        let result1 = agent.introspect();
        assert_eq!(result1.internal_state.get("message_count"), Some(&json!(0)));

        // Process a message
        let _ = agent.process(Message::with_text("user", "test")).await;

        // State should have changed
        let result2 = agent.introspect();
        assert_eq!(result2.internal_state.get("message_count"), Some(&json!(1)));
    }

    #[test]
    fn test_create_default_introspection_result() {
        let result = create_default_introspection_result(
            "test-agent".to_string(),
            vec!["test".to_string(), "demo".to_string()],
        );

        assert_eq!(result.agent_name, "test-agent");
        assert_eq!(result.capabilities, vec!["test", "demo"]);
        assert!(result.memory_state.is_none());
        assert!(result.internal_state.is_empty());
        assert!(result.metadata.is_empty());
    }

    #[test]
    fn test_create_default_introspection_result_no_capabilities() {
        let result = create_default_introspection_result("simple-agent".to_string(), vec![]);

        assert_eq!(result.agent_name, "simple-agent");
        assert!(result.capabilities.is_empty());
    }

    #[test]
    fn test_introspection_with_metadata() {
        let mut metadata = HashMap::new();
        metadata.insert("custom".to_string(), json!("data"));
        metadata.insert("version".to_string(), json!("1.0"));

        let result =
            IntrospectionResult::new("test".to_string(), vec![], None, HashMap::new(), metadata);

        assert_eq!(result.metadata.get("custom"), Some(&json!("data")));
        assert_eq!(result.metadata.get("version"), Some(&json!("1.0")));
    }
}
