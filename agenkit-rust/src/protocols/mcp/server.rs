///! MCPServer — expose agenkit tools as an MCP stdio server.
///!
///! Reads JSON-RPC 2.0 requests from stdin, writes responses to stdout.
///! Handles: `initialize`, `tools/list`, `tools/call`.

use crate::core::{AgentError, Tool};
use crate::protocols::mcp::{
    JsonRpcError, JsonRpcRequest, JsonRpcResponse, McpContent, McpServerInfo, McpToolResult,
};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};

const PROTOCOL_VERSION: &str = "2024-11-05";

/// Configuration for `McpServer`.
pub struct ServerConfig {
    /// Server name advertised during the initialize handshake.
    pub name: String,
    /// Server version advertised during the initialize handshake.
    pub version: String,
    /// agenkit tools to expose via MCP.
    pub tools: Vec<Arc<dyn Tool>>,
}

/// Exposes agenkit tools as an MCP stdio server.
pub struct McpServer {
    info: McpServerInfo,
    tools: HashMap<String, Arc<dyn Tool>>,
    tool_list: Vec<Arc<dyn Tool>>,
}

impl McpServer {
    /// Create a new McpServer with the given configuration.
    pub fn new(cfg: ServerConfig) -> Self {
        let mut tools = HashMap::new();
        let tool_list = cfg.tools.clone();
        for t in cfg.tools {
            tools.insert(t.name().to_string(), t);
        }
        Self {
            info: McpServerInfo {
                name: cfg.name,
                version: cfg.version,
            },
            tools,
            tool_list,
        }
    }

    /// Read JSON-RPC requests from `stdin` and write responses to `stdout`.
    ///
    /// Runs until EOF on stdin or an unrecoverable I/O error.
    pub async fn serve_stdio(&self) -> Result<(), AgentError> {
        let stdin = tokio::io::stdin();
        let stdout = tokio::io::stdout();
        let mut reader = BufReader::new(stdin);
        let mut writer = tokio::io::BufWriter::new(stdout);

        let mut line = String::new();
        loop {
            line.clear();
            let n = reader
                .read_line(&mut line)
                .await
                .map_err(|e| AgentError::Transport(e.to_string()))?;
            if n == 0 {
                break; // EOF
            }

            let resp = match serde_json::from_str::<serde_json::Value>(&line) {
                Err(_) => JsonRpcResponse {
                    jsonrpc: "2.0".to_string(),
                    id: 0,
                    result: None,
                    error: Some(JsonRpcError {
                        code: -32700,
                        message: "parse error".to_string(),
                    }),
                },
                Ok(raw) => {
                    let req = JsonRpcRequest {
                        jsonrpc: raw
                            .get("jsonrpc")
                            .and_then(|v| v.as_str())
                            .unwrap_or("2.0")
                            .to_string(),
                        id: raw.get("id").and_then(|v| v.as_u64()).unwrap_or(0),
                        method: raw
                            .get("method")
                            .and_then(|v| v.as_str())
                            .unwrap_or("")
                            .to_string(),
                        params: raw.get("params").cloned(),
                    };
                    self.handle_request(req).await
                }
            };

            let mut out =
                serde_json::to_string(&resp_to_json(&resp)).unwrap_or_default();
            out.push('\n');
            writer
                .write_all(out.as_bytes())
                .await
                .map_err(|e| AgentError::Transport(e.to_string()))?;
            writer
                .flush()
                .await
                .map_err(|e| AgentError::Transport(e.to_string()))?;
        }
        Ok(())
    }

    /// Dispatch a single JSON-RPC request and return the response.
    ///
    /// Exposed as `pub` so tests can call it directly without a real stdio pipe.
    pub async fn handle_request(&self, req: JsonRpcRequest) -> JsonRpcResponse {
        match req.method.as_str() {
            "initialize" => self.handle_initialize(&req),
            "tools/list" => self.handle_tools_list(&req),
            "tools/call" => self.handle_tools_call(&req).await,
            other => JsonRpcResponse {
                jsonrpc: "2.0".to_string(),
                id: req.id,
                result: None,
                error: Some(JsonRpcError {
                    code: -32601,
                    message: format!("method not found: {other}"),
                }),
            },
        }
    }

    fn handle_initialize(&self, req: &JsonRpcRequest) -> JsonRpcResponse {
        let result = serde_json::json!({
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": self.info.name, "version": self.info.version}
        });
        JsonRpcResponse {
            jsonrpc: "2.0".to_string(),
            id: req.id,
            result: Some(result),
            error: None,
        }
    }

    fn handle_tools_list(&self, req: &JsonRpcRequest) -> JsonRpcResponse {
        let tools: Vec<serde_json::Value> = self
            .tool_list
            .iter()
            .map(|t| serde_json::json!({"name": t.name(), "description": t.description()}))
            .collect();
        JsonRpcResponse {
            jsonrpc: "2.0".to_string(),
            id: req.id,
            result: Some(serde_json::json!({"tools": tools})),
            error: None,
        }
    }

    async fn handle_tools_call(&self, req: &JsonRpcRequest) -> JsonRpcResponse {
        let params = req.params.as_ref().and_then(|v| v.as_object()).cloned();
        let name = params
            .as_ref()
            .and_then(|p| p.get("name"))
            .and_then(|v| v.as_str())
            .unwrap_or("");
        let args: HashMap<String, serde_json::Value> = params
            .as_ref()
            .and_then(|p| p.get("arguments"))
            .and_then(|v| v.as_object())
            .map(|m| m.iter().map(|(k, v)| (k.clone(), v.clone())).collect())
            .unwrap_or_default();

        let tool = match self.tools.get(name) {
            Some(t) => t,
            None => {
                return JsonRpcResponse {
                    jsonrpc: "2.0".to_string(),
                    id: req.id,
                    result: None,
                    error: Some(JsonRpcError {
                        code: -32602,
                        message: format!("unknown tool: {name}"),
                    }),
                };
            }
        };

        let (is_error, text) = match tool.execute(args).await {
            Err(e) => (true, e.to_string()),
            Ok(r) => {
                let is_err = !r.success;
                let text = if is_err {
                    r.error.clone().unwrap_or_default()
                } else {
                    match &r.output {
                        serde_json::Value::String(s) => s.clone(),
                        v => v.to_string(),
                    }
                };
                (is_err, text)
            }
        };

        let mcp_result = McpToolResult {
            content: vec![McpContent {
                content_type: "text".to_string(),
                text,
            }],
            is_error,
        };

        match serde_json::to_value(&mcp_result) {
            Ok(v) => JsonRpcResponse {
                jsonrpc: "2.0".to_string(),
                id: req.id,
                result: Some(v),
                error: None,
            },
            Err(e) => JsonRpcResponse {
                jsonrpc: "2.0".to_string(),
                id: req.id,
                result: None,
                error: Some(JsonRpcError {
                    code: -32603,
                    message: format!("internal error: {e}"),
                }),
            },
        }
    }
}

fn resp_to_json(resp: &JsonRpcResponse) -> serde_json::Value {
    let mut m = serde_json::Map::new();
    m.insert(
        "jsonrpc".to_string(),
        serde_json::Value::String(resp.jsonrpc.clone()),
    );
    m.insert("id".to_string(), serde_json::json!(resp.id));
    if let Some(err) = &resp.error {
        m.insert(
            "error".to_string(),
            serde_json::json!({"code": err.code, "message": err.message}),
        );
    } else if let Some(r) = &resp.result {
        m.insert("result".to_string(), r.clone());
    }
    serde_json::Value::Object(m)
}
