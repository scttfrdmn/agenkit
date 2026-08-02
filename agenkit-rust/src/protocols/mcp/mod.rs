///! Model Context Protocol (MCP) support for agenkit agents.
///!
///! MCP is a JSON-RPC 2.0 based protocol for AI tool integrations used by
///! Claude Code, Cursor, and thousands of community tools. This module
///! provides both client and server implementations using only crate
///! dependencies already in scope (`serde_json`, `tokio`, `async-trait`).
///!
///! # Client usage — stdio
///!
///! ```no_run
///! use agenkit::protocols::mcp::{StdioClient, tools_from_client};
///!
///! #[tokio::main]
///! async fn main() {
///!     let mut client = StdioClient::new("npx", &["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]);
///!     client.initialize().await.unwrap();
///!     let tools = tools_from_client(&client).await.unwrap();
///! }
///! ```
///!
///! # Server usage
///!
///! ```no_run
///! use agenkit::protocols::mcp::{McpServer, ServerConfig};
///!
///! #[tokio::main]
///! async fn main() {
///!     let server = McpServer::new(ServerConfig {
///!         name: "my-agent".into(),
///!         version: "1.0.0".into(),
///!         tools: vec![],
///!     });
///!     server.serve_stdio().await.unwrap();
///! }
///! ```
pub mod client;
pub mod server;
pub mod tool_adapter;

pub use client::{HttpClient, StdioClient};
pub use server::{McpServer, ServerConfig};
pub use tool_adapter::{tools_from_client, McpToolAdapter};

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

pub(crate) const PROTOCOL_VERSION: &str = "2024-11-05";

// ── JSON-RPC 2.0 wire types ───────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize)]
pub struct JsonRpcRequest {
    pub jsonrpc: String,
    pub id: u64,
    pub method: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub params: Option<serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JsonRpcResponse {
    pub jsonrpc: String,
    pub id: u64,
    pub result: Option<serde_json::Value>,
    pub error: Option<JsonRpcError>,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct JsonRpcError {
    pub code: i32,
    pub message: String,
}

// ── MCP domain types (public) ─────────────────────────────────────────────────

/// Describes a tool advertised by an MCP server.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct McpTool {
    pub name: String,
    pub description: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub input_schema: Option<serde_json::Value>,
}

/// A single content block returned by a tool call.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct McpContent {
    #[serde(rename = "type")]
    pub content_type: String,
    #[serde(default)]
    pub text: String,
}

/// The result of a `tools/call` RPC.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct McpToolResult {
    #[serde(default)]
    pub content: Vec<McpContent>,
    #[serde(rename = "isError", default)]
    pub is_error: bool,
}

/// Information about the connected MCP server.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct McpServerInfo {
    pub name: String,
    pub version: String,
}

// ── MCPClient trait ──────────────────────────────────────────────────────────

use async_trait::async_trait;

/// Trait implemented by both `StdioClient` and `HttpClient`.
#[async_trait]
pub trait McpClient: Send + Sync {
    /// Perform the MCP initialize handshake.
    async fn initialize(&mut self) -> Result<(), crate::core::AgentError>;

    /// Return the tools advertised by the server.
    async fn list_tools(&self) -> Result<Vec<McpTool>, crate::core::AgentError>;

    /// Invoke a named tool with the given arguments.
    async fn call_tool(
        &self,
        name: &str,
        args: HashMap<String, serde_json::Value>,
    ) -> Result<McpToolResult, crate::core::AgentError>;

    /// Server name and version (populated after `initialize`).
    fn server_info(&self) -> &McpServerInfo;
}

// ── text_content helper ───────────────────────────────────────────────────────

/// Join all text-type content blocks with a single space.
pub fn text_content(contents: &[McpContent]) -> String {
    contents
        .iter()
        .filter(|c| c.content_type == "text" && !c.text.is_empty())
        .map(|c| c.text.as_str())
        .collect::<Vec<_>>()
        .join(" ")
}
