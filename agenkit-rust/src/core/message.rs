///! Message types for agent communication.
///!
///! This module provides the core Message type for agent communication,
///! following the same design as TypeScript and Go implementations.
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use thiserror::Error;

/// Error types for message operations.
#[derive(Error, Debug)]
pub enum MessageError {
    #[error("message role must be a non-empty string")]
    EmptyRole,

    #[error("message content cannot be null")]
    NullContent,

    #[error("invalid message format: {0}")]
    InvalidFormat(String),

    #[error("serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
}

/// Universal message format for agent communication.
///
/// Design decisions:
/// - role: Identifies message source ("user", "assistant", "system", "tool")
/// - content: Flexible serde_json::Value for any serializable data
/// - metadata: Extension point for framework-specific data
/// - timestamp: UTC timestamp for ordering and debugging
///
/// # Example
/// ```
/// use agenkit::core::Message;
/// use serde_json::json;
///
/// let msg = Message::new("user", json!("Hello, agent!"));
/// assert_eq!(msg.role, "user");
/// ```
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Message {
    /// Message source: "user", "assistant", "system", or "tool"
    pub role: String,

    /// Message content - can be string, object, or any serializable data
    pub content: serde_json::Value,

    /// Optional metadata for framework-specific data
    #[serde(default)]
    pub metadata: HashMap<String, serde_json::Value>,

    /// UTC timestamp - defaults to now if not provided
    #[serde(default = "Utc::now")]
    pub timestamp: DateTime<Utc>,
}

impl Message {
    /// Create a new message with the given role and content.
    ///
    /// # Arguments
    /// * `role` - Message role (e.g., "user", "assistant")
    /// * `content` - Message content as serde_json::Value
    ///
    /// # Example
    /// ```
    /// use agenkit::core::Message;
    /// use serde_json::json;
    ///
    /// let msg = Message::new("user", json!("Hello"));
    /// assert_eq!(msg.role, "user");
    /// ```
    pub fn new(role: impl Into<String>, content: serde_json::Value) -> Self {
        Self {
            role: role.into(),
            content,
            metadata: HashMap::new(),
            timestamp: Utc::now(),
        }
    }

    /// Create a message with content as a string.
    ///
    /// This is a convenience method for the common case of string content.
    ///
    /// # Example
    /// ```
    /// use agenkit::core::Message;
    ///
    /// let msg = Message::with_text("user", "Hello, agent!");
    /// ```
    pub fn with_text(role: impl Into<String>, content: impl Into<String>) -> Self {
        Self::new(role, serde_json::Value::String(content.into()))
    }

    /// Add metadata to the message.
    ///
    /// # Example
    /// ```
    /// use agenkit::core::Message;
    /// use serde_json::json;
    ///
    /// let msg = Message::with_text("user", "Hello")
    ///     .with_metadata("session_id", json!("abc123"));
    /// ```
    pub fn with_metadata(mut self, key: impl Into<String>, value: serde_json::Value) -> Self {
        self.metadata.insert(key.into(), value);
        self
    }

    /// Validate the message according to security constraints.
    ///
    /// Checks:
    /// - Role is non-empty
    /// - Content is not null
    ///
    /// # Errors
    /// Returns MessageError if validation fails.
    pub fn validate(&self) -> Result<(), MessageError> {
        if self.role.is_empty() {
            return Err(MessageError::EmptyRole);
        }

        if self.content.is_null() {
            return Err(MessageError::NullContent);
        }

        Ok(())
    }

    /// Get content as string if it's a string value.
    ///
    /// Returns None if content is not a string.
    pub fn content_as_str(&self) -> Option<&str> {
        self.content.as_str()
    }
}

/// Result from tool execution.
///
/// Contains the output from a tool call along with metadata about the execution.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolResult {
    /// Tool output - can be any serializable data
    pub output: serde_json::Value,

    /// Whether the tool execution was successful
    pub success: bool,

    /// Optional error message if execution failed
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<String>,

    /// Optional metadata about the execution
    #[serde(default)]
    pub metadata: HashMap<String, serde_json::Value>,
}

impl ToolResult {
    /// Create a successful tool result.
    pub fn success(output: serde_json::Value) -> Self {
        Self {
            output,
            success: true,
            error: None,
            metadata: HashMap::new(),
        }
    }

    /// Create a failed tool result with error message.
    pub fn error(error: impl Into<String>) -> Self {
        Self {
            output: serde_json::Value::Null,
            success: false,
            error: Some(error.into()),
            metadata: HashMap::new(),
        }
    }

    /// Add metadata to the tool result.
    pub fn with_metadata(mut self, key: impl Into<String>, value: serde_json::Value) -> Self {
        self.metadata.insert(key.into(), value);
        self
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn test_message_new() {
        let msg = Message::new("user", json!("Hello"));
        assert_eq!(msg.role, "user");
        assert_eq!(msg.content, json!("Hello"));
        assert!(msg.metadata.is_empty());
    }

    #[test]
    fn test_message_with_text() {
        let msg = Message::with_text("user", "Hello, agent!");
        assert_eq!(msg.role, "user");
        assert_eq!(msg.content_as_str(), Some("Hello, agent!"));
    }

    #[test]
    fn test_message_with_metadata() {
        let msg = Message::with_text("user", "Hello")
            .with_metadata("session_id", json!("abc123"))
            .with_metadata("user_id", json!(42));

        assert_eq!(msg.metadata.len(), 2);
        assert_eq!(msg.metadata.get("session_id"), Some(&json!("abc123")));
        assert_eq!(msg.metadata.get("user_id"), Some(&json!(42)));
    }

    #[test]
    fn test_message_validate_success() {
        let msg = Message::with_text("user", "Hello");
        assert!(msg.validate().is_ok());
    }

    #[test]
    fn test_message_validate_empty_role() {
        let msg = Message::new("", json!("Hello"));
        assert!(matches!(msg.validate(), Err(MessageError::EmptyRole)));
    }

    #[test]
    fn test_message_validate_null_content() {
        let msg = Message::new("user", serde_json::Value::Null);
        assert!(matches!(msg.validate(), Err(MessageError::NullContent)));
    }

    #[test]
    fn test_message_serialization() {
        let msg = Message::with_text("user", "Hello").with_metadata("key", json!("value"));

        let json = serde_json::to_string(&msg).unwrap();
        let deserialized: Message = serde_json::from_str(&json).unwrap();

        assert_eq!(deserialized.role, msg.role);
        assert_eq!(deserialized.content, msg.content);
        assert_eq!(deserialized.metadata.get("key"), msg.metadata.get("key"));
    }

    #[test]
    fn test_tool_result_success() {
        let result = ToolResult::success(json!({"answer": 42}));
        assert!(result.success);
        assert!(result.error.is_none());
        assert_eq!(result.output, json!({"answer": 42}));
    }

    #[test]
    fn test_tool_result_error() {
        let result = ToolResult::error("Something went wrong");
        assert!(!result.success);
        assert_eq!(result.error, Some("Something went wrong".to_string()));
    }

    #[test]
    fn test_tool_result_with_metadata() {
        let result = ToolResult::success(json!("OK")).with_metadata("duration_ms", json!(123));

        assert_eq!(result.metadata.get("duration_ms"), Some(&json!(123)));
    }
}
