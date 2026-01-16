//! Optimized message construction utilities
//!
//! Provides zero-allocation or reduced-allocation helpers for common message patterns.

use crate::core::Message;
use std::collections::HashMap;

/// Builder for creating messages with optimized allocations
pub struct MessageBuilder {
    role: String,
    content: serde_json::Value,
    metadata: HashMap<String, serde_json::Value>,
    metadata_capacity: usize,
}

impl MessageBuilder {
    /// Create a new message builder with a given role
    pub fn new(role: impl Into<String>) -> Self {
        Self {
            role: role.into(),
            content: serde_json::Value::Null,
            metadata: HashMap::new(),
            metadata_capacity: 0,
        }
    }

    /// Create a builder for a user message (most common)
    pub fn user() -> Self {
        Self::new(super::string_pool::roles::USER)
    }

    /// Create a builder for an assistant message
    pub fn assistant() -> Self {
        Self::new(super::string_pool::roles::ASSISTANT)
    }

    /// Create a builder for a system message
    pub fn system() -> Self {
        Self::new(super::string_pool::roles::SYSTEM)
    }

    /// Create a builder for a tool message
    pub fn tool() -> Self {
        Self::new(super::string_pool::roles::TOOL)
    }

    /// Set the content as text
    pub fn text(mut self, content: impl Into<String>) -> Self {
        self.content = serde_json::Value::String(content.into());
        self
    }

    /// Set the content as a JSON value
    pub fn content(mut self, content: serde_json::Value) -> Self {
        self.content = content;
        self
    }

    /// Pre-allocate metadata capacity (optimization for known metadata count)
    pub fn with_metadata_capacity(mut self, capacity: usize) -> Self {
        self.metadata_capacity = capacity;
        self.metadata.reserve(capacity);
        self
    }

    /// Add metadata
    pub fn metadata(mut self, key: impl Into<String>, value: serde_json::Value) -> Self {
        self.metadata.insert(key.into(), value);
        self
    }

    /// Build the message
    pub fn build(self) -> Message {
        let mut msg = Message::new(self.role, self.content);
        msg.metadata = self.metadata;
        msg
    }
}

/// Fast path for creating common message patterns with minimal allocations
pub mod fast {
    use super::*;
    use crate::optimizations::string_pool::roles;

    /// Create a user message with text content (zero-copy role)
    #[inline]
    pub fn user_text(content: impl Into<String>) -> Message {
        Message::new(roles::USER, serde_json::Value::String(content.into()))
    }

    /// Create an assistant message with text content (zero-copy role)
    #[inline]
    pub fn assistant_text(content: impl Into<String>) -> Message {
        Message::new(roles::ASSISTANT, serde_json::Value::String(content.into()))
    }

    /// Create a system message with text content (zero-copy role)
    #[inline]
    pub fn system_text(content: impl Into<String>) -> Message {
        Message::new(roles::SYSTEM, serde_json::Value::String(content.into()))
    }

    /// Create a tool message with text content (zero-copy role)
    #[inline]
    pub fn tool_text(content: impl Into<String>) -> Message {
        Message::new(roles::TOOL, serde_json::Value::String(content.into()))
    }

    /// Create a message with pre-allocated metadata capacity
    #[inline]
    pub fn with_metadata(
        role: &str,
        content: impl Into<String>,
        metadata_count: usize,
    ) -> MessageBuilder {
        MessageBuilder::new(role)
            .text(content)
            .with_metadata_capacity(metadata_count)
    }
}

/// Batch message creation with pre-allocated vectors
pub struct MessageBatch {
    messages: Vec<Message>,
}

impl MessageBatch {
    /// Create a new batch with pre-allocated capacity
    pub fn with_capacity(capacity: usize) -> Self {
        Self {
            messages: Vec::with_capacity(capacity),
        }
    }

    /// Add a message to the batch
    pub fn push(&mut self, message: Message) {
        self.messages.push(message);
    }

    /// Add a user message
    pub fn push_user(&mut self, content: impl Into<String>) {
        self.messages.push(fast::user_text(content));
    }

    /// Add an assistant message
    pub fn push_assistant(&mut self, content: impl Into<String>) {
        self.messages.push(fast::assistant_text(content));
    }

    /// Add a system message
    pub fn push_system(&mut self, content: impl Into<String>) {
        self.messages.push(fast::system_text(content));
    }

    /// Get the messages
    pub fn into_messages(self) -> Vec<Message> {
        self.messages
    }

    /// Get a reference to the messages
    pub fn messages(&self) -> &[Message] {
        &self.messages
    }

    /// Get the number of messages
    pub fn len(&self) -> usize {
        self.messages.len()
    }

    /// Check if the batch is empty
    pub fn is_empty(&self) -> bool {
        self.messages.is_empty()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_message_builder_basic() {
        let msg = MessageBuilder::user().text("Hello").build();

        assert_eq!(msg.role, "user");
        assert_eq!(msg.content_as_str().unwrap(), "Hello");
    }

    #[test]
    fn test_message_builder_with_metadata() {
        let msg = MessageBuilder::assistant()
            .text("Response")
            .metadata("model", serde_json::json!("gpt-4"))
            .metadata("temperature", serde_json::json!(0.7))
            .build();

        assert_eq!(msg.role, "assistant");
        assert_eq!(msg.metadata.len(), 2);
    }

    #[test]
    fn test_message_builder_capacity() {
        let msg = MessageBuilder::system()
            .text("Instructions")
            .with_metadata_capacity(5)
            .metadata("key1", serde_json::json!("value1"))
            .build();

        // Capacity should be respected (not directly testable, but won't panic)
        assert_eq!(msg.role, "system");
    }

    #[test]
    fn test_fast_user_text() {
        let msg = fast::user_text("Hello");
        assert_eq!(msg.role, "user");
        assert_eq!(msg.content_as_str().unwrap(), "Hello");
    }

    #[test]
    fn test_fast_assistant_text() {
        let msg = fast::assistant_text("Response");
        assert_eq!(msg.role, "assistant");
        assert_eq!(msg.content_as_str().unwrap(), "Response");
    }

    #[test]
    fn test_fast_with_metadata() {
        let builder = fast::with_metadata("user", "Hello", 2);
        let msg = builder
            .metadata("key1", serde_json::json!("value1"))
            .metadata("key2", serde_json::json!("value2"))
            .build();

        assert_eq!(msg.metadata.len(), 2);
    }

    #[test]
    fn test_message_batch() {
        let mut batch = MessageBatch::with_capacity(3);

        batch.push_user("User message");
        batch.push_assistant("Assistant response");
        batch.push_system("System instruction");

        assert_eq!(batch.len(), 3);
        assert!(!batch.is_empty());

        let messages = batch.into_messages();
        assert_eq!(messages.len(), 3);
        assert_eq!(messages[0].role, "user");
        assert_eq!(messages[1].role, "assistant");
        assert_eq!(messages[2].role, "system");
    }

    #[test]
    fn test_message_batch_empty() {
        let batch = MessageBatch::with_capacity(0);
        assert!(batch.is_empty());
        assert_eq!(batch.len(), 0);
    }
}
