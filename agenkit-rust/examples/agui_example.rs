//! AG-UI Protocol Example
//!
//! Demonstrates the AG-UI (Agent-User Interaction) protocol for streaming
//! agent responses to frontends.
//!
//! This example shows:
//! - Creating an AG-UI adapter
//! - Streaming events from an agent
//! - Different event types (metadata, text messages, errors)
//! - SSE formatting for HTTP transport
//! - WebSocket message formatting
//!
//! # Running
//!
//! ```bash
//! cargo run --example agui_example
//! ```
use agenkit::core::{Agent, AgentError, Message};
use agenkit::protocols::agui::adapter::{AGUIAdapter, AGUIAdapterConfig};
use agenkit::protocols::agui::events::{AGUIEvent, EventType};
use agenkit::protocols::agui::transports::http::AGUISSEStream;
use agenkit::protocols::agui::transports::websocket::WebSocketMessageFormat;
use async_trait::async_trait;
use futures::stream::StreamExt;
use std::sync::Arc;

/// Simple echo agent for demonstration.
struct EchoAgent {
    name: String,
}

impl EchoAgent {
    fn new(name: impl Into<String>) -> Self {
        Self { name: name.into() }
    }
}

#[async_trait]
impl Agent for EchoAgent {
    fn name(&self) -> &str {
        &self.name
    }

    fn capabilities(&self) -> Vec<String> {
        vec!["echo".to_string(), "streaming".to_string()]
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let content = message.content_as_str().unwrap_or("");
        let response = format!("Echo: {}", content);

        Ok(Message::with_text("assistant", &response)
            .with_metadata("confidence", serde_json::json!(0.95)))
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("AG-UI Protocol Example");
    println!("======================\n");

    // Create an agent
    let agent = Arc::new(EchoAgent::new("EchoAgent"));

    // Example 1: Basic event streaming
    println!("Example 1: Basic Event Streaming");
    println!("---------------------------------");
    stream_events_example(agent.clone()).await?;

    println!("\n");

    // Example 2: SSE formatting for HTTP transport
    println!("Example 2: SSE Formatting (HTTP Transport)");
    println!("-------------------------------------------");
    sse_formatting_example(agent.clone()).await?;

    println!("\n");

    // Example 3: WebSocket message formatting
    println!("Example 3: WebSocket Message Formatting");
    println!("----------------------------------------");
    websocket_formatting_example(agent.clone()).await?;

    Ok(())
}

/// Example 1: Stream AG-UI events from an agent.
async fn stream_events_example(agent: Arc<dyn Agent>) -> Result<(), Box<dyn std::error::Error>> {
    // Create AG-UI adapter
    let adapter = AGUIAdapter::new(
        agent,
        AGUIAdapterConfig {
            agent_name: Some("DemoAgent".to_string()),
            chunk_size: 20, // Small chunks for demonstration
        },
    );

    // Create a message
    let message = Message::with_text("user", "Hello, AG-UI!");

    // Stream events
    let mut event_stream = adapter.stream_events(message, None, true).await;

    println!("Streaming events...\n");

    let mut event_count = 0;
    while let Some(event) = event_stream.next().await {
        event_count += 1;

        match event.event_type() {
            EventType::Metadata => {
                println!("  [{}] Metadata Event", event_count);
                let json = event.to_json();
                if let Some(protocol) = json.get("protocol") {
                    println!("    Protocol: {}", protocol);
                }
                if let Some(caps) = json.get("capabilities") {
                    println!("    Capabilities: {}", caps);
                }
            }
            EventType::TextMessageStart => {
                println!("  [{}] Text Message Start", event_count);
                let json = event.to_json();
                if let Some(role) = json.get("role") {
                    println!("    Role: {}", role);
                }
            }
            EventType::TextMessageChunk => {
                let json = event.to_json();
                if let Some(content) = json.get("content") {
                    println!("  [{}] Text Chunk: {}", event_count, content);
                }
            }
            EventType::TextMessageComplete => {
                println!("  [{}] Text Message Complete", event_count);
                let json = event.to_json();
                if let Some(finish_reason) = json.get("finish_reason") {
                    println!("    Finish Reason: {}", finish_reason);
                }
            }
            EventType::Error => {
                println!("  [{}] Error Event", event_count);
                let json = event.to_json();
                if let Some(error_code) = json.get("error_code") {
                    println!("    Error Code: {}", error_code);
                }
            }
            _ => {
                println!("  [{}] Other Event: {:?}", event_count, event.event_type());
            }
        }
    }

    println!("\nTotal events: {}", event_count);

    Ok(())
}

/// Example 2: Format events as Server-Sent Events (SSE) for HTTP.
async fn sse_formatting_example(agent: Arc<dyn Agent>) -> Result<(), Box<dyn std::error::Error>> {
    // Create AG-UI adapter
    let adapter = AGUIAdapter::new(agent, AGUIAdapterConfig::default());

    // Create a message
    let message = Message::with_text("user", "Format me as SSE!");

    // Create SSE stream
    let mut sse_stream = AGUISSEStream::new(adapter, message).await;

    println!("SSE formatted output (ready for HTTP streaming):\n");

    let mut chunk_count = 0;
    while let Some(sse_chunk) = sse_stream.next().await {
        chunk_count += 1;

        // Print first few lines of each SSE chunk
        let lines: Vec<&str> = sse_chunk.lines().take(3).collect();
        println!("  SSE Chunk #{}:", chunk_count);
        for line in lines {
            println!("    {}", line);
        }

        if sse_chunk.lines().count() > 3 {
            println!("    ...");
        }
        println!();
    }

    println!("Total SSE chunks: {}", chunk_count);
    println!("\nThese chunks can be sent directly over HTTP with Content-Type: text/event-stream");

    Ok(())
}

/// Example 3: Format events as WebSocket messages (JSON).
async fn websocket_formatting_example(
    agent: Arc<dyn Agent>,
) -> Result<(), Box<dyn std::error::Error>> {
    // Create AG-UI adapter
    let adapter = AGUIAdapter::new(
        agent,
        AGUIAdapterConfig {
            agent_name: Some("WebSocketAgent".to_string()),
            chunk_size: 30,
        },
    );

    // Create a message
    let message = Message::with_text("user", "Send me over WebSocket!");

    // Stream events
    let mut event_stream = adapter.stream_events(message, None, false).await;

    println!("WebSocket formatted output (JSON messages):\n");

    let mut message_count = 0;
    while let Some(event) = event_stream.next().await {
        message_count += 1;

        // Format as WebSocket message (JSON)
        let ws_message = WebSocketMessageFormat::format_event(event.as_ref());

        // Parse to show structure
        let json: serde_json::Value = serde_json::from_str(&ws_message)?;

        println!("  WebSocket Message #{}:", message_count);
        println!(
            "    Type: {}",
            json.get("event_type")
                .unwrap_or(&serde_json::json!("unknown"))
        );

        // Show content if it's a text chunk
        if let Some(content) = json.get("content") {
            println!("    Content: {}", content);
        }

        // Limit output
        if message_count >= 5 {
            println!("    ... (truncated)");
            break;
        }
    }

    println!("\nThese JSON messages can be sent directly over WebSocket connections");

    Ok(())
}
