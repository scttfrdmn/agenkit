//! Core checkpoint data structure.

use crate::core::Message;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use uuid::Uuid;

/// Checkpoint data structure for durable execution.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Checkpoint {
    /// Unique checkpoint identifier
    pub checkpoint_id: String,

    /// Session identifier (groups related checkpoints)
    pub session_id: String,

    /// Name of the agent being checkpointed
    pub agent_name: String,

    /// When the checkpoint was created
    pub timestamp: DateTime<Utc>,

    /// Sequential step number within session
    pub step_number: usize,

    /// Custom agent state data
    pub state: serde_json::Value,

    /// Conversation history up to this point
    pub messages: Vec<Message>,

    /// Optional metadata (cost, tokens, etc.)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub metadata: Option<serde_json::Value>,

    /// Parent checkpoint for history chain
    #[serde(skip_serializing_if = "Option::is_none")]
    pub parent_checkpoint_id: Option<String>,
}

impl Checkpoint {
    /// Create a new checkpoint.
    pub fn new(
        session_id: String,
        agent_name: String,
        step_number: usize,
        state: serde_json::Value,
        messages: Vec<Message>,
    ) -> Self {
        Self {
            checkpoint_id: Uuid::new_v4().to_string(),
            session_id,
            agent_name,
            timestamp: Utc::now(),
            step_number,
            state,
            messages,
            metadata: None,
            parent_checkpoint_id: None,
        }
    }

    /// Set metadata.
    pub fn with_metadata(mut self, metadata: serde_json::Value) -> Self {
        self.metadata = Some(metadata);
        self
    }

    /// Set parent checkpoint ID.
    pub fn with_parent(mut self, parent_id: String) -> Self {
        self.parent_checkpoint_id = Some(parent_id);
        self
    }

    /// Convert checkpoint to JSON string.
    pub fn to_json(&self) -> Result<String, serde_json::Error> {
        serde_json::to_string_pretty(self)
    }

    /// Create checkpoint from JSON string.
    pub fn from_json(json: &str) -> Result<Self, serde_json::Error> {
        serde_json::from_str(json)
    }

    /// Convert to dictionary representation.
    pub fn to_dict(&self) -> HashMap<String, serde_json::Value> {
        let mut dict = HashMap::new();
        dict.insert("checkpoint_id".to_string(), serde_json::json!(self.checkpoint_id));
        dict.insert("session_id".to_string(), serde_json::json!(self.session_id));
        dict.insert("agent_name".to_string(), serde_json::json!(self.agent_name));
        dict.insert("timestamp".to_string(), serde_json::json!(self.timestamp.to_rfc3339()));
        dict.insert("step_number".to_string(), serde_json::json!(self.step_number));
        dict.insert("state".to_string(), self.state.clone());
        dict.insert("messages".to_string(), serde_json::json!(self.messages));

        if let Some(ref metadata) = self.metadata {
            dict.insert("metadata".to_string(), metadata.clone());
        }

        if let Some(ref parent_id) = self.parent_checkpoint_id {
            dict.insert("parent_checkpoint_id".to_string(), serde_json::json!(parent_id));
        }

        dict
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_checkpoint_creation() {
        let checkpoint = Checkpoint::new(
            "session-1".to_string(),
            "test-agent".to_string(),
            1,
            serde_json::json!({"counter": 42}),
            vec![],
        );

        assert_eq!(checkpoint.session_id, "session-1");
        assert_eq!(checkpoint.agent_name, "test-agent");
        assert_eq!(checkpoint.step_number, 1);
        assert!(checkpoint.metadata.is_none());
        assert!(checkpoint.parent_checkpoint_id.is_none());
    }

    #[test]
    fn test_checkpoint_with_metadata_and_parent() {
        let checkpoint = Checkpoint::new(
            "session-1".to_string(),
            "test-agent".to_string(),
            2,
            serde_json::json!({"data": "value"}),
            vec![],
        )
        .with_metadata(serde_json::json!({"cost": 0.05}))
        .with_parent("parent-id".to_string());

        assert!(checkpoint.metadata.is_some());
        assert_eq!(checkpoint.parent_checkpoint_id, Some("parent-id".to_string()));
    }

    #[test]
    fn test_checkpoint_json_serialization() {
        let checkpoint = Checkpoint::new(
            "session-1".to_string(),
            "test-agent".to_string(),
            1,
            serde_json::json!({"key": "value"}),
            vec![],
        );

        let json = checkpoint.to_json().unwrap();
        let deserialized = Checkpoint::from_json(&json).unwrap();

        assert_eq!(checkpoint.checkpoint_id, deserialized.checkpoint_id);
        assert_eq!(checkpoint.session_id, deserialized.session_id);
        assert_eq!(checkpoint.step_number, deserialized.step_number);
    }

    #[test]
    fn test_checkpoint_to_dict() {
        let checkpoint = Checkpoint::new(
            "session-1".to_string(),
            "test-agent".to_string(),
            5,
            serde_json::json!({"active": true}),
            vec![],
        );

        let dict = checkpoint.to_dict();

        assert!(dict.contains_key("checkpoint_id"));
        assert!(dict.contains_key("session_id"));
        assert!(dict.contains_key("timestamp"));
        assert_eq!(dict.get("step_number"), Some(&serde_json::json!(5)));
    }
}
