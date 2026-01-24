///! Protocol implementations for agent communication.
///!
///! Provides standardized protocols for agent-to-frontend communication
///! and other agent interaction patterns.
///!
///! # Available Protocols
///!
///! - **AG-UI**: Agent-User Interaction protocol for streaming agent responses
///!   to frontends over HTTP/SSE and WebSocket.

pub mod agui;

// Re-export main types for convenience
pub use agui::{
    AGUIAdapter, AGUIAdapterConfig, AGUIHumanInLoopAdapter, AGUIHumanInLoopConfig, EventType,
};
pub use agui::transports::http::{SSEFormatter, SSEStreamConfig};
pub use agui::transports::websocket::WebSocketHandlerConfig;
