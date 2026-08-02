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

    #[error("message role exceeds maximum length of 20 characters (got {0})")]
    RoleTooLong(usize),

    #[error("invalid message role: {0}. Must be one of: user, assistant, system, tool, agent")]
    InvalidRole(String),

    #[error("message content cannot be null")]
    NullContent,

    #[error("message content exceeds maximum size of {max} bytes (got {actual} bytes)")]
    ContentTooLarge { max: usize, actual: usize },

    #[error("message metadata exceeds maximum of {max} keys (got {actual})")]
    TooManyMetadataKeys { max: usize, actual: usize },

    #[error("metadata key '{key}' exceeds maximum length of {max} characters (got {actual})")]
    MetadataKeyTooLong {
        key: String,
        max: usize,
        actual: usize,
    },

    #[error(
        "metadata value for key '{key}' exceeds maximum size of {max} bytes (got {actual} bytes)"
    )]
    MetadataValueTooLarge {
        key: String,
        max: usize,
        actual: usize,
    },

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
    /// - Role is non-empty and <= 20 characters
    /// - Role is one of: user, assistant, system, tool, agent
    /// - Content is not null
    /// - Content size <= 16MB
    /// - Metadata has <= 100 keys
    /// - Each metadata key <= 50 characters
    /// - Each metadata value <= 16MB
    ///
    /// # Errors
    /// Returns MessageError if validation fails.
    pub fn validate(&self) -> Result<(), MessageError> {
        // Role validation
        if self.role.is_empty() {
            return Err(MessageError::EmptyRole);
        }

        if self.role.len() > 20 {
            return Err(MessageError::RoleTooLong(self.role.len()));
        }

        // Validate role is one of the allowed values
        let allowed_roles = ["user", "assistant", "system", "tool", "agent"];
        if !allowed_roles.contains(&self.role.as_str()) {
            return Err(MessageError::InvalidRole(self.role.clone()));
        }

        // Content validation
        if self.content.is_null() {
            return Err(MessageError::NullContent);
        }

        // Content size validation - max 16MB
        let content_str = self.content.to_string();
        let content_size = content_str.as_bytes().len();
        let max_content_size = 16 * 1024 * 1024; // 16MB

        if content_size > max_content_size {
            return Err(MessageError::ContentTooLarge {
                max: max_content_size,
                actual: content_size,
            });
        }

        // Metadata validation
        if !self.metadata.is_empty() {
            // Max 100 keys
            if self.metadata.len() > 100 {
                return Err(MessageError::TooManyMetadataKeys {
                    max: 100,
                    actual: self.metadata.len(),
                });
            }

            // Validate each key and value
            let max_key_length = 50;
            let max_value_size = 16 * 1024 * 1024; // 16MB

            for (key, value) in &self.metadata {
                // Key length validation
                if key.len() > max_key_length {
                    return Err(MessageError::MetadataKeyTooLong {
                        key: key.clone(),
                        max: max_key_length,
                        actual: key.len(),
                    });
                }

                // Value size validation
                let value_str = value.to_string();
                let value_size = value_str.as_bytes().len();

                if value_size > max_value_size {
                    return Err(MessageError::MetadataValueTooLarge {
                        key: key.clone(),
                        max: max_value_size,
                        actual: value_size,
                    });
                }
            }
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

    // Size validation tests
    #[test]
    fn test_validate_role_too_long() {
        let msg = Message::new("a".repeat(21), json!("Hello"));
        assert!(matches!(msg.validate(), Err(MessageError::RoleTooLong(21))));
    }

    #[test]
    fn test_validate_invalid_role() {
        let msg = Message::new("invalid_role", json!("Hello"));
        assert!(matches!(msg.validate(), Err(MessageError::InvalidRole(_))));
    }

    #[test]
    fn test_validate_all_valid_roles() {
        let valid_roles = ["user", "assistant", "system", "tool", "agent"];
        for role in &valid_roles {
            let msg = Message::new(*role, json!("Hello"));
            assert!(msg.validate().is_ok());
        }
    }

    #[test]
    fn test_validate_content_too_large() {
        // Create a large string (>16MB)
        let large_content = "a".repeat(17 * 1024 * 1024); // 17MB
        let msg = Message::new("user", json!(large_content));
        assert!(matches!(
            msg.validate(),
            Err(MessageError::ContentTooLarge { .. })
        ));
    }

    #[test]
    fn test_validate_content_under_limit() {
        // Create a 1MB string
        let content = "a".repeat(1024 * 1024);
        let msg = Message::new("user", json!(content));
        assert!(msg.validate().is_ok());
    }

    #[test]
    fn test_validate_too_many_metadata_keys() {
        let mut msg = Message::new("user", json!("Hello"));
        for i in 0..101 {
            msg = msg.with_metadata(format!("key{}", i), json!("value"));
        }
        assert!(matches!(
            msg.validate(),
            Err(MessageError::TooManyMetadataKeys { .. })
        ));
    }

    #[test]
    fn test_validate_metadata_key_too_long() {
        let long_key = "a".repeat(51);
        let msg = Message::new("user", json!("Hello")).with_metadata(long_key, json!("value"));
        assert!(matches!(
            msg.validate(),
            Err(MessageError::MetadataKeyTooLong { .. })
        ));
    }

    #[test]
    fn test_validate_metadata_value_too_large() {
        let large_value = "a".repeat(17 * 1024 * 1024); // 17MB
        let msg = Message::new("user", json!("Hello")).with_metadata("key", json!(large_value));
        assert!(matches!(
            msg.validate(),
            Err(MessageError::MetadataValueTooLarge { .. })
        ));
    }

    #[test]
    fn test_validate_metadata_value_under_limit() {
        let value = "a".repeat(1024 * 1024); // 1MB
        let msg = Message::new("user", json!("Hello")).with_metadata("key", json!(value));
        assert!(msg.validate().is_ok());
    }

    #[test]
    fn test_validate_100_metadata_keys() {
        let mut msg = Message::new("user", json!("Hello"));
        for i in 0..100 {
            msg = msg.with_metadata(format!("key{}", i), json!("value"));
        }
        assert!(msg.validate().is_ok());
    }

    #[test]
    fn test_validate_50_char_metadata_key() {
        let key = "a".repeat(50);
        let msg = Message::new("user", json!("Hello")).with_metadata(key, json!("value"));
        assert!(msg.validate().is_ok());
    }
}
