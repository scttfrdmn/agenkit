//! Agent invariant tests
//!
//! Cross-cutting tests that verify invariants applying to all agents:
//! message properties, agent lifecycle, tool call/result handling,
//! and error propagation.

use agenkit::core::{Agent, AgentError, Message, Tool, ToolResult};
use async_trait::async_trait;
use serde_json::json;
use std::collections::HashMap;
use std::sync::Arc;

// ─────────────────────────────────────────────────────────────────────────────
// Test agents
// ─────────────────────────────────────────────────────────────────────────────

struct EchoAgent {
    name: String,
}

#[async_trait]
impl Agent for EchoAgent {
    fn name(&self) -> &str {
        &self.name
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        // Preserve metadata in response
        let mut response = Message::with_text(
            "assistant",
            format!("echo:{}", message.content_as_str().unwrap_or("")),
        );
        for (k, v) in &message.metadata {
            response = response.with_metadata(k.clone(), v.clone());
        }
        Ok(response)
    }

    fn capabilities(&self) -> Vec<String> {
        vec!["echo".to_string(), "respond".to_string()]
    }
}

struct NamedAgent {
    agent_name: String,
}

#[async_trait]
impl Agent for NamedAgent {
    fn name(&self) -> &str {
        &self.agent_name
    }

    async fn process(&self, _message: Message) -> Result<Message, AgentError> {
        Ok(Message::with_text("assistant", "response"))
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Message invariant tests
// ─────────────────────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_message_role_preserved_through_agent() {
    let agent = EchoAgent { name: "echo".to_string() };
    let msg = Message::with_text("user", "hello");
    assert_eq!(msg.role, "user");
    let resp = agent.process(msg).await.unwrap();
    assert_eq!(resp.role, "assistant");
}

#[tokio::test]
async fn test_message_content_preserved() {
    let msg = Message::with_text("user", "exact content");
    assert_eq!(msg.content_as_str().unwrap(), "exact content");
}

#[tokio::test]
async fn test_message_metadata_round_trip() {
    let msg = Message::with_text("user", "test")
        .with_metadata("key1", json!("value1"))
        .with_metadata("key2", json!(42))
        .with_metadata("key3", json!(true));
    assert_eq!(msg.metadata.get("key1").unwrap().as_str().unwrap(), "value1");
    assert_eq!(msg.metadata.get("key2").unwrap().as_i64().unwrap(), 42);
    assert!(msg.metadata.get("key3").unwrap().as_bool().unwrap());
}

#[tokio::test]
async fn test_message_with_metadata_immutability() {
    let original = Message::with_text("user", "base");
    let with_meta = original.clone().with_metadata("added", json!("yes"));
    // Original should not have the metadata (with_metadata takes self by value)
    assert!(!original.metadata.contains_key("added"));
    assert!(with_meta.metadata.contains_key("added"));
}

#[tokio::test]
async fn test_message_content_as_str_string_content() {
    let msg = Message::with_text("user", "hello world");
    assert_eq!(msg.content_as_str().unwrap(), "hello world");
}

#[tokio::test]
async fn test_message_content_as_str_non_string_returns_none() {
    let msg = Message::new("user", json!({"complex": "object"}));
    // Non-string content should return None from content_as_str
    assert!(msg.content_as_str().is_none());
}

#[tokio::test]
async fn test_message_json_round_trip() {
    let msg = Message::with_text("user", "serializable message")
        .with_metadata("id", json!("msg-123"));
    let json_str = serde_json::to_string(&msg).unwrap();
    let restored: Message = serde_json::from_str(&json_str).unwrap();
    assert_eq!(restored.role, msg.role);
    assert_eq!(restored.content, msg.content);
    assert_eq!(
        restored.metadata.get("id").unwrap(),
        msg.metadata.get("id").unwrap()
    );
}

#[tokio::test]
async fn test_message_large_content() {
    let large = "x".repeat(10_000);
    let msg = Message::with_text("user", large.as_str());
    assert_eq!(msg.content_as_str().unwrap().len(), 10_000);
}

#[tokio::test]
async fn test_message_empty_content() {
    let msg = Message::with_text("user", "");
    assert_eq!(msg.content_as_str().unwrap(), "");
}

#[tokio::test]
async fn test_message_unicode_content() {
    let unicode = "こんにちは 你好 مرحبا 🌍";
    let msg = Message::with_text("user", unicode);
    assert_eq!(msg.content_as_str().unwrap(), unicode);
}

// ─────────────────────────────────────────────────────────────────────────────
// Agent lifecycle tests
// ─────────────────────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_agent_name_stable_across_calls() {
    let agent = EchoAgent { name: "stable-name".to_string() };
    for _ in 0..10 {
        assert_eq!(agent.name(), "stable-name");
    }
}

#[tokio::test]
async fn test_agent_process_multiple_times() {
    let agent = EchoAgent { name: "multi".to_string() };
    for i in 0..5 {
        let msg = Message::with_text("user", format!("msg {}", i));
        let result = agent.process(msg).await;
        assert!(result.is_ok());
    }
}

#[tokio::test]
async fn test_agent_capabilities_non_empty() {
    let agent = EchoAgent { name: "capable".to_string() };
    assert!(!agent.capabilities().is_empty());
}

#[tokio::test]
async fn test_agent_introspect_returns_result() {
    let agent = EchoAgent { name: "introspectable".to_string() };
    let result = agent.introspect();
    // introspect() should return a valid IntrospectionResult
    assert!(!result.agent_name.is_empty());
}

#[tokio::test]
async fn test_agent_concurrent_process_safe() {
    let agent = Arc::new(EchoAgent { name: "concurrent".to_string() });
    let handles: Vec<_> = (0..10)
        .map(|i| {
            let a = Arc::clone(&agent);
            tokio::spawn(async move {
                a.process(Message::with_text("user", format!("msg {}", i))).await
            })
        })
        .collect();
    for handle in handles {
        assert!(handle.await.unwrap().is_ok());
    }
}

#[tokio::test]
async fn test_agent_process_after_error() {
    // An error from one process() call should not prevent future calls
    struct FlakyAgent {
        fail_first: std::sync::atomic::AtomicBool,
    }
    #[async_trait]
    impl Agent for FlakyAgent {
        fn name(&self) -> &str { "flaky" }
        async fn process(&self, msg: Message) -> Result<Message, AgentError> {
            if self.fail_first.swap(false, std::sync::atomic::Ordering::SeqCst) {
                Err(AgentError::ProcessingError("first call fails".to_string()))
            } else {
                Ok(Message::with_text("assistant", "ok"))
            }
        }
    }
    let agent = FlakyAgent {
        fail_first: std::sync::atomic::AtomicBool::new(true),
    };
    let first = agent.process(Message::with_text("user", "1")).await;
    let second = agent.process(Message::with_text("user", "2")).await;
    assert!(first.is_err());
    assert!(second.is_ok());
}

#[tokio::test]
async fn test_agent_name_uniqueness_not_required() {
    // Two agents can have the same name — no uniqueness constraint
    let a1 = EchoAgent { name: "duplicate".to_string() };
    let a2 = EchoAgent { name: "duplicate".to_string() };
    assert_eq!(a1.name(), a2.name());
}

#[tokio::test]
async fn test_agent_empty_message_processed() {
    let agent = EchoAgent { name: "echo".to_string() };
    let result = agent.process(Message::with_text("user", "")).await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn test_agent_metadata_only_message() {
    let agent = EchoAgent { name: "echo".to_string() };
    let msg = Message::with_text("user", "")
        .with_metadata("action", json!("process"))
        .with_metadata("version", json!("1.0"));
    let result = agent.process(msg).await;
    assert!(result.is_ok());
}

// ─────────────────────────────────────────────────────────────────────────────
// Tool call / result tests
// ─────────────────────────────────────────────────────────────────────────────

struct EchoTool;

#[async_trait]
impl Tool for EchoTool {
    fn name(&self) -> &str {
        "echo_tool"
    }

    fn description(&self) -> &str {
        "Echoes the input back"
    }

    async fn execute(
        &self,
        params: HashMap<String, serde_json::Value>,
    ) -> Result<ToolResult, AgentError> {
        let input = params.get("input").cloned().unwrap_or(json!(""));
        Ok(ToolResult::success(input))
    }
}

struct FailingTool;

#[async_trait]
impl Tool for FailingTool {
    fn name(&self) -> &str {
        "failing_tool"
    }

    fn description(&self) -> &str {
        "Always fails"
    }

    async fn execute(
        &self,
        _params: HashMap<String, serde_json::Value>,
    ) -> Result<ToolResult, AgentError> {
        Err(AgentError::ProcessingError("tool execution failed".to_string()))
    }
}

#[tokio::test]
async fn test_tool_result_success_constructed() {
    let result = ToolResult::success(json!("output value"));
    assert!(result.success);
    assert!(result.error.is_none());
    assert_eq!(result.output, json!("output value"));
}

#[tokio::test]
async fn test_tool_result_error_constructed() {
    let result = ToolResult::error("something went wrong");
    assert!(!result.success);
    assert!(result.error.is_some());
    assert_eq!(result.error.unwrap(), "something went wrong");
}

#[tokio::test]
async fn test_tool_name_accessible() {
    let tool = EchoTool;
    assert_eq!(tool.name(), "echo_tool");
}

#[tokio::test]
async fn test_tool_description_accessible() {
    let tool = EchoTool;
    assert!(!tool.description().is_empty());
}

#[tokio::test]
async fn test_tool_execute_success() {
    let tool = EchoTool;
    let mut params = HashMap::new();
    params.insert("input".to_string(), json!("hello"));
    let result = tool.execute(params).await.unwrap();
    assert!(result.success);
    assert_eq!(result.output, json!("hello"));
}

#[tokio::test]
async fn test_tool_execute_failure_returns_error() {
    let tool = FailingTool;
    let result = tool.execute(HashMap::new()).await;
    assert!(result.is_err());
}

#[tokio::test]
async fn test_tool_result_with_metadata() {
    let result = ToolResult::success(json!("out"))
        .with_metadata("source", json!("database"))
        .with_metadata("count", json!(42));
    assert_eq!(result.metadata.get("source").unwrap(), &json!("database"));
    assert_eq!(result.metadata.get("count").unwrap(), &json!(42));
}

#[tokio::test]
async fn test_tool_execute_complex_args() {
    let tool = EchoTool;
    let mut params = HashMap::new();
    params.insert(
        "input".to_string(),
        json!({
            "nested": {
                "key": "value",
                "list": [1, 2, 3]
            }
        }),
    );
    let result = tool.execute(params).await.unwrap();
    assert!(result.success);
    assert_eq!(result.output["nested"]["key"], json!("value"));
}

// ─────────────────────────────────────────────────────────────────────────────
// Error propagation tests
// ─────────────────────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_agent_error_timeout_variant() {
    let err = AgentError::Timeout("operation timed out".to_string());
    let msg = format!("{}", err);
    assert!(!msg.is_empty());
}

#[tokio::test]
async fn test_agent_error_internal_variant() {
    let err = AgentError::Internal("internal error".to_string());
    let msg = format!("{}", err);
    assert!(!msg.is_empty());
}

#[tokio::test]
async fn test_agent_error_invalid_input_variant() {
    let err = AgentError::InvalidInput("bad input".to_string());
    let msg = format!("{}", err);
    assert!(!msg.is_empty());
}

#[tokio::test]
async fn test_agent_error_processing_error_variant() {
    let err = AgentError::ProcessingError("processing failed".to_string());
    let msg = format!("{}", err);
    assert!(!msg.is_empty());
}

#[tokio::test]
async fn test_agent_error_display_non_empty() {
    let errors = vec![
        AgentError::Timeout("t".to_string()),
        AgentError::Internal("i".to_string()),
        AgentError::InvalidInput("ii".to_string()),
        AgentError::ProcessingError("pe".to_string()),
        AgentError::ConfigurationError("ce".to_string()),
        AgentError::NotFound("nf".to_string()),
    ];
    for err in errors {
        assert!(!format!("{}", err).is_empty());
    }
}

#[tokio::test]
async fn test_agent_error_propagates_through_process() {
    struct PropagatingAgent {
        inner_error: AgentError,
    }
    // Can't easily clone AgentError, so use a string to create it
    struct ErrorPropagator;
    #[async_trait]
    impl Agent for ErrorPropagator {
        fn name(&self) -> &str { "propagator" }
        async fn process(&self, _msg: Message) -> Result<Message, AgentError> {
            Err(AgentError::Internal("downstream error preserved".to_string()))
        }
    }
    let agent = ErrorPropagator;
    let err = agent.process(Message::with_text("user", "test")).await.unwrap_err();
    let msg = format!("{}", err);
    assert!(msg.contains("downstream"), "error message: {}", msg);
}

#[tokio::test]
async fn test_agent_error_not_found_variant() {
    let err = AgentError::NotFound("agent not found".to_string());
    let msg = format!("{}", err);
    assert!(msg.len() > 0);
}
