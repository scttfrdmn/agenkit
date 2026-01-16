//! Agents-as-Tools Pattern - Hierarchical Agent Delegation
//!
//! The Agents-as-Tools pattern enables agents to call other agents as tools,
//! creating hierarchical multi-agent systems where specialized agents can be
//! invoked by supervisor agents.
//!
//! # Key Concepts
//!
//! - **AgentTool**: Wrapper that exposes an agent as a tool
//! - **Hierarchical Delegation**: Supervisor delegates to specialist agents
//! - **Tool Interface**: Agents expose standard tool interface (name, description, execute)
//! - **Transparent Integration**: Works with existing ReAct and tool-calling infrastructure
//!
//! # Use Cases
//!
//! - Supervisor agent delegating to specialist agents
//! - Domain-specific agent routing
//! - Hierarchical multi-agent systems
//! - Agent composition and orchestration
//!
//! # Example
//!
//! ```no_run
//! use agenkit::patterns::AgentTool;
//! use agenkit::core::{Agent, Tool, Message};
//! use std::sync::Arc;
//!
//! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
//! # let code_agent: Arc<dyn Agent> = todo!();
//! # let data_agent: Arc<dyn Agent> = todo!();
//! // Create specialist agents
//! let code_tool = AgentTool::new(
//!     code_agent,
//!     "code_specialist",
//!     "Expert in programming, code review, and debugging",
//! );
//!
//! let data_tool = AgentTool::new(
//!     data_agent,
//!     "data_specialist",
//!     "Expert in data analysis, SQL, and visualization",
//! );
//!
//! // Use with supervisor agent that supports tools
//! // (e.g., ReActAgent with tool registry)
//! # Ok(())
//! # }
//! ```
//!
//! # References
//!
//! - LangChain: Agents-as-Tools pattern
//! - AutoGPT: Hierarchical agent architecture
//! - Multi-Agent Systems literature

use async_trait::async_trait;
use std::collections::HashMap;
use std::sync::Arc;

use crate::core::{Agent, AgentError, Message, Tool, ToolResult};

/// Wrapper that exposes an agent as a tool.
///
/// Allows agents to call other agents as tools, enabling hierarchical
/// delegation and specialization. Compatible with existing tool infrastructure
/// (e.g., ReActAgent, ToolRegistry).
///
/// # Performance Characteristics
///
/// - **Latency**: Same as underlying agent
/// - Enables hierarchical composition
/// - Maintains full observability (traces preserved)
///
/// # Example
///
/// ```no_run
/// use agenkit::core::{Agent, Tool};
/// use agenkit::patterns::AgentTool;
/// use std::sync::Arc;
///
/// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
/// # let specialist: Arc<dyn Agent> = todo!();
/// let tool = AgentTool::new(
///     specialist,
///     "code_specialist",
///     "Expert in Python programming and code review",
///)?;
///
/// // Execute as a tool
/// let mut params = std::collections::HashMap::new();
/// params.insert("query".to_string(), serde_json::json!("Write a function to reverse a string"));
/// let result = tool.execute(params).await?;
/// # Ok(())
/// # }
/// ```
pub struct AgentTool {
    agent: Arc<dyn Agent>,
    tool_name: String,
    tool_description: String,
    input_key: String,
    include_metadata: bool,
}

impl AgentTool {
    /// Creates a new AgentTool.
    ///
    /// # Arguments
    ///
    /// * `agent` - The agent to wrap as a tool
    /// * `name` - Tool name for identification and routing
    /// * `description` - Description for LLM to understand when to use this tool
    ///
    /// # Errors
    ///
    /// Returns an error if name or description is empty.
    pub fn new(
        agent: Arc<dyn Agent>,
        name: impl Into<String>,
        description: impl Into<String>,
    ) -> Result<Self, AgentError> {
        let tool_name = name.into();
        let tool_description = description.into();

        if tool_name.is_empty() {
            return Err(AgentError::InvalidInput(
                "Tool name cannot be empty".to_string(),
            ));
        }
        if tool_description.is_empty() {
            return Err(AgentError::InvalidInput(
                "Tool description cannot be empty".to_string(),
            ));
        }

        Ok(Self {
            agent,
            tool_name,
            tool_description,
            input_key: "query".to_string(),
            include_metadata: false,
        })
    }

    /// Creates a new AgentTool with custom configuration.
    ///
    /// # Arguments
    ///
    /// * `agent` - The agent to wrap as a tool
    /// * `name` - Tool name for identification and routing
    /// * `description` - Description for LLM to understand when to use this tool
    /// * `input_key` - Parameter name for input (default: "query")
    /// * `include_metadata` - Whether to include agent metadata in output (default: false)
    pub fn with_config(
        agent: Arc<dyn Agent>,
        name: impl Into<String>,
        description: impl Into<String>,
        input_key: impl Into<String>,
        include_metadata: bool,
    ) -> Result<Self, AgentError> {
        let tool_name = name.into();
        let tool_description = description.into();

        if tool_name.is_empty() {
            return Err(AgentError::InvalidInput(
                "Tool name cannot be empty".to_string(),
            ));
        }
        if tool_description.is_empty() {
            return Err(AgentError::InvalidInput(
                "Tool description cannot be empty".to_string(),
            ));
        }

        Ok(Self {
            agent,
            tool_name,
            tool_description,
            input_key: input_key.into(),
            include_metadata,
        })
    }

    /// Get the underlying agent.
    pub fn agent(&self) -> &Arc<dyn Agent> {
        &self.agent
    }
}

#[async_trait]
impl Tool for AgentTool {
    fn name(&self) -> &str {
        &self.tool_name
    }

    fn description(&self) -> &str {
        &self.tool_description
    }

    fn parameters_schema(&self) -> Option<serde_json::Value> {
        // Basic schema for the input parameter
        let input_key = &self.input_key;
        Some(serde_json::json!({
            "type": "object",
            "properties": {
                input_key: {
                    "type": "string",
                    "description": "Input query or task for the agent"
                }
            },
            "required": [input_key]
        }))
    }

    async fn execute(
        &self,
        params: HashMap<String, serde_json::Value>,
    ) -> Result<ToolResult, AgentError> {
        // Extract input
        let query = params
            .get(&self.input_key)
            .ok_or_else(|| {
                AgentError::InvalidInput(format!(
                    "Missing required parameter '{}'. Available parameters: {:?}",
                    self.input_key,
                    params.keys().collect::<Vec<_>>()
                ))
            })?
            .as_str()
            .ok_or_else(|| {
                AgentError::InvalidInput(format!("Parameter '{}' must be a string", self.input_key))
            })?;

        // Create message
        let message = Message::with_text("user", query);

        // Call agent
        let response = self.agent.process(message).await?;

        // Format output
        let output = if self.include_metadata {
            serde_json::json!({
                "content": response.content,
                "metadata": response.metadata
            })
        } else {
            // Just return the content
            response.content.clone()
        };

        Ok(ToolResult {
            output,
            success: true,
            error: None,
            metadata: HashMap::new(),
        })
    }
}

/// Convenience function to wrap an agent as a tool.
///
/// This is the primary API for creating agent tools.
///
/// # Arguments
///
/// * `agent` - The agent to wrap
/// * `name` - Tool name (used for routing and identification)
/// * `description` - Tool description (helps LLM decide when to use)
///
/// # Example
///
/// ```no_run
/// use agenkit::patterns::agent_as_tool;
/// use agenkit::core::Agent;
/// use std::sync::Arc;
///
/// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
/// # let code_agent: Arc<dyn Agent> = todo!();
/// # let math_agent: Arc<dyn Agent> = todo!();
/// // Create specialists
/// let code_tool = agent_as_tool(
///     code_agent,
///     "code_expert",
///     "Expert programmer for code-related tasks",
/// )?;
///
/// let math_tool = agent_as_tool(
///     math_agent,
///     "math_expert",
///     "Expert mathematician for math problems",
/// )?;
///
/// // Use with supervisor that has tool registry
/// # Ok(())
/// # }
/// ```
pub fn agent_as_tool(
    agent: Arc<dyn Agent>,
    name: impl Into<String>,
    description: impl Into<String>,
) -> Result<AgentTool, AgentError> {
    AgentTool::new(agent, name, description)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicUsize, Ordering};

    // Mock agent for testing
    struct MockAgent {
        agent_name: String,
        call_count: Arc<AtomicUsize>,
    }

    #[async_trait]
    impl Agent for MockAgent {
        fn name(&self) -> &str {
            &self.agent_name
        }

        fn capabilities(&self) -> Vec<String> {
            vec!["mock".to_string()]
        }

        async fn process(&self, message: Message) -> Result<Message, AgentError> {
            self.call_count.fetch_add(1, Ordering::SeqCst);
            let content = message.content_as_str().unwrap_or("");
            let response = format!("Processed: {}", content);
            Ok(Message::with_text("assistant", response))
        }
    }

    #[tokio::test]
    async fn test_agent_tool_basic() {
        let agent = Arc::new(MockAgent {
            agent_name: "test_agent".to_string(),
            call_count: Arc::new(AtomicUsize::new(0)),
        });

        let tool = AgentTool::new(agent, "test_tool", "A test tool").unwrap();

        assert_eq!(tool.name(), "test_tool");
        assert_eq!(tool.description(), "A test tool");

        // Execute the tool
        let mut params = HashMap::new();
        params.insert("query".to_string(), serde_json::json!("Hello, agent!"));

        let result = tool.execute(params).await.unwrap();
        assert!(result.success);
        assert_eq!(result.output.as_str().unwrap(), "Processed: Hello, agent!");
    }

    #[tokio::test]
    async fn test_agent_tool_custom_input_key() {
        let agent = Arc::new(MockAgent {
            agent_name: "test_agent".to_string(),
            call_count: Arc::new(AtomicUsize::new(0)),
        });

        let tool =
            AgentTool::with_config(agent, "test_tool", "A test tool", "task", false).unwrap();

        let mut params = HashMap::new();
        params.insert("task".to_string(), serde_json::json!("Custom input"));

        let result = tool.execute(params).await.unwrap();
        assert!(result.success);
        assert_eq!(result.output.as_str().unwrap(), "Processed: Custom input");
    }

    #[tokio::test]
    async fn test_agent_tool_missing_parameter() {
        let agent = Arc::new(MockAgent {
            agent_name: "test_agent".to_string(),
            call_count: Arc::new(AtomicUsize::new(0)),
        });

        let tool = AgentTool::new(agent, "test_tool", "A test tool").unwrap();

        let params = HashMap::new(); // Missing required "query" parameter

        let result = tool.execute(params).await;
        assert!(result.is_err());
        match result {
            Err(AgentError::InvalidInput(msg)) => {
                assert!(msg.contains("Missing required parameter"));
            }
            _ => panic!("Expected InvalidInput error"),
        }
    }

    #[tokio::test]
    async fn test_agent_tool_validation() {
        let agent = Arc::new(MockAgent {
            agent_name: "test_agent".to_string(),
            call_count: Arc::new(AtomicUsize::new(0)),
        });

        // Test empty name
        let result = AgentTool::new(agent.clone(), "", "Description");
        assert!(result.is_err());

        // Test empty description
        let result = AgentTool::new(agent, "name", "");
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_agent_as_tool_convenience() {
        let agent = Arc::new(MockAgent {
            agent_name: "test_agent".to_string(),
            call_count: Arc::new(AtomicUsize::new(0)),
        });

        let tool = agent_as_tool(agent, "convenience_tool", "Convenience test").unwrap();

        assert_eq!(tool.name(), "convenience_tool");
        assert_eq!(tool.description(), "Convenience test");
    }

    #[tokio::test]
    async fn test_agent_tool_with_metadata() {
        let agent = Arc::new(MockAgent {
            agent_name: "test_agent".to_string(),
            call_count: Arc::new(AtomicUsize::new(0)),
        });

        let tool = AgentTool::with_config(
            agent,
            "test_tool",
            "A test tool",
            "query",
            true, // Include metadata
        )
        .unwrap();

        let mut params = HashMap::new();
        params.insert("query".to_string(), serde_json::json!("Test"));

        let result = tool.execute(params).await.unwrap();
        assert!(result.success);

        // With metadata, output should be an object
        assert!(result.output.is_object());
        assert!(result.output.get("content").is_some());
        assert!(result.output.get("metadata").is_some());
    }
}
