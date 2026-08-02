//! Bridge MCP tools to the agenkit Tool trait.
use crate::core::{AgentError, Tool, ToolResult};
use crate::protocols::mcp::{text_content, McpClient, McpTool};
use async_trait::async_trait;
use std::collections::HashMap;
use std::sync::Arc;

/// Wraps an `McpTool` as an agenkit `Tool`.
///
/// The client reference is shared so multiple adapters from the same
/// `tools_from_client` call all share one connection.
pub struct McpToolAdapter {
    client: Arc<dyn McpClient>,
    tool: McpTool,
}

impl McpToolAdapter {
    pub fn new(client: Arc<dyn McpClient>, tool: McpTool) -> Self {
        Self { client, tool }
    }
}

#[async_trait]
impl Tool for McpToolAdapter {
    fn name(&self) -> &str {
        &self.tool.name
    }

    fn description(&self) -> &str {
        &self.tool.description
    }

    async fn execute(
        &self,
        params: HashMap<String, serde_json::Value>,
    ) -> Result<ToolResult, AgentError> {
        let result = self.client.call_tool(&self.tool.name, params).await?;
        let text = text_content(&result.content);
        if result.is_error {
            Ok(ToolResult {
                success: false,
                output: serde_json::Value::Null,
                error: Some(text),
                metadata: Default::default(),
            })
        } else {
            Ok(ToolResult {
                success: true,
                output: serde_json::Value::String(text),
                error: None,
                metadata: Default::default(),
            })
        }
    }
}

/// Call `list_tools` on *client* and wrap each `McpTool` as an agenkit `Tool`.
///
/// The client is wrapped in an `Arc` so all returned adapters share the
/// same connection.
///
/// # Example
///
/// ```no_run
/// use std::sync::Arc;
/// use agenkit::protocols::mcp::{McpClient, StdioClient, tools_from_client};
///
/// #[tokio::main]
/// async fn main() {
///     let mut client = StdioClient::new("npx", &["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]);
///     client.initialize().await.unwrap();
///     let tools = tools_from_client(Arc::new(client)).await.unwrap();
/// }
/// ```
pub async fn tools_from_client(
    client: Arc<dyn McpClient>,
) -> Result<Vec<Arc<dyn Tool>>, AgentError> {
    let mcp_tools = client.list_tools().await?;
    Ok(mcp_tools
        .into_iter()
        .map(|t| Arc::new(McpToolAdapter::new(Arc::clone(&client), t)) as Arc<dyn Tool>)
        .collect())
}
