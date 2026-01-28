///! AG-UI HTTP/SSE Transport
///!
///! Implements Server-Sent Events (SSE) transport for AG-UI protocol over HTTP.
///! Provides framework-agnostic SSE formatting and helpers for popular web frameworks.
///!
///! # SSE Format
///!
///! Events are formatted as:
///! ```text
///! data: {"event_type": "text_message_chunk", ...}\n\n
///! ```
///!
///! Or with event names:
///! ```text
///! event: text_message_chunk
///! data: {...}\n\n
///! ```
///!
///! # Example (Framework-Agnostic)
///! ```no_run
///! use agenkit::core::{Agent, Message};
///! use agenkit::protocols::agui::{AGUIAdapter, AGUIAdapterConfig};
///! use agenkit::protocols::agui::transports::http::{SSEFormatter, AGUISSEStream};
///! use futures::stream::StreamExt;
///! use std::sync::Arc;
///!
///! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
///! # let agent: Arc<dyn Agent> = todo!();
///! let adapter = AGUIAdapter::new(agent, AGUIAdapterConfig::default());
///! let message = Message::with_text("user", "Hello!");
///!
///! let mut stream = AGUISSEStream::new(adapter, message);
///!
///! while let Some(sse_chunk) = stream.next().await {
///!     // Write sse_chunk to HTTP response
///!     println!("{}", sse_chunk);
///! }
///! # Ok(())
///! # }
///! ```

use crate::core::Message;
use crate::protocols::agui::adapter::AGUIAdapter;
use crate::protocols::agui::events::AGUIEvent;
use futures::stream::{Stream, StreamExt};
use std::pin::Pin;

/// Formats AG-UI events as Server-Sent Events (SSE).
///
/// SSE format follows the EventSource specification:
/// - `data:` lines contain the JSON payload
/// - `event:` lines (optional) specify the event type
/// - Empty line (`\n\n`) terminates each message
pub struct SSEFormatter;

impl SSEFormatter {
    /// Format AG-UI event as SSE message.
    ///
    /// # Arguments
    /// * `event` - AG-UI event to format
    /// * `include_event_name` - Whether to include "event:" line
    ///
    /// # Returns
    /// SSE-formatted string ready to send over HTTP
    ///
    /// # Example
    /// ```
    /// use agenkit::protocols::agui::events::TextMessageChunk;
    /// use agenkit::protocols::agui::transports::http::SSEFormatter;
    ///
    /// let event = TextMessageChunk::new("Hello".to_string(), Some("msg_123".to_string()));
    /// let sse = SSEFormatter::format_event(&event, false);
    /// assert!(sse.starts_with("data: "));
    /// assert!(sse.ends_with("\n\n"));
    /// ```
    pub fn format_event(event: &dyn AGUIEvent, include_event_name: bool) -> String {
        let event_data = event.to_json();
        let event_json = serde_json::to_string(&event_data).unwrap_or_else(|_| "{}".to_string());

        if include_event_name {
            let event_name = format!("{:?}", event.event_type()).to_lowercase();
            format!("event: {}\ndata: {}\n\n", event_name, event_json)
        } else {
            format!("data: {}\n\n", event_json)
        }
    }

    /// Format SSE comment (keeps connection alive).
    ///
    /// Comments start with `:` and are ignored by EventSource clients.
    ///
    /// # Arguments
    /// * `comment` - Comment text
    ///
    /// # Returns
    /// SSE comment line
    pub fn format_comment(comment: &str) -> String {
        format!(": {}\n\n", comment)
    }

    /// Format SSE retry directive.
    ///
    /// Tells the client how long to wait before reconnecting.
    ///
    /// # Arguments
    /// * `milliseconds` - Reconnection time in milliseconds
    ///
    /// # Returns
    /// SSE retry line
    pub fn format_retry(milliseconds: u64) -> String {
        format!("retry: {}\n\n", milliseconds)
    }
}

/// Configuration for SSE stream.
#[derive(Debug, Clone)]
pub struct SSEStreamConfig {
    /// Whether to include "event:" lines in SSE output
    pub include_event_names: bool,
    /// Whether to send a completion comment when stream ends
    pub send_completion_comment: bool,
}

impl Default for SSEStreamConfig {
    fn default() -> Self {
        Self {
            include_event_names: false,
            send_completion_comment: true,
        }
    }
}

/// Async stream that produces SSE-formatted AG-UI events.
///
/// Can be used with any Rust web framework that supports async streaming.
///
/// # Example
/// ```no_run
/// use agenkit::core::{Agent, Message};
/// use agenkit::protocols::agui::{AGUIAdapter, AGUIAdapterConfig};
/// use agenkit::protocols::agui::transports::http::AGUISSEStream;
/// use futures::stream::StreamExt;
/// use std::sync::Arc;
///
/// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
/// # let agent: Arc<dyn Agent> = todo!();
/// let adapter = AGUIAdapter::new(agent, AGUIAdapterConfig::default());
/// let message = Message::with_text("user", "Hello!");
///
/// let mut stream = AGUISSEStream::new(adapter, message);
///
/// while let Some(sse_chunk) = stream.next().await {
///     // Send sse_chunk to client
/// }
/// # Ok(())
/// # }
/// ```
pub struct AGUISSEStream {
    event_stream: Pin<Box<dyn Stream<Item = Box<dyn AGUIEvent>> + Send>>,
    config: SSEStreamConfig,
    completed: bool,
}

impl AGUISSEStream {
    /// Create a new SSE stream.
    ///
    /// # Arguments
    /// * `adapter` - AG-UI adapter wrapping the agent
    /// * `message` - Input message to process
    pub async fn new(adapter: AGUIAdapter, message: Message) -> Self {
        Self::with_config(adapter, message, SSEStreamConfig::default()).await
    }

    /// Create a new SSE stream with custom configuration.
    ///
    /// # Arguments
    /// * `adapter` - AG-UI adapter wrapping the agent
    /// * `message` - Input message to process
    /// * `config` - Stream configuration
    pub async fn with_config(adapter: AGUIAdapter, message: Message, config: SSEStreamConfig) -> Self {
        // Start streaming events
        let event_stream = adapter.stream_events(message, None, true).await;

        Self {
            event_stream,
            config,
            completed: false,
        }
    }

    /// Create SSE stream from existing event stream.
    ///
    /// # Arguments
    /// * `event_stream` - Stream of AG-UI events
    /// * `config` - Stream configuration
    pub fn from_event_stream(
        event_stream: Pin<Box<dyn Stream<Item = Box<dyn AGUIEvent>> + Send>>,
        config: SSEStreamConfig,
    ) -> Self {
        Self {
            event_stream,
            config,
            completed: false,
        }
    }
}

impl Stream for AGUISSEStream {
    type Item = String;

    fn poll_next(
        mut self: Pin<&mut Self>,
        cx: &mut std::task::Context<'_>,
    ) -> std::task::Poll<Option<Self::Item>> {
        if self.completed {
            return std::task::Poll::Ready(None);
        }

        match self.event_stream.as_mut().poll_next(cx) {
            std::task::Poll::Ready(Some(event)) => {
                let sse_formatted =
                    SSEFormatter::format_event(event.as_ref(), self.config.include_event_names);
                std::task::Poll::Ready(Some(sse_formatted))
            }
            std::task::Poll::Ready(None) => {
                self.completed = true;
                if self.config.send_completion_comment {
                    std::task::Poll::Ready(Some(SSEFormatter::format_comment("stream_complete")))
                } else {
                    std::task::Poll::Ready(None)
                }
            }
            std::task::Poll::Pending => std::task::Poll::Pending,
        }
    }
}

/// Configuration for SSE response headers.
#[derive(Debug, Clone)]
pub struct SSEResponseConfig {
    /// CORS allowed origins (e.g., ["http://localhost:3000"])
    pub cors_origins: Vec<String>,
    /// Cache control directive
    pub cache_control: String,
    /// Connection header value
    pub connection: String,
}

impl Default for SSEResponseConfig {
    fn default() -> Self {
        Self {
            cors_origins: vec![],
            cache_control: "no-cache".to_string(),
            connection: "keep-alive".to_string(),
        }
    }
}

impl SSEResponseConfig {
    /// Create SSE response headers as a vector of (name, value) tuples.
    ///
    /// # Arguments
    /// * `origin` - Optional request origin for CORS
    ///
    /// # Returns
    /// Vector of HTTP headers
    pub fn headers(&self, origin: Option<&str>) -> Vec<(&str, String)> {
        let mut headers = vec![
            ("Content-Type", "text/event-stream".to_string()),
            ("Cache-Control", self.cache_control.clone()),
            ("Connection", self.connection.clone()),
            ("X-Accel-Buffering", "no".to_string()), // Disable nginx buffering
        ];

        // Add CORS headers if configured
        if !self.cors_origins.is_empty() {
            if let Some(origin) = origin {
                if self.cors_origins.contains(&"*".to_string())
                    || self.cors_origins.contains(&origin.to_string())
                {
                    headers.push(("Access-Control-Allow-Origin", origin.to_string()));
                    headers.push((
                        "Access-Control-Allow-Methods",
                        "POST, OPTIONS".to_string(),
                    ));
                    headers.push((
                        "Access-Control-Allow-Headers",
                        "Content-Type".to_string(),
                    ));
                }
            }
        }

        headers
    }
}

/// Parse request body for AG-UI message.
///
/// Expected JSON format:
/// ```json
/// {
///   "message": "User message text",
///   "message_id": "optional-id"
/// }
/// ```
#[derive(Debug, serde::Deserialize)]
pub struct AGUIRequest {
    /// User message content
    pub message: String,
    /// Optional message ID
    pub message_id: Option<String>,
}

impl AGUIRequest {
    /// Convert request to Message.
    pub fn to_message(&self) -> Message {
        Message::with_text("user", &self.message)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::core::{Agent, AgentError};
    use crate::protocols::agui::adapter::AGUIAdapterConfig;
    use crate::protocols::agui::events::{EventType, TextMessageChunk};
    use async_trait::async_trait;
    use std::sync::Arc;

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
    fn test_sse_formatter_basic() {
        let event = TextMessageChunk::new("Hello".to_string(), Some("msg_123".to_string()));
        let sse = SSEFormatter::format_event(&event, false);

        assert!(sse.starts_with("data: "));
        assert!(sse.ends_with("\n\n"));
        assert!(sse.contains("\"event_type\""));
        assert!(sse.contains("Hello"));
    }

    #[test]
    fn test_sse_formatter_with_event_name() {
        let event = TextMessageChunk::new("Hello".to_string(), Some("msg_123".to_string()));
        let sse = SSEFormatter::format_event(&event, true);

        assert!(sse.starts_with("event: "));
        assert!(sse.contains("\ndata: "));
        assert!(sse.ends_with("\n\n"));
    }

    #[test]
    fn test_sse_formatter_comment() {
        let comment = SSEFormatter::format_comment("ping");
        assert_eq!(comment, ": ping\n\n");
    }

    #[test]
    fn test_sse_formatter_retry() {
        let retry = SSEFormatter::format_retry(3000);
        assert_eq!(retry, "retry: 3000\n\n");
    }

    #[tokio::test]
    async fn test_sse_stream() {
        let agent = Arc::new(MockAgent {
            response: "Test response".to_string(),
        });

        let adapter = AGUIAdapter::new(agent, AGUIAdapterConfig::default());
        let message = Message::with_text("user", "test");

        let mut stream = AGUISSEStream::new(adapter, message).await;

        let mut chunks: Vec<String> = Vec::new();
        while let Some(chunk) = stream.next().await {
            chunks.push(chunk);
        }

        // Should have multiple SSE chunks
        assert!(!chunks.is_empty());

        // All chunks should be valid SSE format
        for chunk in &chunks {
            assert!(
                chunk.starts_with("data: ") || chunk.starts_with(": "),
                "Invalid SSE format: {}",
                chunk
            );
        }

        // Last chunk should be completion comment
        if let Some(last) = chunks.last() {
            assert!(
                last.contains("stream_complete"),
                "Missing completion comment"
            );
        }
    }

    #[test]
    fn test_sse_response_config_headers() {
        let config = SSEResponseConfig::default();
        let headers = config.headers(None);

        // Check required SSE headers
        assert!(headers.iter().any(|(k, v)| k == &"Content-Type"
            && v == "text/event-stream"));
        assert!(headers
            .iter()
            .any(|(k, v)| k == &"Cache-Control" && v == "no-cache"));
        assert!(headers
            .iter()
            .any(|(k, v)| k == &"Connection" && v == "keep-alive"));
    }

    #[test]
    fn test_sse_response_config_cors() {
        let mut config = SSEResponseConfig::default();
        config.cors_origins = vec!["http://localhost:3000".to_string()];

        let headers = config.headers(Some("http://localhost:3000"));

        // Should include CORS headers
        assert!(headers
            .iter()
            .any(|(k, v)| k == &"Access-Control-Allow-Origin"
                && v == "http://localhost:3000"));
    }

    #[test]
    fn test_agui_request_deserialization() {
        let json = r#"{"message": "Hello", "message_id": "msg_123"}"#;
        let req: AGUIRequest = serde_json::from_str(json).unwrap();

        assert_eq!(req.message, "Hello");
        assert_eq!(req.message_id, Some("msg_123".to_string()));

        let message = req.to_message();
        assert_eq!(message.role, "user");
        assert_eq!(message.content_as_str(), Some("Hello"));
    }
}
