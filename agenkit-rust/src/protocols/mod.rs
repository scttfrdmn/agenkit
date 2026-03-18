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
pub mod mcp;

// Re-export main types for convenience
pub use agui::{
    AGUIAdapter, AGUIAdapterConfig, AGUIHumanInLoopAdapter, AGUIHumanInLoopConfig, EventType,
};
pub use agui::transports::http::{SSEFormatter, SSEStreamConfig};
pub use agui::transports::websocket::WebSocketHandlerConfig;
pub use mcp::{
    HttpClient as McpHttpClient, McpClient, McpContent, McpServerInfo, McpTool, McpToolResult,
    McpServer, ServerConfig as McpServerConfig, StdioClient as McpStdioClient,
};
pub use mcp::tools_from_client as mcp_tools_from_client;
