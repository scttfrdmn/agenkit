//! MCP client implementations.
//!
//! `StdioClient` — spawn a subprocess and speak JSON-RPC 2.0 over stdin/stdout.
//! `HttpClient`  — POST JSON-RPC 2.0 to a running MCP HTTP server.
use crate::core::AgentError;
use crate::protocols::mcp::{
    JsonRpcRequest, JsonRpcResponse, McpClient, McpServerInfo, McpTool, McpToolResult,
    PROTOCOL_VERSION,
};
use async_trait::async_trait;
use std::collections::HashMap;
use std::sync::atomic::{AtomicU64, Ordering};
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
use tokio::process::{Child, ChildStdin, ChildStdout, Command};
use tokio::sync::Mutex;

fn init_params() -> serde_json::Value {
    serde_json::json!({
        "protocolVersion": PROTOCOL_VERSION,
        "capabilities": {},
        "clientInfo": {"name": "agenkit", "version": "0.90.0"}
    })
}

fn parse_server_info(result: &serde_json::Value) -> McpServerInfo {
    result
        .get("serverInfo")
        .map(|info| McpServerInfo {
            name: info
                .get("name")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string(),
            version: info
                .get("version")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string(),
        })
        .unwrap_or_default()
}

// ── StdioClient ───────────────────────────────────────────────────────────────

/// MCP client that talks JSON-RPC 2.0 to a subprocess over stdin/stdout.
pub struct StdioClient {
    command: String,
    args: Vec<String>,
    env: Vec<(String, String)>,
    inner: Option<StdioInner>,
    next_id: AtomicU64,
    server_info: McpServerInfo,
}

struct StdioIo {
    stdin: ChildStdin,
    stdout: BufReader<ChildStdout>,
}

struct StdioInner {
    _child: Child,
    io: Mutex<StdioIo>,
}

impl StdioClient {
    /// Create a new StdioClient for the given command and arguments.
    ///
    /// Call `initialize()` before using `list_tools()` or `call_tool()`.
    pub fn new(command: &str, args: &[&str]) -> Self {
        Self {
            command: command.to_string(),
            args: args.iter().map(|s| s.to_string()).collect(),
            env: Vec::new(),
            inner: None,
            next_id: AtomicU64::new(0),
            server_info: McpServerInfo::default(),
        }
    }

    /// Add an environment variable for the subprocess.
    pub fn with_env(mut self, key: &str, value: &str) -> Self {
        self.env.push((key.to_string(), value.to_string()));
        self
    }

    async fn send_request(
        &self,
        method: &str,
        params: Option<serde_json::Value>,
    ) -> Result<JsonRpcResponse, AgentError> {
        let inner = self
            .inner
            .as_ref()
            .ok_or_else(|| AgentError::Internal("mcp: call initialize() first".to_string()))?;

        let id = self.next_id.fetch_add(1, Ordering::SeqCst) + 1;
        let req = JsonRpcRequest {
            jsonrpc: "2.0".to_string(),
            id,
            method: method.to_string(),
            params,
        };

        let line = serde_json::to_string(&req).map_err(AgentError::Serialization)? + "\n";

        // Single lock covers the full write→read cycle to prevent interleaving.
        let mut io = inner.io.lock().await;
        io.stdin
            .write_all(line.as_bytes())
            .await
            .map_err(|e| AgentError::Transport(e.to_string()))?;
        io.stdin
            .flush()
            .await
            .map_err(|e| AgentError::Transport(e.to_string()))?;

        let mut buf = String::new();
        io.stdout
            .read_line(&mut buf)
            .await
            .map_err(|e| AgentError::Transport(e.to_string()))?;

        if buf.is_empty() {
            return Err(AgentError::Transport(
                "mcp: server closed stdout unexpectedly".to_string(),
            ));
        }

        let resp: JsonRpcResponse =
            serde_json::from_str(&buf).map_err(AgentError::Serialization)?;

        if let Some(err) = &resp.error {
            return Err(AgentError::Transport(format!(
                "mcp rpc error {}: {}",
                err.code, err.message
            )));
        }

        Ok(resp)
    }
}

#[async_trait]
impl McpClient for StdioClient {
    async fn initialize(&mut self) -> Result<(), AgentError> {
        let mut cmd = Command::new(&self.command);
        cmd.args(&self.args)
            .stdin(std::process::Stdio::piped())
            .stdout(std::process::Stdio::piped())
            .stderr(std::process::Stdio::null());

        for (k, v) in &self.env {
            cmd.env(k, v);
        }

        let mut child = cmd
            .spawn()
            .map_err(|e| AgentError::Transport(format!("mcp: spawn subprocess: {e}")))?;

        let stdin = child
            .stdin
            .take()
            .ok_or_else(|| AgentError::Transport("mcp: no stdin".to_string()))?;
        let stdout = child
            .stdout
            .take()
            .ok_or_else(|| AgentError::Transport("mcp: no stdout".to_string()))?;

        self.inner = Some(StdioInner {
            _child: child,
            io: Mutex::new(StdioIo {
                stdin,
                stdout: BufReader::new(stdout),
            }),
        });

        let resp = self.send_request("initialize", Some(init_params())).await?;
        let result = resp.result.unwrap_or_default();
        self.server_info = parse_server_info(&result);
        Ok(())
    }

    async fn list_tools(&self) -> Result<Vec<McpTool>, AgentError> {
        let resp = self.send_request("tools/list", None).await?;
        let result = resp.result.unwrap_or_default();
        let tools: Vec<McpTool> = serde_json::from_value(
            result
                .get("tools")
                .cloned()
                .unwrap_or(serde_json::Value::Array(vec![])),
        )
        .map_err(AgentError::Serialization)?;
        Ok(tools)
    }

    async fn call_tool(
        &self,
        name: &str,
        args: HashMap<String, serde_json::Value>,
    ) -> Result<McpToolResult, AgentError> {
        let params = serde_json::json!({"name": name, "arguments": args});
        let resp = self.send_request("tools/call", Some(params)).await?;
        let result = resp.result.unwrap_or_default();
        let tool_result: McpToolResult =
            serde_json::from_value(result).map_err(AgentError::Serialization)?;
        Ok(tool_result)
    }

    fn server_info(&self) -> &McpServerInfo {
        &self.server_info
    }
}

// ── HttpClient ────────────────────────────────────────────────────────────────

/// MCP client that POSTs JSON-RPC 2.0 to a running MCP HTTP server.
#[cfg(feature = "native")]
pub struct HttpClient {
    base_url: String,
    http: reqwest::Client,
    next_id: AtomicU64,
    server_info: McpServerInfo,
}

#[cfg(feature = "native")]
impl HttpClient {
    /// Create a new HttpClient for the given base URL.
    ///
    /// Call `initialize()` before using `list_tools()` or `call_tool()`.
    pub fn new(base_url: &str) -> Self {
        Self {
            base_url: base_url.trim_end_matches('/').to_string(),
            http: reqwest::Client::new(),
            next_id: AtomicU64::new(0),
            server_info: McpServerInfo::default(),
        }
    }

    async fn send_request(
        &self,
        method: &str,
        params: Option<serde_json::Value>,
    ) -> Result<JsonRpcResponse, AgentError> {
        let id = self.next_id.fetch_add(1, Ordering::SeqCst) + 1;
        let req = JsonRpcRequest {
            jsonrpc: "2.0".to_string(),
            id,
            method: method.to_string(),
            params,
        };

        let resp = self
            .http
            .post(&self.base_url)
            .json(&req)
            .send()
            .await
            .map_err(|e| AgentError::Transport(e.to_string()))?;

        let rpc_resp: JsonRpcResponse = resp
            .json()
            .await
            .map_err(|e| AgentError::Transport(e.to_string()))?;

        if let Some(err) = &rpc_resp.error {
            return Err(AgentError::Transport(format!(
                "mcp rpc error {}: {}",
                err.code, err.message
            )));
        }

        Ok(rpc_resp)
    }
}

#[cfg(feature = "native")]
#[async_trait]
impl McpClient for HttpClient {
    async fn initialize(&mut self) -> Result<(), AgentError> {
        let resp = self.send_request("initialize", Some(init_params())).await?;
        let result = resp.result.unwrap_or_default();
        self.server_info = parse_server_info(&result);
        Ok(())
    }

    async fn list_tools(&self) -> Result<Vec<McpTool>, AgentError> {
        let resp = self.send_request("tools/list", None).await?;
        let result = resp.result.unwrap_or_default();
        let tools: Vec<McpTool> = serde_json::from_value(
            result
                .get("tools")
                .cloned()
                .unwrap_or(serde_json::Value::Array(vec![])),
        )
        .map_err(AgentError::Serialization)?;
        Ok(tools)
    }

    async fn call_tool(
        &self,
        name: &str,
        args: HashMap<String, serde_json::Value>,
    ) -> Result<McpToolResult, AgentError> {
        let params = serde_json::json!({"name": name, "arguments": args});
        let resp = self.send_request("tools/call", Some(params)).await?;
        let result = resp.result.unwrap_or_default();
        let tool_result: McpToolResult =
            serde_json::from_value(result).map_err(AgentError::Serialization)?;
        Ok(tool_result)
    }

    fn server_info(&self) -> &McpServerInfo {
        &self.server_info
    }
}

// ── When native feature is disabled, provide a stub HttpClient ────────────────

#[cfg(not(feature = "native"))]
pub struct HttpClient {
    base_url: String,
    server_info: McpServerInfo,
}

#[cfg(not(feature = "native"))]
impl HttpClient {
    pub fn new(base_url: &str) -> Self {
        Self {
            base_url: base_url.to_string(),
            server_info: McpServerInfo::default(),
        }
    }
}

#[cfg(not(feature = "native"))]
#[async_trait]
impl McpClient for HttpClient {
    async fn initialize(&mut self) -> Result<(), AgentError> {
        Err(AgentError::ConfigurationError(
            "HttpClient requires the 'native' feature".to_string(),
        ))
    }

    async fn list_tools(&self) -> Result<Vec<McpTool>, AgentError> {
        Err(AgentError::ConfigurationError(
            "HttpClient requires the 'native' feature".to_string(),
        ))
    }

    async fn call_tool(
        &self,
        _name: &str,
        _args: HashMap<String, serde_json::Value>,
    ) -> Result<McpToolResult, AgentError> {
        Err(AgentError::ConfigurationError(
            "HttpClient requires the 'native' feature".to_string(),
        ))
    }

    fn server_info(&self) -> &McpServerInfo {
        &self.server_info
    }
}
