///! Agent trait and core abstractions.
///!
///! This module defines the core Agent trait that all agents must implement,
///! following the same design as TypeScript and Go implementations.

use super::message::{Message, ToolResult};
use async_trait::async_trait;
use std::fmt;
use thiserror::Error;

/// Error types for agent operations.
#[derive(Error, Debug)]
pub enum AgentError {
    #[error("agent processing error: {0}")]
    ProcessingError(String),

    #[error("agent timeout: {0}")]
    Timeout(String),

    #[error("agent not found: {0}")]
    NotFound(String),

    #[error("transport error: {0}")]
    Transport(String),

    #[error("serialization error: {0}")]
    Serialization(#[from] serde_json::Error),

    #[error("HTTP error: {0}")]
    Http(#[from] reqwest::Error),

    #[error("internal error: {0}")]
    Internal(String),
}

/// Agent trait - minimal contract for agent communication.
///
/// Design decisions:
/// - Only 2 required methods (name, process)
/// - Optional streaming support via process_stream
/// - No state in trait (agents manage their own state)
/// - Async process (agents typically do I/O)
///
/// # Example
/// ```
/// use agenkit::core::{Agent, Message, AgentError};
/// use async_trait::async_trait;
/// use serde_json::json;
///
/// struct SimpleAgent;
///
/// #[async_trait]
/// impl Agent for SimpleAgent {
///     fn name(&self) -> &str {
///         "simple"
///     }
///
///     async fn process(&self, message: Message) -> Result<Message, AgentError> {
///         Ok(Message::with_text(
///             "assistant",
///             format!("Processed: {}", message.content_as_str().unwrap_or(""))
///         ))
///     }
/// }
/// ```
#[async_trait]
pub trait Agent: Send + Sync {
    /// Agent identifier.
    fn name(&self) -> &str;

    /// Process a message and return a response.
    ///
    /// This is the primary method for synchronous request-response interactions.
    ///
    /// # Arguments
    /// * `message` - Input message
    ///
    /// # Returns
    /// Response message or error
    async fn process(&self, message: Message) -> Result<Message, AgentError>;

    /// What this agent can do (optional).
    ///
    /// Returns a list of capabilities this agent supports.
    fn capabilities(&self) -> Vec<String> {
        Vec::new()
    }
}

/// Tool trait - deterministic operations for agents.
///
/// Design decisions:
/// - Async execute: Tools typically do I/O
/// - Flexible parameters: Tools accept any JSON-serializable input
/// - Rich metadata: name, description, and schema for LLM selection
///
/// # Example
/// ```
/// use agenkit::core::{Tool, ToolResult, AgentError};
/// use async_trait::async_trait;
/// use serde_json::{json, Value};
/// use std::collections::HashMap;
///
/// struct SearchTool;
///
/// #[async_trait]
/// impl Tool for SearchTool {
///     fn name(&self) -> &str {
///         "search"
///     }
///
///     fn description(&self) -> &str {
///         "Search the web"
///     }
///
///     async fn execute(&self, params: HashMap<String, Value>) -> Result<ToolResult, AgentError> {
///         let query = params.get("query")
///             .and_then(|v| v.as_str())
///             .unwrap_or("");
///
///         Ok(ToolResult::success(json!({"results": []})))
///     }
/// }
/// ```
#[async_trait]
pub trait Tool: Send + Sync {
    /// Tool identifier - must be unique within a tool set.
    fn name(&self) -> &str;

    /// What this tool does - used by LLMs to decide when to call it.
    fn description(&self) -> &str;

    /// JSON schema for tool parameters (optional).
    ///
    /// Used by LLMs to understand how to call the tool.
    fn parameters_schema(&self) -> Option<serde_json::Value> {
        None
    }

    /// Execute the tool with given parameters.
    ///
    /// # Arguments
    /// * `params` - Tool parameters (should match schema if provided)
    ///
    /// # Returns
    /// Tool execution result
    async fn execute(
        &self,
        params: std::collections::HashMap<String, serde_json::Value>,
    ) -> Result<ToolResult, AgentError>;
}

/// Helper trait for agents that can provide debug information.
pub trait Debuggable {
    /// Get debug information about the agent's state.
    fn debug_info(&self) -> serde_json::Value;
}

impl fmt::Debug for dyn Agent {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Agent")
            .field("name", &self.name())
            .field("capabilities", &self.capabilities())
            .finish()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    struct EchoAgent {
        name: String,
    }

    #[async_trait]
    impl Agent for EchoAgent {
        fn name(&self) -> &str {
            &self.name
        }

        async fn process(&self, message: Message) -> Result<Message, AgentError> {
            Ok(Message::new("assistant", message.content.clone()))
        }

        fn capabilities(&self) -> Vec<String> {
            vec!["echo".to_string()]
        }
    }

    #[tokio::test]
    async fn test_agent_process() {
        let agent = EchoAgent {
            name: "echo".to_string(),
        };

        let msg = Message::with_text("user", "Hello");
        let response = agent.process(msg).await.unwrap();

        assert_eq!(response.role, "assistant");
        assert_eq!(response.content_as_str(), Some("Hello"));
    }

    #[tokio::test]
    async fn test_agent_capabilities() {
        let agent = EchoAgent {
            name: "echo".to_string(),
        };

        let caps = agent.capabilities();
        assert_eq!(caps, vec!["echo".to_string()]);
    }

    struct CalculatorTool;

    #[async_trait]
    impl Tool for CalculatorTool {
        fn name(&self) -> &str {
            "calculator"
        }

        fn description(&self) -> &str {
            "Perform basic arithmetic"
        }

        fn parameters_schema(&self) -> Option<serde_json::Value> {
            Some(json!({
                "type": "object",
                "properties": {
                    "a": {"type": "number"},
                    "b": {"type": "number"},
                    "op": {"type": "string", "enum": ["add", "sub", "mul", "div"]}
                },
                "required": ["a", "b", "op"]
            }))
        }

        async fn execute(
            &self,
            params: std::collections::HashMap<String, serde_json::Value>,
        ) -> Result<ToolResult, AgentError> {
            let a = params
                .get("a")
                .and_then(|v| v.as_f64())
                .ok_or_else(|| AgentError::ProcessingError("missing 'a' parameter".to_string()))?;
            let b = params
                .get("b")
                .and_then(|v| v.as_f64())
                .ok_or_else(|| AgentError::ProcessingError("missing 'b' parameter".to_string()))?;
            let op = params
                .get("op")
                .and_then(|v| v.as_str())
                .ok_or_else(|| AgentError::ProcessingError("missing 'op' parameter".to_string()))?;

            let result = match op {
                "add" => a + b,
                "sub" => a - b,
                "mul" => a * b,
                "div" => {
                    if b == 0.0 {
                        return Ok(ToolResult::error("division by zero"));
                    }
                    a / b
                }
                _ => return Ok(ToolResult::error(format!("unknown operation: {}", op))),
            };

            Ok(ToolResult::success(json!(result)))
        }
    }

    #[tokio::test]
    async fn test_tool_execute() {
        let tool = CalculatorTool;
        let mut params = std::collections::HashMap::new();
        params.insert("a".to_string(), json!(10.0));
        params.insert("b".to_string(), json!(5.0));
        params.insert("op".to_string(), json!("add"));

        let result = tool.execute(params).await.unwrap();
        assert!(result.success);
        assert_eq!(result.output, json!(15.0));
    }

    #[tokio::test]
    async fn test_tool_division_by_zero() {
        let tool = CalculatorTool;
        let mut params = std::collections::HashMap::new();
        params.insert("a".to_string(), json!(10.0));
        params.insert("b".to_string(), json!(0.0));
        params.insert("op".to_string(), json!("div"));

        let result = tool.execute(params).await.unwrap();
        assert!(!result.success);
        assert_eq!(result.error, Some("division by zero".to_string()));
    }
}
