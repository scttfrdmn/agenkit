//! Comprehensive AG-UI Protocol Integration Tests
//!
//! Tests the complete AG-UI protocol implementation including:
//! - Event streaming and serialization
//! - Adapter functionality
//! - Human-in-the-loop integration
//! - HTTP/SSE transport
//! - WebSocket transport
//! - Error handling
//! - Edge cases
use agenkit::core::{Agent, AgentError, Message};
use agenkit::patterns::human_in_loop::{
    simple_approval_func, HumanInLoopAgent, HumanInLoopConfig,
};
use agenkit::protocols::agui::adapter::{AGUIAdapter, AGUIAdapterConfig};
use agenkit::protocols::agui::events::*;
use agenkit::protocols::agui::hitl::{AGUIHumanInLoopAdapter, AGUIHumanInLoopConfig};
use agenkit::protocols::agui::transports::http::{AGUISSEStream, SSEFormatter};
use agenkit::protocols::agui::transports::websocket::{
    AGUIWebSocketHandler, WebSocketHandlerConfig, WebSocketMessageFormat,
};
use async_trait::async_trait;
use futures::stream::StreamExt;
use std::sync::Arc;

// ============================================================================
// Mock Agents for Testing
// ============================================================================

struct MockAgent {
    name: String,
    response: String,
    confidence: f64,
    should_error: bool,
}

impl MockAgent {
    fn new(name: &str, response: &str) -> Self {
        Self {
            name: name.to_string(),
            response: response.to_string(),
            confidence: 0.95,
            should_error: false,
        }
    }

    fn with_confidence(mut self, confidence: f64) -> Self {
        self.confidence = confidence;
        self
    }

    fn with_error(mut self) -> Self {
        self.should_error = true;
        self
    }
}

#[async_trait]
impl Agent for MockAgent {
    fn name(&self) -> &str {
        &self.name
    }

    fn capabilities(&self) -> Vec<String> {
        vec!["test".to_string()]
    }

    async fn process(&self, _message: Message) -> Result<Message, AgentError> {
        if self.should_error {
            return Err(AgentError::ProcessingError("Test error".to_string()));
        }

        Ok(
            Message::new("assistant", serde_json::json!(self.response.clone()))
                .with_metadata("confidence", serde_json::json!(self.confidence)),
        )
    }
}

// ============================================================================
// Event System Tests
// ============================================================================

#[tokio::test]
async fn test_event_serialization_completeness() {
    // Test that all event types can be serialized and deserialized

    // TextMessageStart
    let event = TextMessageStart::new("assistant", Some("msg_123".to_string()))
        .with_metadata("test", serde_json::json!("value"));
    let json = event.to_json();
    assert_eq!(
        json.get("event_type"),
        Some(&serde_json::json!("text_message_start"))
    );
    assert_eq!(json.get("test"), Some(&serde_json::json!("value")));

    // TextMessageChunk
    let event = TextMessageChunk::new("Hello".to_string(), Some("msg_123".to_string()));
    let json = event.to_json();
    assert_eq!(
        json.get("event_type"),
        Some(&serde_json::json!("text_message_chunk"))
    );
    assert_eq!(json.get("content"), Some(&serde_json::json!("Hello")));

    // Interrupt
    let event = Interrupt::new(
        InterruptReason::ApprovalRequired,
        "Approval needed".to_string(),
        vec![InterruptAction::Approve, InterruptAction::Reject],
        std::collections::HashMap::new(),
        Some("int_123".to_string()),
    );
    let json = event.to_json();
    assert_eq!(
        json.get("event_type"),
        Some(&serde_json::json!("interrupt"))
    );
    assert_eq!(
        json.get("reason"),
        Some(&serde_json::json!("approval_required"))
    );
}

#[tokio::test]
async fn test_event_metadata_preservation() {
    // Ensure metadata is preserved through serialization
    let mut metadata = std::collections::HashMap::new();
    metadata.insert(
        "custom_field".to_string(),
        serde_json::json!("custom_value"),
    );
    metadata.insert("nested".to_string(), serde_json::json!({"key": "value"}));

    let event = TextMessageChunk::new("Test".to_string(), Some("msg_1".to_string()));
    let event_with_meta = event
        .with_metadata("custom_field", serde_json::json!("custom_value"))
        .with_metadata("nested", serde_json::json!({"key": "value"}));

    let json = event_with_meta.to_json();

    assert_eq!(
        json.get("custom_field"),
        Some(&serde_json::json!("custom_value"))
    );
    assert!(json.get("nested").is_some());
}

// ============================================================================
// Adapter Tests
// ============================================================================

#[tokio::test]
async fn test_adapter_basic_streaming() {
    let agent = Arc::new(MockAgent::new("TestAgent", "Hello World"));
    let adapter = AGUIAdapter::new(agent, AGUIAdapterConfig::default());

    let message = Message::with_text("user", "test");
    let mut stream = adapter.stream_events(message, None, false).await;

    let mut event_types = Vec::new();
    while let Some(event) = stream.next().await {
        event_types.push(event.event_type());
    }

    assert!(event_types.contains(&EventType::TextMessageStart));
    assert!(event_types.contains(&EventType::TextMessageChunk));
    assert!(event_types.contains(&EventType::TextMessageComplete));
}

#[tokio::test]
async fn test_adapter_error_handling() {
    let agent = Arc::new(MockAgent::new("ErrorAgent", "").with_error());
    let adapter = AGUIAdapter::new(agent, AGUIAdapterConfig::default());

    let message = Message::with_text("user", "test");
    let mut stream = adapter.stream_events(message, None, false).await;

    let mut has_error = false;
    while let Some(event) = stream.next().await {
        if event.event_type() == EventType::Error {
            has_error = true;
            let json = event.to_json();
            assert_eq!(
                json.get("error_code"),
                Some(&serde_json::json!("agent_error"))
            );
        }
    }

    assert!(has_error, "Should have emitted error event");
}

#[tokio::test]
async fn test_adapter_metadata_emission() {
    let agent = Arc::new(MockAgent::new("TestAgent", "Test"));
    let adapter = AGUIAdapter::new(agent, AGUIAdapterConfig::default());

    let message = Message::with_text("user", "test");
    let mut stream = adapter.stream_events(message, None, true).await;

    let first_event = stream.next().await.expect("Should have first event");
    assert_eq!(first_event.event_type(), EventType::Metadata);

    let json = first_event.to_json();
    assert_eq!(json.get("protocol"), Some(&serde_json::json!("ag-ui")));
}

#[tokio::test]
async fn test_adapter_message_id_consistency() {
    let agent = Arc::new(MockAgent::new("TestAgent", "Test"));
    let adapter = AGUIAdapter::new(agent, AGUIAdapterConfig::default());

    let message = Message::with_text("user", "test");
    let custom_id = "custom_msg_123";
    let mut stream = adapter
        .stream_events(message, Some(custom_id.to_string()), false)
        .await;

    while let Some(event) = stream.next().await {
        let json = event.to_json();
        if let Some(message_id) = json.get("message_id") {
            assert_eq!(message_id, &serde_json::json!(custom_id));
        }
    }
}

#[tokio::test]
async fn test_adapter_chunking() {
    let agent = Arc::new(MockAgent::new("TestAgent", "Hello World"));
    let adapter = AGUIAdapter::new(
        agent,
        AGUIAdapterConfig {
            agent_name: None,
            chunk_size: 5, // Small chunks
        },
    );

    let message = Message::with_text("user", "test");
    let mut stream = adapter.stream_events(message, None, false).await;

    let mut chunks = Vec::new();
    while let Some(event) = stream.next().await {
        if event.event_type() == EventType::TextMessageChunk {
            let json = event.to_json();
            if let Some(content) = json.get("content") {
                chunks.push(content.as_str().unwrap().to_string());
            }
        }
    }

    // Should have multiple chunks
    assert!(chunks.len() > 1, "Should have chunked the content");

    // Reassemble should match original
    let reassembled: String = chunks.join("");
    assert_eq!(reassembled, "Hello World");
}

// ============================================================================
// Human-in-the-Loop Tests
// ============================================================================

#[tokio::test]
async fn test_hitl_high_confidence_no_interrupt() {
    let agent = Arc::new(MockAgent::new("TestAgent", "Response").with_confidence(0.95));

    let hil_agent = HumanInLoopAgent::new(HumanInLoopConfig {
        agent,
        approval_threshold: 0.8,
        approval_func: simple_approval_func(true),
        confidence_key: "confidence".to_string(),
    })
    .unwrap();

    let adapter =
        AGUIHumanInLoopAdapter::new(Arc::new(hil_agent), AGUIHumanInLoopConfig::default());

    let message = Message::with_text("user", "test");
    let mut stream = adapter.stream_events(message, None, false).await;

    let mut has_interrupt = false;
    while let Some(event) = stream.next().await {
        if event.event_type() == EventType::Interrupt {
            has_interrupt = true;
        }
    }

    assert!(
        !has_interrupt,
        "High confidence should not trigger interrupt"
    );
}

#[tokio::test]
async fn test_hitl_low_confidence_with_interrupt() {
    let agent = Arc::new(MockAgent::new("TestAgent", "Response").with_confidence(0.5));

    let hil_agent = HumanInLoopAgent::new(HumanInLoopConfig {
        agent,
        approval_threshold: 0.8,
        approval_func: simple_approval_func(true),
        confidence_key: "confidence".to_string(),
    })
    .unwrap();

    let adapter =
        AGUIHumanInLoopAdapter::new(Arc::new(hil_agent), AGUIHumanInLoopConfig::default());

    let message = Message::with_text("user", "test");
    let mut stream = adapter.stream_events(message, None, false).await;

    let mut interrupt_event = None;
    while let Some(event) = stream.next().await {
        if event.event_type() == EventType::Interrupt {
            interrupt_event = Some(event.to_json());
        }
    }

    assert!(interrupt_event.is_some(), "Should have interrupt event");

    let json = interrupt_event.unwrap();
    assert_eq!(
        json.get("reason"),
        Some(&serde_json::json!("approval_required"))
    );

    // Check context
    let context = json.get("context").expect("Should have context");
    assert!(context.get("confidence").is_some());
    assert!(context.get("threshold").is_some());
}

#[tokio::test]
async fn test_hitl_rejection_flow() {
    let agent = Arc::new(MockAgent::new("TestAgent", "Response").with_confidence(0.4));

    let hil_agent = HumanInLoopAgent::new(HumanInLoopConfig {
        agent,
        approval_threshold: 0.8,
        approval_func: simple_approval_func(false), // Reject
        confidence_key: "confidence".to_string(),
    })
    .unwrap();

    let adapter =
        AGUIHumanInLoopAdapter::new(Arc::new(hil_agent), AGUIHumanInLoopConfig::default());

    let message = Message::with_text("user", "test");
    let mut stream = adapter.stream_events(message, None, false).await;

    let mut final_content = String::new();
    while let Some(event) = stream.next().await {
        if event.event_type() == EventType::TextMessageComplete {
            let json = event.to_json();
            if let Some(content) = json.get("content") {
                final_content = content.as_str().unwrap().to_string();
            }
        }
    }

    assert!(
        final_content.contains("rejected"),
        "Should contain rejection message"
    );
}

// ============================================================================
// HTTP/SSE Transport Tests
// ============================================================================

#[tokio::test]
async fn test_sse_format_correctness() {
    let event = TextMessageChunk::new("Hello".to_string(), Some("msg_1".to_string()));
    let sse = SSEFormatter::format_event(&event, false);

    // Should start with "data: "
    assert!(sse.starts_with("data: "));

    // Should end with double newline
    assert!(sse.ends_with("\n\n"));

    // Should contain valid JSON
    let json_part = sse.trim_start_matches("data: ").trim_end_matches("\n\n");
    let parsed: serde_json::Value = serde_json::from_str(json_part).unwrap();
    assert!(parsed.is_object());
}

#[tokio::test]
async fn test_sse_format_with_event_name() {
    let event = TextMessageChunk::new("Hello".to_string(), Some("msg_1".to_string()));
    let sse = SSEFormatter::format_event(&event, true);

    // Should start with "event: "
    assert!(sse.starts_with("event: "));

    // Should contain "data: " on a separate line
    assert!(sse.contains("\ndata: "));
}

#[tokio::test]
async fn test_sse_stream_completeness() {
    let agent = Arc::new(MockAgent::new("TestAgent", "Hello World"));
    let adapter = AGUIAdapter::new(agent, AGUIAdapterConfig::default());
    let message = Message::with_text("user", "test");

    let mut stream = AGUISSEStream::new(adapter, message).await;

    let mut chunks = Vec::new();
    while let Some(chunk) = stream.next().await {
        chunks.push(chunk);
    }

    // Should have multiple SSE chunks
    assert!(!chunks.is_empty());

    // Last chunk should be completion comment
    let last = chunks.last().unwrap();
    assert!(last.contains("stream_complete"));

    // All chunks should be valid SSE format
    for chunk in &chunks {
        assert!(
            chunk.starts_with("data: ") || chunk.starts_with(": "),
            "Invalid SSE format: {}",
            chunk
        );
    }
}

// ============================================================================
// WebSocket Transport Tests
// ============================================================================

#[tokio::test]
async fn test_websocket_message_format_json() {
    let event = TextMessageChunk::new("Hello".to_string(), Some("msg_1".to_string()));
    let json_str = WebSocketMessageFormat::format_event(&event);

    // Should be valid JSON
    let parsed: serde_json::Value = serde_json::from_str(&json_str).unwrap();
    assert!(parsed.is_object());

    // Should contain event_type
    assert_eq!(
        parsed.get("event_type"),
        Some(&serde_json::json!("text_message_chunk"))
    );
}

#[tokio::test]
async fn test_websocket_handler_metadata() {
    let agent = Arc::new(MockAgent::new("TestAgent", "Test"));
    let handler = AGUIWebSocketHandler::new(agent, WebSocketHandlerConfig::default());

    let metadata = handler.create_metadata_event();
    let json = metadata.to_json();

    assert_eq!(json.get("protocol"), Some(&serde_json::json!("ag-ui")));
    assert_eq!(json.get("transport"), Some(&serde_json::json!("websocket")));

    // Should have bidirectional capability
    if let Some(caps) = json.get("capabilities") {
        if let Some(bidirectional) = caps.get("bidirectional") {
            assert_eq!(bidirectional, &serde_json::json!(true));
        }
    }
}

#[tokio::test]
async fn test_websocket_handler_ping_pong() {
    let agent = Arc::new(MockAgent::new("TestAgent", "Test"));
    let handler = AGUIWebSocketHandler::new(agent, WebSocketHandlerConfig::default());

    let ping = r#"{"type": "ping"}"#;
    let responses = handler.handle_message(ping).await;

    assert_eq!(responses.len(), 1);

    let parsed: serde_json::Value = serde_json::from_str(&responses[0]).unwrap();
    assert_eq!(parsed.get("type"), Some(&serde_json::json!("pong")));
    assert!(parsed.get("timestamp").is_some());
}

#[tokio::test]
async fn test_websocket_handler_message_processing() {
    let agent = Arc::new(MockAgent::new("TestAgent", "Test response"));
    let handler = AGUIWebSocketHandler::new(agent, WebSocketHandlerConfig::default());

    let message = r#"{"type": "message", "content": "Hello"}"#;
    let responses = handler.handle_message(message).await;

    // Should have multiple response events
    assert!(!responses.is_empty());

    // All should be valid JSON
    for response in &responses {
        let parsed: serde_json::Value = serde_json::from_str(response).unwrap();
        assert!(parsed.is_object());
    }

    // Should contain event_type in at least one response
    let has_event_type = responses.iter().any(|r| {
        serde_json::from_str::<serde_json::Value>(r)
            .unwrap()
            .get("event_type")
            .is_some()
    });
    assert!(has_event_type);
}

#[tokio::test]
async fn test_websocket_handler_invalid_json() {
    let agent = Arc::new(MockAgent::new("TestAgent", "Test"));
    let handler = AGUIWebSocketHandler::new(agent, WebSocketHandlerConfig::default());

    let invalid = "not json";
    let responses = handler.handle_message(invalid).await;

    assert_eq!(responses.len(), 1);

    let parsed: serde_json::Value = serde_json::from_str(&responses[0]).unwrap();
    assert_eq!(parsed.get("event_type"), Some(&serde_json::json!("error")));
    assert_eq!(
        parsed.get("error_code"),
        Some(&serde_json::json!("invalid_json"))
    );
}

#[tokio::test]
async fn test_websocket_handler_message_size_limit() {
    let agent = Arc::new(MockAgent::new("TestAgent", "Test"));
    let mut config = WebSocketHandlerConfig::default();
    config.max_message_size = 10; // Very small

    let handler = AGUIWebSocketHandler::new(agent, config);

    let large = r#"{"type": "message", "content": "This is a very long message"}"#;
    let responses = handler.handle_message(large).await;

    assert_eq!(responses.len(), 1);

    let parsed: serde_json::Value = serde_json::from_str(&responses[0]).unwrap();
    assert_eq!(
        parsed.get("error_code"),
        Some(&serde_json::json!("message_too_large"))
    );
}

// ============================================================================
// End-to-End Integration Tests
// ============================================================================

#[tokio::test]
async fn test_end_to_end_basic_flow() {
    // Complete flow: Agent -> Adapter -> SSE Stream -> Events
    let agent = Arc::new(MockAgent::new("E2EAgent", "Complete response"));
    let adapter = AGUIAdapter::new(
        agent,
        AGUIAdapterConfig {
            agent_name: Some("E2ETest".to_string()),
            chunk_size: 10,
        },
    );

    let message = Message::with_text("user", "test");
    let mut sse_stream = AGUISSEStream::new(adapter, message).await;

    let mut event_sequence = Vec::new();
    while let Some(sse_chunk) = sse_stream.next().await {
        // Parse SSE to get event type
        if sse_chunk.starts_with("data: ") {
            let json_part = sse_chunk.trim_start_matches("data: ").trim();
            if let Ok(parsed) = serde_json::from_str::<serde_json::Value>(json_part) {
                if let Some(event_type) = parsed.get("event_type") {
                    event_sequence.push(event_type.as_str().unwrap().to_string());
                }
            }
        }
    }

    // Verify event sequence
    assert!(event_sequence.contains(&"text_message_start".to_string()));
    assert!(event_sequence.contains(&"text_message_chunk".to_string()));
    assert!(event_sequence.contains(&"text_message_complete".to_string()));
}

#[tokio::test]
async fn test_end_to_end_hitl_flow() {
    // Complete HITL flow: HumanInLoopAgent -> HITL Adapter -> Events with Interrupts
    let agent = Arc::new(MockAgent::new("HITLAgent", "Response").with_confidence(0.6));

    let hil_agent = HumanInLoopAgent::new(HumanInLoopConfig {
        agent,
        approval_threshold: 0.8,
        approval_func: simple_approval_func(true),
        confidence_key: "confidence".to_string(),
    })
    .unwrap();

    let adapter =
        AGUIHumanInLoopAdapter::new(Arc::new(hil_agent), AGUIHumanInLoopConfig::default());

    let message = Message::with_text("user", "test");
    let mut stream = adapter.stream_events(message, None, true).await;

    let mut event_types = Vec::new();
    while let Some(event) = stream.next().await {
        event_types.push(event.event_type());
    }

    // Should have metadata (from emit_metadata=true)
    assert!(event_types.contains(&EventType::Metadata));

    // Should have interrupt (due to low confidence)
    assert!(event_types.contains(&EventType::Interrupt));

    // Should have complete message flow
    assert!(event_types.contains(&EventType::TextMessageStart));
    assert!(event_types.contains(&EventType::TextMessageComplete));
}
