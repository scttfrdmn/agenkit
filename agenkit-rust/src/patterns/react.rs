//! ReAct (Reasoning + Acting) Agent Pattern
//!
//! Implements the ReAct pattern where agents reason about actions and execute tools
//! in an iterative loop until completing a task.
//!
//! The ReAct loop:
//! 1. Observation: Current state/input
//! 2. Thought: Agent reasons about what to do next
//! 3. Action: Execute a tool or provide final answer
//! 4. Repeat until task is complete
//!
//! References:
//! - ReAct Paper: <https://arxiv.org/abs/2210.03629>
//!
//! # Example
//!
//! ```no_run
//! use agenkit::core::{Agent, Message, Tool, ToolResult, AgentError};
//! use agenkit::patterns::{ReActAgent, ReActConfig};
//! use async_trait::async_trait;
//! use std::sync::Arc;
//! use std::collections::HashMap;
//!
//! # #[derive(Clone)]
//! # struct MockAgent;
//! # #[async_trait]
//! # impl Agent for MockAgent {
//! #     fn name(&self) -> &str { "mock" }
//! #     async fn process(&self, message: Message) -> Result<Message, AgentError> {
//! #         Ok(Message::with_text("assistant", "Final Answer: 42"))
//! #     }
//! # }
//! # struct CalculatorTool;
//! # #[async_trait]
//! # impl Tool for CalculatorTool {
//! #     fn name(&self) -> &str { "calculator" }
//! #     fn description(&self) -> &str { "Performs calculations" }
//! #     async fn execute(&self, _params: HashMap<String, serde_json::Value>)
//! #         -> Result<ToolResult, AgentError> {
//! #         Ok(ToolResult { output: serde_json::json!("42"), success: true, error: None, metadata: HashMap::new() })
//! #     }
//! # }
//! # #[tokio::main]
//! # async fn main() -> Result<(), AgentError> {
//! // Create reasoning agent
//! let reasoning_agent = Arc::new(MockAgent);
//!
//! // Register tools
//! let calculator = Arc::new(CalculatorTool) as Arc<dyn Tool>;
//!
//! // Create ReAct agent
//! let config = ReActConfig {
//!     agent: reasoning_agent,
//!     tools: vec![calculator],
//!     max_steps: 10,
//!     verbose: true,
//!     prompt_template: None,
//! };
//!
//! let react_agent = ReActAgent::new(config)?;
//!
//! // Process a query
//! let message = Message::with_text("user", "What is 15% of 240?");
//! let result = react_agent.process(message).await?;
//! # Ok(())
//! # }
//! ```

#[cfg(test)]
use crate::core::ToolResult;
use crate::core::{Agent, AgentError, Message, Tool};
use async_trait::async_trait;
use std::collections::HashMap;
use std::sync::Arc;

/// A single step in the ReAct reasoning loop.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ReActStep {
    /// The agent's reasoning about what to do
    pub thought: String,
    /// The action to take (tool name or "Final Answer")
    pub action: String,
    /// Parameters for the action
    pub action_input: String,
    /// Result from executing the action
    pub observation: String,
    /// Which step this is in the sequence (0-indexed)
    pub step_number: usize,
    /// Whether this is the final answer
    pub is_final: bool,
}

/// Reason why the ReAct loop terminated.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum StopReason {
    /// Agent provided a final answer
    FinalAnswer,
    /// Maximum number of steps reached
    MaxSteps,
    /// Invalid action was attempted
    InvalidAction,
    /// Tool execution failed critically
    ToolError,
}

impl std::fmt::Display for StopReason {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            StopReason::FinalAnswer => write!(f, "final_answer"),
            StopReason::MaxSteps => write!(f, "max_steps"),
            StopReason::InvalidAction => write!(f, "invalid_action"),
            StopReason::ToolError => write!(f, "tool_error"),
        }
    }
}

/// Configuration for ReActAgent.
pub struct ReActConfig {
    /// Agent to use for reasoning
    pub agent: Arc<dyn Agent>,
    /// Tools available to the agent
    pub tools: Vec<Arc<dyn Tool>>,
    /// Maximum number of reasoning-acting steps (default: 10)
    pub max_steps: usize,
    /// Include step-by-step reasoning in final output (default: true)
    pub verbose: bool,
    /// Custom prompt template for the agent (None = use default)
    pub prompt_template: Option<String>,
}

/// Agent that uses the ReAct pattern to reason and act.
///
/// The agent maintains a thought process, deciding which tools to use
/// and when to provide a final answer.
///
/// Expected agent response format:
/// ```text
/// Thought: [reasoning about what to do]
/// Action: [tool name]
/// Action Input: [tool input]
/// ```
///
/// Or for final answer:
/// ```text
/// Thought: [reasoning about conclusion]
/// Final Answer: [the final answer]
/// ```
pub struct ReActAgent {
    name: String,
    agent: Arc<dyn Agent>,
    tools: HashMap<String, Arc<dyn Tool>>,
    max_steps: usize,
    verbose: bool,
    prompt_template: String,
}

impl ReActAgent {
    /// Create a new ReAct agent.
    ///
    /// # Arguments
    ///
    /// * `config` - Configuration for the agent
    ///
    /// # Errors
    ///
    /// Returns an error if:
    /// - No tools are provided
    /// - Tools have duplicate names
    pub fn new(config: ReActConfig) -> Result<Self, AgentError> {
        if config.tools.is_empty() {
            return Err(AgentError::InvalidInput(
                "at least one tool is required".to_string(),
            ));
        }

        // Build tools map and check for duplicates
        let mut tools_map = HashMap::new();
        for tool in config.tools {
            let name = tool.name().to_string();
            if tools_map.contains_key(&name) {
                return Err(AgentError::InvalidInput(format!(
                    "duplicate tool name: {}",
                    name
                )));
            }
            tools_map.insert(name, tool);
        }

        let max_steps = if config.max_steps == 0 {
            10
        } else {
            config.max_steps
        };

        let prompt_template = config
            .prompt_template
            .unwrap_or_else(|| build_default_prompt(&tools_map));

        Ok(Self {
            name: "ReActAgent".to_string(),
            agent: config.agent,
            tools: tools_map,
            max_steps,
            verbose: config.verbose,
            prompt_template,
        })
    }

    /// Get the reasoning steps from the last execution.
    ///
    /// This is stored in the response metadata under the "steps" key.
    pub fn get_steps_from_metadata(message: &Message) -> Option<Vec<ReActStep>> {
        message
            .metadata
            .get("reasoning")
            .and_then(|v| serde_json::from_value(v.clone()).ok())
    }

    /// Parse agent response into a ReActStep.
    ///
    /// Accepts both final-answer conventions used across the 9 cores (#765):
    /// this core's own `Final Answer: <answer>` line prefix, and the
    /// `Action: Final Answer` / `Action Input: <answer>` form used by Python
    /// and Zig. Without this, a cross-language prompt or few-shot example
    /// written against the Python docs silently degrades into max_steps here:
    /// "Final Answer" gets looked up as a tool name, misses, and the loop
    /// retries the identical response until it gives up.
    fn parse_response(&self, response: &str, step_number: usize) -> ReActStep {
        let lines: Vec<&str> = response.lines().collect();

        let mut thought = String::new();
        let mut action = String::new();
        let mut action_input = String::new();
        let mut observation = String::new();
        let mut is_final = false;

        for line in lines {
            let line = line.trim();

            if let Some(content) = line.strip_prefix("Thought:") {
                thought = content.trim().to_string();
            } else if let Some(content) = line.strip_prefix("Final Answer:") {
                if thought.is_empty() {
                    thought = "Reached final answer".to_string();
                }
                observation = content.trim().to_string();
                is_final = true;
                break;
            } else if let Some(content) = line.strip_prefix("Action Input:") {
                action_input = content.trim().to_string();
            } else if let Some(content) = line.strip_prefix("Action:") {
                action = content.trim().to_string();
            }
        }

        // Python/Zig convention: the sentinel is an action name, with the
        // answer in a following Action Input: line.
        if !is_final && action.eq_ignore_ascii_case("Final Answer") {
            if thought.is_empty() {
                thought = "Reached final answer".to_string();
            }
            observation = action_input.clone();
            is_final = true;
        }

        ReActStep {
            thought,
            action,
            action_input,
            observation,
            step_number,
            is_final,
        }
    }

    /// Format a step for conversation history.
    fn format_step(&self, step: &ReActStep) -> String {
        let mut formatted = format!("Thought: {}", step.thought);

        if !step.action.is_empty() {
            formatted.push_str(&format!("\nAction: {}", step.action));
            formatted.push_str(&format!("\nAction Input: {}", step.action_input));
        }

        if !step.observation.is_empty() {
            formatted.push_str(&format!("\nObservation: {}", step.observation));
        }

        formatted
    }

    /// Format the final answer message.
    fn format_final_answer(&self, steps: &[ReActStep], stop_reason: StopReason) -> Message {
        let mut content = String::new();

        if self.verbose {
            // Include full reasoning trace
            for (i, step) in steps.iter().enumerate() {
                if i > 0 {
                    content.push_str("\n\n");
                }
                content.push_str(&self.format_step(step));
            }
            content.push_str("\n\n---\n\n");
        }

        // Add final answer
        match stop_reason {
            StopReason::FinalAnswer => {
                let final_answer = steps
                    .last()
                    .map(|s| s.observation.clone())
                    .unwrap_or_else(|| "No final answer provided".to_string());
                content.push_str(&final_answer);
            }
            _ => {
                content.push_str(&format!("Unable to complete task ({})", stop_reason));
                if let Some(last_step) = steps.last() {
                    if !last_step.thought.is_empty() {
                        content.push_str(&format!("\nLast thought: {}", last_step.thought));
                    }
                }
            }
        }

        let mut metadata = HashMap::new();
        metadata.insert(
            "stop_reason".to_string(),
            serde_json::json!(stop_reason.to_string()),
        );
        metadata.insert("steps".to_string(), serde_json::json!(steps.len()));
        metadata.insert(
            "reasoning".to_string(),
            serde_json::to_value(steps).unwrap_or(serde_json::json!([])),
        );

        let mut message = Message::with_text("assistant", content);
        message.metadata = metadata;
        message
    }
}

#[async_trait]
impl Agent for ReActAgent {
    fn name(&self) -> &str {
        &self.name
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let mut steps: Vec<ReActStep> = Vec::new();
        let mut conversation_history = vec![
            self.prompt_template.clone(),
            format!("\nQuestion: {}", message.content_as_str().unwrap_or("")),
        ];

        for step in 0..self.max_steps {
            // Get agent's reasoning
            let prompt = conversation_history.join("\n");
            let response = self
                .agent
                .process(Message::with_text("user", &prompt))
                .await?;

            let response_text = response.content_as_str().unwrap_or("");

            // Parse the response
            let mut parsed = self.parse_response(response_text, step);

            // Check for final answer
            if parsed.is_final {
                steps.push(parsed);
                return Ok(self.format_final_answer(&steps, StopReason::FinalAnswer));
            }

            // Validate action
            if parsed.action.is_empty() {
                steps.push(parsed.clone());
                return Ok(self.format_final_answer(&steps, StopReason::InvalidAction));
            }

            // Execute action
            let tool = self.tools.get(&parsed.action);
            if tool.is_none() {
                let available_tools: Vec<&str> = self.tools.keys().map(|s| s.as_str()).collect();
                parsed.observation = format!(
                    "Error: Tool '{}' not found. Available tools: {}",
                    parsed.action,
                    available_tools.join(", ")
                );
                steps.push(parsed.clone());
                conversation_history.push(self.format_step(&parsed));
                continue;
            }

            let tool = tool.unwrap();

            // Execute tool
            let mut params = HashMap::new();
            params.insert("input".to_string(), serde_json::json!(parsed.action_input));

            match tool.execute(params).await {
                Ok(tool_result) => {
                    if tool_result.success {
                        parsed.observation = format!("{}", tool_result.output);
                    } else {
                        let error_msg = tool_result
                            .error
                            .unwrap_or_else(|| "Tool execution failed".to_string());
                        parsed.observation = format!("Error: {}", error_msg);
                    }
                }
                Err(e) => {
                    parsed.observation = format!("Error: {}", e);
                    steps.push(parsed.clone());
                    return Ok(self.format_final_answer(&steps, StopReason::ToolError));
                }
            }

            // Record step and add to conversation
            steps.push(parsed.clone());
            conversation_history.push(self.format_step(&parsed));
        }

        // Max steps reached
        Ok(self.format_final_answer(&steps, StopReason::MaxSteps))
    }
}

/// Build default prompt template with tool descriptions.
fn build_default_prompt(tools: &HashMap<String, Arc<dyn Tool>>) -> String {
    let mut tool_descriptions = Vec::new();
    for (name, tool) in tools {
        tool_descriptions.push(format!("- {}: {}", name, tool.description()));
    }

    format!(
        r#"You are a helpful assistant that can use tools to answer questions.

Available tools:
{}

Use the following format:

Thought: Think about what to do next
Action: [tool name]
Action Input: [input for the tool]
Observation: [result will be provided]

... (repeat Thought/Action/Observation as needed)

Thought: I now know the final answer
Final Answer: [your final answer here]

Begin!"#,
        tool_descriptions.join("\n")
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Mutex;

    #[derive(Clone)]
    struct MockAgent {
        responses: Arc<Mutex<Vec<String>>>,
    }

    #[async_trait]
    impl Agent for MockAgent {
        fn name(&self) -> &str {
            "mock"
        }

        async fn process(&self, _message: Message) -> Result<Message, AgentError> {
            let mut responses = self.responses.lock().unwrap();
            let response = responses.remove(0);
            Ok(Message::with_text("assistant", &response))
        }
    }

    struct CalculatorTool;

    #[async_trait]
    impl Tool for CalculatorTool {
        fn name(&self) -> &str {
            "calculator"
        }

        fn description(&self) -> &str {
            "Performs basic arithmetic calculations"
        }

        async fn execute(
            &self,
            params: HashMap<String, serde_json::Value>,
        ) -> Result<ToolResult, AgentError> {
            let input = params.get("input").and_then(|v| v.as_str()).unwrap_or("");

            // Simple evaluation - just return a mock result
            let result = if input.contains("2+2") {
                "4"
            } else if input.contains("15% of 240") || input.contains("240 * 0.15") {
                "36"
            } else {
                "42"
            };

            Ok(ToolResult {
                output: serde_json::json!(result),
                success: true,
                error: None,
                metadata: HashMap::new(),
            })
        }
    }

    #[tokio::test]
    async fn test_react_agent_final_answer() {
        let responses = vec![
            "Thought: I need to calculate 2+2\nAction: calculator\nAction Input: 2+2".to_string(),
            "Thought: I have the answer now\nFinal Answer: The result is 4".to_string(),
        ];

        let mock_agent = Arc::new(MockAgent {
            responses: Arc::new(Mutex::new(responses)),
        });

        let calculator = Arc::new(CalculatorTool) as Arc<dyn Tool>;

        let config = ReActConfig {
            agent: mock_agent,
            tools: vec![calculator],
            max_steps: 5,
            verbose: false,
            prompt_template: None,
        };

        let react_agent = ReActAgent::new(config).unwrap();
        let message = Message::with_text("user", "What is 2+2?");
        let result = react_agent.process(message).await.unwrap();

        assert_eq!(result.content_as_str().unwrap(), "The result is 4");

        let metadata = &result.metadata;
        assert_eq!(
            metadata.get("stop_reason").and_then(|v| v.as_str()),
            Some("final_answer")
        );
        assert_eq!(metadata.get("steps").and_then(|v| v.as_u64()), Some(2));
    }

    #[tokio::test]
    async fn test_react_agent_tool_not_found() {
        let responses = vec![
            "Thought: I should use a tool\nAction: nonexistent_tool\nAction Input: test"
                .to_string(),
            "Thought: The tool wasn't found, I'll give up\nFinal Answer: Unable to complete task"
                .to_string(),
        ];

        let mock_agent = Arc::new(MockAgent {
            responses: Arc::new(Mutex::new(responses)),
        });

        let calculator = Arc::new(CalculatorTool) as Arc<dyn Tool>;

        let config = ReActConfig {
            agent: mock_agent,
            tools: vec![calculator],
            max_steps: 5,
            verbose: true, // Enable verbose to see the error in the trace
            prompt_template: None,
        };

        let react_agent = ReActAgent::new(config).unwrap();
        let message = Message::with_text("user", "Test");
        let result = react_agent.process(message).await.unwrap();

        let content = result.content_as_str().unwrap();
        assert!(content.contains("Tool 'nonexistent_tool' not found"));
    }

    #[tokio::test]
    async fn test_react_agent_max_steps() {
        let responses = vec![
            "Thought: Step 1\nAction: calculator\nAction Input: test".to_string(),
            "Thought: Step 2\nAction: calculator\nAction Input: test".to_string(),
            "Thought: Step 3\nAction: calculator\nAction Input: test".to_string(),
        ];

        let mock_agent = Arc::new(MockAgent {
            responses: Arc::new(Mutex::new(responses)),
        });

        let calculator = Arc::new(CalculatorTool) as Arc<dyn Tool>;

        let config = ReActConfig {
            agent: mock_agent,
            tools: vec![calculator],
            max_steps: 3,
            verbose: false,
            prompt_template: None,
        };

        let react_agent = ReActAgent::new(config).unwrap();
        let message = Message::with_text("user", "Test");
        let result = react_agent.process(message).await.unwrap();

        let metadata = &result.metadata;
        assert_eq!(
            metadata.get("stop_reason").and_then(|v| v.as_str()),
            Some("max_steps")
        );
        assert_eq!(metadata.get("steps").and_then(|v| v.as_u64()), Some(3));
    }

    #[tokio::test]
    async fn test_react_agent_requires_tools() {
        let mock_agent = Arc::new(MockAgent {
            responses: Arc::new(Mutex::new(vec![])),
        });

        let config = ReActConfig {
            agent: mock_agent,
            tools: vec![],
            max_steps: 5,
            verbose: false,
            prompt_template: None,
        };

        let result = ReActAgent::new(config);
        assert!(result.is_err());
        if let Err(e) = result {
            assert!(e.to_string().contains("at least one tool is required"));
        }
    }

    #[tokio::test]
    async fn test_react_agent_verbose_mode() {
        let responses = vec![
            "Thought: First step\nAction: calculator\nAction Input: 2+2".to_string(),
            "Thought: Got result\nFinal Answer: The answer is 4".to_string(),
        ];

        let mock_agent = Arc::new(MockAgent {
            responses: Arc::new(Mutex::new(responses)),
        });

        let calculator = Arc::new(CalculatorTool) as Arc<dyn Tool>;

        let config = ReActConfig {
            agent: mock_agent,
            tools: vec![calculator],
            max_steps: 5,
            verbose: true,
            prompt_template: None,
        };

        let react_agent = ReActAgent::new(config).unwrap();
        let message = Message::with_text("user", "What is 2+2?");
        let result = react_agent.process(message).await.unwrap();

        let content = result.content_as_str().unwrap();
        // In verbose mode, should include thought process
        assert!(content.contains("Thought: First step"));
        assert!(content.contains("Action: calculator"));
        assert!(content.contains("---"));
        assert!(content.contains("The answer is 4"));
    }

    /// Verifies the parser also accepts the Python/Zig convention: "Final
    /// Answer" as an action name, with the answer in a following "Action
    /// Input:" line, rather than this core's own "Final Answer: <answer>"
    /// line prefix. See #765 -- without this, a Python-style response
    /// reaching the Rust core looked up "Final Answer" as a tool name,
    /// missed, and burned every step until max_steps.
    #[tokio::test]
    async fn test_react_agent_final_answer_as_action() {
        let responses = vec![
            "Thought: I have the answer\nAction: Final Answer\nAction Input: The result is 4"
                .to_string(),
        ];

        let mock_agent = Arc::new(MockAgent {
            responses: Arc::new(Mutex::new(responses)),
        });

        let calculator = Arc::new(CalculatorTool) as Arc<dyn Tool>;

        let config = ReActConfig {
            agent: mock_agent,
            tools: vec![calculator],
            max_steps: 3,
            verbose: false,
            prompt_template: None,
        };

        let react_agent = ReActAgent::new(config).unwrap();
        let message = Message::with_text("user", "What is 2+2?");
        let result = react_agent.process(message).await.unwrap();

        assert_eq!(result.content_as_str().unwrap(), "The result is 4");

        let metadata = &result.metadata;
        assert_eq!(
            metadata.get("stop_reason").and_then(|v| v.as_str()),
            Some("final_answer")
        );
        assert_eq!(metadata.get("steps").and_then(|v| v.as_u64()), Some(1));
    }
}
