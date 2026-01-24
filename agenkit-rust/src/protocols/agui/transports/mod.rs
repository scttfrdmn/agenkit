///! AG-UI Transport Layer
///!
///! Provides transport implementations for serving AG-UI protocol over different channels.
///!
///! # Available Transports
///!
///! - **HTTP/SSE**: Server-Sent Events for unidirectional streaming over HTTP
///! - **WebSocket**: Bidirectional streaming with lower latency
///!
///! # Example (HTTP/SSE)
///! ```no_run
///! use agenkit::core::{Agent, Message};
///! use agenkit::protocols::agui::{AGUIAdapter, AGUIAdapterConfig};
///! use agenkit::protocols::agui::transports::http::AGUISSEStream;
///! use futures::stream::StreamExt;
///! use std::sync::Arc;
///!
///! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
///! # let agent: Arc<dyn Agent> = todo!();
///! let adapter = AGUIAdapter::new(agent, AGUIAdapterConfig::default());
///! let message = Message::with_text("user", "Hello!");
///!
///! let mut stream = AGUISSEStream::new(adapter, message);
///! while let Some(sse_chunk) = stream.next().await {
///!     // Send sse_chunk to HTTP response
///! }
///! # Ok(())
///! # }
///! ```
///!
///! # Example (WebSocket)
///! ```no_run
///! use agenkit::core::Agent;
///! use agenkit::protocols::agui::transports::websocket::{
///!     AGUIWebSocketHandler, WebSocketHandlerConfig
///! };
///! use std::sync::Arc;
///!
///! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
///! # let agent: Arc<dyn Agent> = todo!();
///! let handler = AGUIWebSocketHandler::new(agent, WebSocketHandlerConfig::default());
///!
///! // Send metadata on connect
///! let metadata = handler.create_metadata_event();
///! // websocket.send(serde_json::to_string(&metadata)?).await?;
///!
///! // Handle incoming messages
///! // let responses = handler.handle_message(message_str).await;
///! # Ok(())
///! # }
///! ```

pub mod http;
pub mod websocket;

// Re-export main types for convenience
pub use http::{AGUISSEStream, SSEFormatter, SSEResponseConfig, SSEStreamConfig};
pub use websocket::{
    AGUIWebSocketHandler, WebSocketHandlerConfig, WebSocketMessage, WebSocketMessageFormat,
};
