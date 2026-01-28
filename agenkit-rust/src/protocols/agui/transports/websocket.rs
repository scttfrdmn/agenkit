///! AG-UI WebSocket Transport
///!
///! Implements bidirectional WebSocket transport for AG-UI protocol.
///! Provides lower latency and bidirectional communication compared to HTTP/SSE.
///!
///! # WebSocket Message Format
///!
///! Messages are JSON objects with event data:
///! ```json
///! {"event_type": "text_message_chunk", "content": "Hello", ...}
///! ```
///!
///! Client messages:
///! ```json
///! {"type": "message", "content": "User message"}
///! {"type": "ping"}
///! ```
///!
///! # Example (Framework-Agnostic)
///! ```no_run
///! use agenkit::core::{Agent, Message};
///! use agenkit::protocols::agui::{AGUIAdapter, AGUIAdapterConfig};
///! use agenkit::protocols::agui::transports::websocket::WebSocketMessageFormat;
///! use std::sync::Arc;
///!
///! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
///! # let agent: Arc<dyn Agent> = todo!();
///! let adapter = AGUIAdapter::new(agent, AGUIAdapterConfig::default());
///!
///! // Format event for WebSocket transmission
///! // let event = ...;
///! // let json = WebSocketMessageFormat::format_event(&event);
///! // websocket.send(json).await?;
///! # Ok(())
///! # }
///! ```

use crate::core::{Agent, Message};
use crate::protocols::agui::adapter::{AGUIAdapter, AGUIAdapterConfig};
use crate::protocols::agui::events::{AGUIEvent, ErrorEvent, HeartbeatEvent, MetadataEvent};
use futures::stream::StreamExt;
use std::collections::HashMap;
use std::sync::Arc;
use std::time::Duration;

/// Formats AG-UI events for WebSocket transmission.
pub struct WebSocketMessageFormat;

impl WebSocketMessageFormat {
    /// Format AG-UI event as WebSocket message (JSON string).
    ///
    /// # Arguments
    /// * `event` - AG-UI event to format
    ///
    /// # Returns
    /// JSON string for WebSocket transmission
    ///
    /// # Example
    /// ```
    /// use agenkit::protocols::agui::events::TextMessageChunk;
    /// use agenkit::protocols::agui::transports::websocket::WebSocketMessageFormat;
    ///
    /// let event = TextMessageChunk::new("Hello".to_string(), Some("msg_123".to_string()));
    /// let json = WebSocketMessageFormat::format_event(&event);
    /// assert!(json.contains("\"event_type\""));
    /// ```
    pub fn format_event(event: &dyn AGUIEvent) -> String {
        let event_data = event.to_json();
        serde_json::to_string(&event_data).unwrap_or_else(|_| "{}".to_string())
    }

    /// Parse WebSocket message (JSON string) to dictionary.
    ///
    /// # Arguments
    /// * `message` - JSON string from WebSocket
    ///
    /// # Returns
    /// Parsed object or error
    pub fn parse_message(message: &str) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::from_str(message)
    }
}

/// Configuration for WebSocket handler.
#[derive(Debug, Clone)]
pub struct WebSocketHandlerConfig {
    /// Optional agent name override
    pub agent_name: Option<String>,
    /// Whether to send metadata event on connect
    pub send_metadata: bool,
    /// Seconds between heartbeat events (None = no heartbeats)
    pub heartbeat_interval: Option<u64>,
    /// Maximum message size in bytes
    pub max_message_size: usize,
}

impl Default for WebSocketHandlerConfig {
    fn default() -> Self {
        Self {
            agent_name: None,
            send_metadata: true,
            heartbeat_interval: Some(30),
            max_message_size: 1024 * 1024, // 1MB
        }
    }
}

/// WebSocket message types.
#[derive(Debug, Clone, serde::Deserialize, serde::Serialize)]
#[serde(tag = "type")]
pub enum WebSocketMessage {
    /// User message
    #[serde(rename = "message")]
    Message {
        /// Message content
        content: String,
        /// Optional message ID
        message_id: Option<String>,
    },
    /// Ping message
    #[serde(rename = "ping")]
    Ping,
    /// Pong response
    #[serde(rename = "pong")]
    Pong {
        /// Timestamp
        timestamp: String,
    },
}

/// WebSocket handler for AG-UI protocol.
///
/// Provides bidirectional communication with automatic event streaming
/// and message processing.
///
/// # Example
/// ```no_run
/// use agenkit::core::Agent;
/// use agenkit::protocols::agui::transports::websocket::{
///     AGUIWebSocketHandler, WebSocketHandlerConfig
/// };
/// use std::sync::Arc;
///
/// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
/// # let agent: Arc<dyn Agent> = todo!();
/// let handler = AGUIWebSocketHandler::new(agent, WebSocketHandlerConfig::default());
///
/// // In your WebSocket connection handler:
/// // let metadata = handler.create_metadata_event().await;
/// // websocket.send(serde_json::to_string(&metadata)?).await?;
/// # Ok(())
/// # }
/// ```
pub struct AGUIWebSocketHandler {
    agent: Arc<dyn Agent>,
    adapter: AGUIAdapter,
    config: WebSocketHandlerConfig,
}

impl AGUIWebSocketHandler {
    /// Create a new WebSocket handler.
    ///
    /// # Arguments
    /// * `agent` - Agent to serve over WebSocket
    /// * `config` - Handler configuration
    pub fn new(agent: Arc<dyn Agent>, config: WebSocketHandlerConfig) -> Self {
        let adapter = AGUIAdapter::new(
            agent.clone(),
            AGUIAdapterConfig {
                agent_name: config.agent_name.clone(),
                chunk_size: 100,
            },
        );

        Self {
            agent,
            adapter,
            config,
        }
    }

    /// Create metadata event to send on connection.
    ///
    /// # Returns
    /// MetadataEvent with agent capabilities
    pub fn create_metadata_event(&self) -> MetadataEvent {
        let mut data = HashMap::new();
        data.insert(
            "agent_name".to_string(),
            serde_json::json!(self
                .config
                .agent_name
                .clone()
                .unwrap_or_else(|| self.agent.name().to_string())),
        );
        data.insert(
            "protocol".to_string(),
            serde_json::json!("ag-ui"),
        );
        data.insert(
            "protocol_version".to_string(),
            serde_json::json!("1.0"),
        );
        data.insert(
            "transport".to_string(),
            serde_json::json!("websocket"),
        );

        let mut capabilities = HashMap::new();
        capabilities.insert("streaming", serde_json::Value::Bool(true));
        capabilities.insert("bidirectional", serde_json::Value::Bool(true));
        capabilities.insert("tool_calls", serde_json::Value::Bool(false));
        capabilities.insert("interrupts", serde_json::Value::Bool(false));
        capabilities.insert("multimodal", serde_json::Value::Bool(false));

        data.insert(
            "capabilities".to_string(),
            serde_json::to_value(capabilities).unwrap_or(serde_json::Value::Null),
        );

        // Add agent capabilities if available
        let introspection = self.agent.introspect();
        if !introspection.capabilities.is_empty() {
            data.insert(
                "agent_capabilities".to_string(),
                serde_json::to_value(&introspection.capabilities)
                    .unwrap_or(serde_json::Value::Null),
            );
        }

        MetadataEvent::new(data)
    }

    /// Create heartbeat event.
    ///
    /// # Returns
    /// HeartbeatEvent with interval
    pub fn create_heartbeat_event(&self) -> HeartbeatEvent {
        let interval_ms = self
            .config
            .heartbeat_interval
            .unwrap_or(30)
            .checked_mul(1000)
            .unwrap_or(30000);
        HeartbeatEvent::new(interval_ms)
    }

    /// Handle incoming WebSocket message.
    ///
    /// # Arguments
    /// * `message_str` - Raw message string from WebSocket
    ///
    /// # Returns
    /// Vector of AG-UI events to send back to client
    pub async fn handle_message(&self, message_str: &str) -> Vec<String> {
        let mut responses = Vec::new();

        // Check message size
        if message_str.len() > self.config.max_message_size {
            let error = ErrorEvent::new(
                "message_too_large",
                format!(
                    "Message size {} exceeds limit {}",
                    message_str.len(),
                    self.config.max_message_size
                ),
                false,
                None,
            );
            responses.push(WebSocketMessageFormat::format_event(&error));
            return responses;
        }

        // Parse message
        let message_data = match WebSocketMessageFormat::parse_message(message_str) {
            Ok(data) => data,
            Err(e) => {
                let error = ErrorEvent::new(
                    "invalid_json",
                    format!("Invalid JSON: {}", e),
                    true,
                    None,
                );
                responses.push(WebSocketMessageFormat::format_event(&error));
                return responses;
            }
        };

        // Extract message type
        let message_type = message_data
            .get("type")
            .and_then(|v| v.as_str())
            .unwrap_or("message");

        match message_type {
            "message" => {
                // Process user message
                let content = message_data
                    .get("content")
                    .or_else(|| message_data.get("message"))
                    .and_then(|v| v.as_str())
                    .unwrap_or("");

                let message = Message::with_text("user", content);

                // Stream response events
                let mut event_stream = self
                    .adapter
                    .stream_events(message, None, false)
                    .await;

                while let Some(event) = event_stream.next().await {
                    responses.push(WebSocketMessageFormat::format_event(event.as_ref()));
                }
            }
            "ping" => {
                // Respond with pong
                let pong = serde_json::json!({
                    "type": "pong",
                    "timestamp": chrono::Utc::now().to_rfc3339(),
                });
                responses.push(serde_json::to_string(&pong).unwrap_or_else(|_| "{}".to_string()));
            }
            _ => {
                // Unknown message type
                let error = ErrorEvent::new(
                    "unknown_message_type",
                    format!("Unknown message type: {}", message_type),
                    true,
                    None,
                );
                responses.push(WebSocketMessageFormat::format_event(&error));
            }
        }

        responses
    }

    /// Get heartbeat interval.
    ///
    /// # Returns
    /// Duration between heartbeats, or None if disabled
    pub fn heartbeat_interval(&self) -> Option<Duration> {
        self.config
            .heartbeat_interval
            .map(Duration::from_secs)
    }

    /// Get the underlying adapter.
    pub fn adapter(&self) -> &AGUIAdapter {
        &self.adapter
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::core::AgentError;
    use async_trait::async_trait;

    struct MockAgent {
        response: String,
    }

    #[async_trait]
    impl Agent for MockAgent {
        fn name(&self) -> &str {
            "MockAgent"
        }

        async fn process(&self, _message: Message) -> Result<Message, AgentError> {
            Ok(Message::new("assistant", serde_json::json!(self.response.clone())))
        }
    }

    #[test]
    fn test_websocket_message_format() {
        use crate::protocols::agui::events::TextMessageChunk;

        let event = TextMessageChunk::new("Hello".to_string(), Some("msg_123".to_string()));
        let json = WebSocketMessageFormat::format_event(&event);

        assert!(json.contains("\"event_type\""));
        assert!(json.contains("Hello"));

        // Should be valid JSON
        let parsed: serde_json::Value = serde_json::from_str(&json).unwrap();
        assert!(parsed.is_object());
    }

    #[test]
    fn test_websocket_message_parse() {
        let json = r#"{"type": "message", "content": "Hello"}"#;
        let parsed = WebSocketMessageFormat::parse_message(json).unwrap();

        assert_eq!(
            parsed.get("type").and_then(|v| v.as_str()),
            Some("message")
        );
        assert_eq!(
            parsed.get("content").and_then(|v| v.as_str()),
            Some("Hello")
        );
    }

    #[test]
    fn test_websocket_handler_config_default() {
        let config = WebSocketHandlerConfig::default();

        assert!(config.send_metadata);
        assert_eq!(config.heartbeat_interval, Some(30));
        assert_eq!(config.max_message_size, 1024 * 1024);
    }

    #[tokio::test]
    async fn test_websocket_handler_metadata() {
        let agent = Arc::new(MockAgent {
            response: "Test".to_string(),
        });

        let handler = AGUIWebSocketHandler::new(agent, WebSocketHandlerConfig::default());
        let metadata = handler.create_metadata_event();

        let json = metadata.to_json();
        assert_eq!(json.get("protocol"), Some(&serde_json::json!("ag-ui")));
        assert_eq!(
            json.get("transport"),
            Some(&serde_json::json!("websocket"))
        );
    }

    #[tokio::test]
    async fn test_websocket_handler_heartbeat() {
        let agent = Arc::new(MockAgent {
            response: "Test".to_string(),
        });

        let handler = AGUIWebSocketHandler::new(agent, WebSocketHandlerConfig::default());
        let heartbeat = handler.create_heartbeat_event();

        let json = heartbeat.to_json();
        assert!(json.get("interval_ms").is_some());
    }

    #[tokio::test]
    async fn test_websocket_handler_message() {
        let agent = Arc::new(MockAgent {
            response: "Test response".to_string(),
        });

        let handler = AGUIWebSocketHandler::new(agent, WebSocketHandlerConfig::default());

        let message = r#"{"type": "message", "content": "Hello"}"#;
        let responses = handler.handle_message(message).await;

        // Should have multiple response events
        assert!(!responses.is_empty());

        // All responses should be valid JSON
        for response in &responses {
            let parsed: serde_json::Value = serde_json::from_str(response).unwrap();
            assert!(parsed.is_object());
        }
    }

    #[tokio::test]
    async fn test_websocket_handler_ping() {
        let agent = Arc::new(MockAgent {
            response: "Test".to_string(),
        });

        let handler = AGUIWebSocketHandler::new(agent, WebSocketHandlerConfig::default());

        let ping = r#"{"type": "ping"}"#;
        let responses = handler.handle_message(ping).await;

        assert_eq!(responses.len(), 1);

        // Should be a pong response
        let parsed: serde_json::Value = serde_json::from_str(&responses[0]).unwrap();
        assert_eq!(parsed.get("type").and_then(|v| v.as_str()), Some("pong"));
        assert!(parsed.get("timestamp").is_some());
    }

    #[tokio::test]
    async fn test_websocket_handler_invalid_json() {
        let agent = Arc::new(MockAgent {
            response: "Test".to_string(),
        });

        let handler = AGUIWebSocketHandler::new(agent, WebSocketHandlerConfig::default());

        let invalid = "not json";
        let responses = handler.handle_message(invalid).await;

        assert_eq!(responses.len(), 1);

        // Should be an error event
        let parsed: serde_json::Value = serde_json::from_str(&responses[0]).unwrap();
        assert_eq!(
            parsed.get("event_type").and_then(|v| v.as_str()),
            Some("error")
        );
        assert_eq!(
            parsed.get("error_code").and_then(|v| v.as_str()),
            Some("invalid_json")
        );
    }

    #[tokio::test]
    async fn test_websocket_handler_message_too_large() {
        let agent = Arc::new(MockAgent {
            response: "Test".to_string(),
        });

        let mut config = WebSocketHandlerConfig::default();
        config.max_message_size = 10; // Very small limit

        let handler = AGUIWebSocketHandler::new(agent, config);

        let large_message = r#"{"type": "message", "content": "This message is too long"}"#;
        let responses = handler.handle_message(large_message).await;

        assert_eq!(responses.len(), 1);

        // Should be an error event
        let parsed: serde_json::Value = serde_json::from_str(&responses[0]).unwrap();
        assert_eq!(
            parsed.get("error_code").and_then(|v| v.as_str()),
            Some("message_too_large")
        );
    }
}
