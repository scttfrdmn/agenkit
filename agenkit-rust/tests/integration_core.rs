//! Integration tests for core functionality
//!
//! Tests message creation and serialization, agent interface compliance,
//! result type handling, error propagation, and metadata handling.

use agenkit::core::{Agent, AgentError, Message};
use async_trait::async_trait;
use serde_json::json;
use std::collections::HashMap;

/// Simple echo agent for testing
struct SimpleEchoAgent;

#[async_trait]
impl Agent for SimpleEchoAgent {
    fn name(&self) -> &str {
        "simple-echo"
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let content = message.content_as_str().unwrap_or("");
        let response = Message::with_text("assistant", format!("Echo: {}", content))
            .with_metadata("original", json!(content))
            .with_metadata("language", json!("rust"))
            .with_metadata("agent", json!(self.name()));
        Ok(response)
    }

    fn capabilities(&self) -> Vec<String> {
        vec!["echo".to_string()]
    }
}

/// Test 1: Message creation and basic properties
#[tokio::test]
async fn test_message_creation() {
    let msg = Message::with_text("user", "Hello");
    let msg = msg.with_metadata("test", json!(true));

    assert_eq!(msg.role, "user");
    assert_eq!(msg.content_as_str().unwrap(), "Hello");
    assert_eq!(msg.metadata.get("test").unwrap().as_bool().unwrap(), true);
    assert!(!msg.timestamp.to_rfc3339().is_empty());
}

/// Test 2: Message serialization and deserialization
///
/// The 3.14 below is hand-mirrored across cores: Go's
/// `TestMessageSerialization` (agenkit-go/tests/integration/basic_integration_test.go)
/// and Python's `test_message_serialization` (tests/integration/test_basic_integration.py)
/// build the identical metadata map. Taking clippy's suggestion and substituting
/// `std::f64::consts::PI` would silently break that correspondence for the sake
/// of a lint — the value is a shared test vector, not an approximation of pi.
#[allow(clippy::approx_constant)]
#[tokio::test]
async fn test_message_serialization() {
    let mut metadata = HashMap::new();
    metadata.insert("string".to_string(), json!("value"));
    metadata.insert("number".to_string(), json!(42));
    metadata.insert("float".to_string(), json!(3.14));
    metadata.insert("bool".to_string(), json!(true));
    metadata.insert("nested".to_string(), json!({"key": "value"}));
    metadata.insert("list".to_string(), json!([1, 2, 3]));

    let original = Message {
        role: "user".to_string(),
        content: json!("Test message"),
        metadata: metadata.clone(),
        timestamp: chrono::Utc::now(),
    };

    // Serialize to JSON
    let json_str = serde_json::to_string(&original).expect("Failed to serialize");
    assert!(!json_str.is_empty());

    // Deserialize
    let deserialized: Message = serde_json::from_str(&json_str).expect("Failed to deserialize");

    assert_eq!(deserialized.role, "user");
    assert_eq!(deserialized.content_as_str().unwrap(), "Test message");
    assert_eq!(
        deserialized
            .metadata
            .get("string")
            .unwrap()
            .as_str()
            .unwrap(),
        "value"
    );
    assert_eq!(
        deserialized
            .metadata
            .get("number")
            .unwrap()
            .as_i64()
            .unwrap(),
        42
    );
    assert!(
        (deserialized
            .metadata
            .get("float")
            .unwrap()
            .as_f64()
            .unwrap()
            - 3.14)
            .abs()
            < 0.01
    );
    assert_eq!(
        deserialized
            .metadata
            .get("bool")
            .unwrap()
            .as_bool()
            .unwrap(),
        true
    );
}

/// Test 3: Agent basic processing
#[tokio::test]
async fn test_agent_basic_processing() {
    let agent = SimpleEchoAgent;

    assert_eq!(agent.name(), "simple-echo");
    assert!(!agent.capabilities().is_empty());
    assert!(agent.capabilities().contains(&"echo".to_string()));

    let msg = Message::with_text("user", "Hello");
    let response = agent.process(msg).await.expect("Process failed");

    assert_eq!(response.role, "assistant");
    assert_eq!(response.content_as_str().unwrap(), "Echo: Hello");
    assert_eq!(
        response.metadata.get("original").unwrap().as_str().unwrap(),
        "Hello"
    );
    assert_eq!(
        response.metadata.get("language").unwrap().as_str().unwrap(),
        "rust"
    );
}

/// Test 4: Agent metadata preservation
#[tokio::test]
async fn test_agent_metadata_preservation() {
    let agent = SimpleEchoAgent;

    let msg = Message::with_text("user", "Test").with_metadata("request_id", json!("123"));

    let response = agent.process(msg).await.expect("Process failed");

    // Agent adds its own metadata
    assert_eq!(
        response.metadata.get("original").unwrap().as_str().unwrap(),
        "Test"
    );
    assert_eq!(
        response.metadata.get("language").unwrap().as_str().unwrap(),
        "rust"
    );
    assert_eq!(
        response.metadata.get("agent").unwrap().as_str().unwrap(),
        "simple-echo"
    );
}

/// Test 5: Multiple sequential requests
#[tokio::test]
async fn test_multiple_sequential_requests() {
    let agent = SimpleEchoAgent;

    for i in 0..5 {
        let msg = Message::with_text("user", format!("Message {}", i));
        let response = agent.process(msg).await.expect("Process failed");

        assert_eq!(
            response.content_as_str().unwrap(),
            format!("Echo: Message {}", i)
        );
        assert_eq!(
            response.metadata.get("original").unwrap().as_str().unwrap(),
            format!("Message {}", i).as_str()
        );
    }
}

/// Test 6: Agent with complex metadata
#[tokio::test]
async fn test_agent_with_complex_metadata() {
    let agent = SimpleEchoAgent;

    let complex_metadata = json!({
        "trace_id": "abc-123",
        "user": {
            "id": 42,
            "name": "Test User",
            "preferences": {
                "language": "en",
                "timezone": "UTC"
            }
        },
        "tags": ["test", "integration", "metadata"],
        "counts": [1, 2, 3, 4, 5]
    });

    let msg = Message::with_text("user", "Complex test").with_metadata("context", complex_metadata);

    let response = agent.process(msg).await.expect("Process failed");

    assert_eq!(
        response.metadata.get("original").unwrap().as_str().unwrap(),
        "Complex test"
    );
    assert_eq!(
        response.metadata.get("language").unwrap().as_str().unwrap(),
        "rust"
    );
}

/// Test 7: Message immutability
#[tokio::test]
async fn test_message_immutability() {
    let agent = SimpleEchoAgent;

    let original_content = "Original message";
    let msg = Message::with_text("user", original_content);
    let msg_content = msg.content_as_str().unwrap().to_string();

    // Process message
    let _ = agent.process(msg.clone()).await;

    // Original message should be unchanged
    assert_eq!(msg.content_as_str().unwrap(), msg_content);
}

/// Test 8: Agent consistency
#[tokio::test]
async fn test_agent_consistency() {
    let agent = SimpleEchoAgent;
    let msg = Message::with_text("user", "Consistency test");

    let mut results = Vec::new();
    for _ in 0..3 {
        let response = agent.process(msg.clone()).await.expect("Process failed");
        results.push(response.content_as_str().unwrap().to_string());
    }

    // All results should be identical
    assert_eq!(results[0], results[1]);
    assert_eq!(results[1], results[2]);
    assert_eq!(results[0], "Echo: Consistency test");
}

/// Test 9: Empty content handling
#[tokio::test]
async fn test_empty_content_handling() {
    let agent = SimpleEchoAgent;
    let msg = Message::with_text("user", "");
    let response = agent.process(msg).await.expect("Process failed");

    assert_eq!(response.role, "assistant");
    assert_eq!(response.content_as_str().unwrap(), "Echo: ");
    assert_eq!(
        response.metadata.get("original").unwrap().as_str().unwrap(),
        ""
    );
}

/// Test 10: Unicode content handling
#[tokio::test]
async fn test_unicode_content_handling() {
    let agent = SimpleEchoAgent;
    let unicode_content = "Hello 世界 🌍 Привет";
    let msg = Message::with_text("user", unicode_content);
    let response = agent.process(msg).await.expect("Process failed");

    let expected = format!("Echo: {}", unicode_content);
    assert_eq!(response.content_as_str().unwrap(), expected);
    assert_eq!(
        response.metadata.get("original").unwrap().as_str().unwrap(),
        unicode_content
    );
}

/// Test 11: Message with various JSON content types
#[tokio::test]
async fn test_message_json_content_types() {
    // String content
    let msg_str = Message::new("user", json!("string content"));
    assert_eq!(msg_str.content_as_str().unwrap(), "string content");

    // Numeric content
    let msg_num = Message::new("user", json!(42));
    assert_eq!(msg_num.content.as_i64().unwrap(), 42);

    // Object content
    let msg_obj = Message::new("user", json!({"key": "value"}));
    assert_eq!(
        msg_obj.content.get("key").unwrap().as_str().unwrap(),
        "value"
    );

    // Array content
    let msg_arr = Message::new("user", json!([1, 2, 3]));
    assert_eq!(msg_arr.content.as_array().unwrap().len(), 3);
}

/// Test 12: Error handling in agent processing
#[tokio::test]
async fn test_agent_error_handling() {
    struct ErrorAgent;

    #[async_trait]
    impl Agent for ErrorAgent {
        fn name(&self) -> &str {
            "error-agent"
        }

        async fn process(&self, _message: Message) -> Result<Message, AgentError> {
            Err(AgentError::ProcessingError(
                "Intentional error for testing".to_string(),
            ))
        }
    }

    let agent = ErrorAgent;
    let msg = Message::with_text("user", "test");
    let result = agent.process(msg).await;

    assert!(result.is_err());
    match result {
        Err(AgentError::ProcessingError(msg)) => {
            assert!(msg.contains("Intentional error"))
        }
        _ => panic!("Expected ProcessingError"),
    }
}
