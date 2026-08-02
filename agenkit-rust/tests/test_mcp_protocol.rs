///! MCP (Model Context Protocol) protocol tests.
///!
///! Tests the complete MCP implementation:
///! - Wire type serialization (JSON-RPC 2.0)
///! - McpTool / McpContent / McpToolResult types
///! - text_content helper
///! - McpToolAdapter (name, description, execute success/error)
///! - tools_from_client factory
///! - McpServer handle_request (initialize, tools/list, tools/call)
use agenkit::core::{AgentError, Tool, ToolResult};
use agenkit::protocols::mcp::{
    text_content, tools_from_client, HttpClient, McpClient, McpContent, McpServer, McpServerInfo,
    McpTool, McpToolAdapter, McpToolResult, ServerConfig, StdioClient,
};
use agenkit::protocols::mcp::{JsonRpcRequest, JsonRpcResponse};
use async_trait::async_trait;
use std::collections::HashMap;
use std::sync::Arc;

// ── interface compile-time checks ─────────────────────────────────────────────

/// StdioClient and HttpClient implement the McpClient trait.
#[test]
fn test_mcp_client_interface() {
    fn assert_mcp_client<T: McpClient>() {}
    assert_mcp_client::<StdioClient>();
    assert_mcp_client::<HttpClient>();
}

// ── JSON-RPC wire type serialization ─────────────────────────────────────────

#[test]
fn test_jsonrpc_request_serializes_correctly() {
    let req = JsonRpcRequest {
        jsonrpc: "2.0".to_string(),
        id: 42,
        method: "tools/list".to_string(),
        params: None,
    };
    let json = serde_json::to_string(&req).unwrap();
    assert!(json.contains(r#""jsonrpc":"2.0""#));
    assert!(json.contains(r#""id":42"#));
    assert!(json.contains(r#""method":"tools/list""#));
    assert!(!json.contains("params"));
}

#[test]
fn test_jsonrpc_response_deserializes_correctly() {
    let raw = r#"{"jsonrpc":"2.0","id":7,"result":{"ok":true}}"#;
    let resp: JsonRpcResponse = serde_json::from_str(raw).unwrap();
    assert_eq!(resp.jsonrpc, "2.0");
    assert_eq!(resp.id, 7);
    assert!(resp.error.is_none());
    assert!(resp.result.is_some());
}

// ── McpTool serialization ────────────────────────────────────────────────────

#[test]
fn test_mcp_tool_round_trip() {
    let tool = McpTool {
        name: "read_file".to_string(),
        description: "Read a file from disk".to_string(),
        input_schema: None,
    };
    let json = serde_json::to_string(&tool).unwrap();
    let got: McpTool = serde_json::from_str(&json).unwrap();
    assert_eq!(got.name, tool.name);
    assert_eq!(got.description, tool.description);
}

// ── text_content ──────────────────────────────────────────────────────────────

#[test]
fn test_text_content_single() {
    let contents = vec![McpContent {
        content_type: "text".to_string(),
        text: "hello".to_string(),
    }];
    assert_eq!(text_content(&contents), "hello");
}

#[test]
fn test_text_content_multi() {
    let contents = vec![
        McpContent {
            content_type: "text".to_string(),
            text: "hello".to_string(),
        },
        McpContent {
            content_type: "text".to_string(),
            text: "world".to_string(),
        },
    ];
    assert_eq!(text_content(&contents), "hello world");
}

// ── Mock McpClient ────────────────────────────────────────────────────────────

struct MockMcpClient {
    tools: Vec<McpTool>,
    call_result: McpToolResult,
    info: McpServerInfo,
}

impl MockMcpClient {
    fn new(tools: Vec<McpTool>, call_result: McpToolResult) -> Self {
        Self {
            tools,
            call_result,
            info: McpServerInfo {
                name: "mock".to_string(),
                version: "1.0.0".to_string(),
            },
        }
    }
}

#[async_trait]
impl McpClient for MockMcpClient {
    async fn initialize(&mut self) -> Result<(), AgentError> {
        Ok(())
    }

    async fn list_tools(&self) -> Result<Vec<McpTool>, AgentError> {
        Ok(self.tools.clone())
    }

    async fn call_tool(
        &self,
        _name: &str,
        _args: HashMap<String, serde_json::Value>,
    ) -> Result<McpToolResult, AgentError> {
        Ok(self.call_result.clone())
    }

    fn server_info(&self) -> &McpServerInfo {
        &self.info
    }
}

// ── McpToolAdapter ─────────────────────────────────────────────────────────────

#[test]
fn test_mcp_tool_adapter_name() {
    let client = Arc::new(MockMcpClient::new(vec![], McpToolResult::default()));
    let tool = McpTool {
        name: "echo".to_string(),
        description: "Echo input".to_string(),
        input_schema: None,
    };
    let adapter = McpToolAdapter::new(client, tool);
    assert_eq!(adapter.name(), "echo");
}

#[test]
fn test_mcp_tool_adapter_description() {
    let client = Arc::new(MockMcpClient::new(vec![], McpToolResult::default()));
    let tool = McpTool {
        name: "echo".to_string(),
        description: "Echo input".to_string(),
        input_schema: None,
    };
    let adapter = McpToolAdapter::new(client, tool);
    assert_eq!(adapter.description(), "Echo input");
}

#[tokio::test]
async fn test_mcp_tool_adapter_execute_success() {
    let call_result = McpToolResult {
        content: vec![McpContent {
            content_type: "text".to_string(),
            text: "result data".to_string(),
        }],
        is_error: false,
    };
    let client = Arc::new(MockMcpClient::new(vec![], call_result));
    let tool = McpTool {
        name: "mytool".to_string(),
        description: "".to_string(),
        input_schema: None,
    };
    let adapter = McpToolAdapter::new(client, tool);
    let result = adapter.execute(HashMap::new()).await.unwrap();
    assert!(result.success);
    assert_eq!(
        result.output,
        serde_json::Value::String("result data".to_string())
    );
}

#[tokio::test]
async fn test_mcp_tool_adapter_execute_is_error() {
    let call_result = McpToolResult {
        content: vec![McpContent {
            content_type: "text".to_string(),
            text: "something went wrong".to_string(),
        }],
        is_error: true,
    };
    let client = Arc::new(MockMcpClient::new(vec![], call_result));
    let tool = McpTool {
        name: "mytool".to_string(),
        description: "".to_string(),
        input_schema: None,
    };
    let adapter = McpToolAdapter::new(client, tool);
    let result = adapter.execute(HashMap::new()).await.unwrap();
    assert!(!result.success);
    assert_eq!(result.error.as_deref(), Some("something went wrong"));
}

// ── tools_from_client ─────────────────────────────────────────────────────────

#[tokio::test]
async fn test_tools_from_client() {
    let mcp_tools = vec![
        McpTool {
            name: "tool_a".to_string(),
            description: "Tool A".to_string(),
            input_schema: None,
        },
        McpTool {
            name: "tool_b".to_string(),
            description: "Tool B".to_string(),
            input_schema: None,
        },
    ];
    let client = Arc::new(MockMcpClient::new(mcp_tools, McpToolResult::default()));
    let tools = tools_from_client(client).await.unwrap();
    assert_eq!(tools.len(), 2);
    assert_eq!(tools[0].name(), "tool_a");
    assert_eq!(tools[1].name(), "tool_b");
}

// ── McpServer ─────────────────────────────────────────────────────────────────

struct EchoTool;

#[async_trait]
impl Tool for EchoTool {
    fn name(&self) -> &str {
        "echo"
    }

    fn description(&self) -> &str {
        "Echoes the input message"
    }

    async fn execute(
        &self,
        params: HashMap<String, serde_json::Value>,
    ) -> Result<ToolResult, AgentError> {
        let msg = params
            .get("message")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();
        Ok(ToolResult {
            success: true,
            output: serde_json::Value::String(msg),
            error: None,
            metadata: Default::default(),
        })
    }
}

#[tokio::test]
async fn test_mcp_server_handle_request() {
    let server = McpServer::new(ServerConfig {
        name: "test-server".to_string(),
        version: "1.0.0".to_string(),
        tools: vec![Arc::new(EchoTool)],
    });

    // initialize
    let init_req = JsonRpcRequest {
        jsonrpc: "2.0".to_string(),
        id: 1,
        method: "initialize".to_string(),
        params: None,
    };
    let init_resp = server.handle_request(init_req).await;
    assert!(init_resp.error.is_none());
    let result = init_resp.result.unwrap();
    assert_eq!(result["serverInfo"]["name"], "test-server");

    // tools/list
    let list_req = JsonRpcRequest {
        jsonrpc: "2.0".to_string(),
        id: 2,
        method: "tools/list".to_string(),
        params: None,
    };
    let list_resp = server.handle_request(list_req).await;
    assert!(list_resp.error.is_none());
    let tools = &list_resp.result.unwrap()["tools"];
    assert_eq!(tools[0]["name"], "echo");

    // tools/call
    let call_req = JsonRpcRequest {
        jsonrpc: "2.0".to_string(),
        id: 3,
        method: "tools/call".to_string(),
        params: Some(serde_json::json!({
            "name": "echo",
            "arguments": {"message": "hello MCP"}
        })),
    };
    let call_resp = server.handle_request(call_req).await;
    assert!(call_resp.error.is_none());
    let r = call_resp.result.unwrap();
    assert_eq!(r["isError"], false);
    assert_eq!(r["content"][0]["text"], "hello MCP");
}
