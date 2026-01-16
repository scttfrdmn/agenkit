//! Reasoning with Tools Pattern
//!
//! Enables interleaved reasoning and tool usage, where tools can be called
//! DURING the reasoning process rather than only after reasoning completes.
//!
//! # Key Concepts
//!
//! - **Interleaved Thinking**: Tools used while reasoning, not just after
//! - **Real-time Refinement**: Tools help refine reasoning in progress
//! - **Extended Thinking**: Supports Claude 4 / o3 style extended reasoning
//!
//! # Differences from ReAct
//!
//! - **ReAct**: Observe → Think → Act → Observe → Think → Act (sequential)
//! - **This**: Think ↔ Act (interleaved, tools available during thinking)
//!
//! # Example
//!
//! ```no_run
//! use agenkit::core::{Agent, Message, Tool};
//! use agenkit::patterns::{ReasoningWithToolsAgent, ReasoningWithToolsConfig};
//! use std::sync::Arc;
//!
//! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
//! # let llm_agent: Arc<dyn Agent> = todo!();
//! # let calculator_tool: Arc<dyn Tool> = todo!();
//! let agent = ReasoningWithToolsAgent::new(
//!     llm_agent,
//!     vec![calculator_tool],
//!     ReasoningWithToolsConfig {
//!         max_reasoning_steps: 10,
//!         enable_trace: true,
//!         ..Default::default()
//!     },
//! );
//!
//! let message = Message::with_text("user", "Calculate 15.99 * 3 with 8.5% tax");
//! let result = agent.process(message).await?;
//! # Ok(())
//! # }
//! ```

use chrono::Utc;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;

use crate::core::{Agent, AgentError, Message, Tool};

/// Type of reasoning step.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum ReasoningStepType {
    /// Thinking step
    Thinking,
    /// Tool call step
    ToolCall,
    /// Tool result step
    ToolResult,
    /// Conclusion step
    Conclusion,
}

impl std::fmt::Display for ReasoningStepType {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ReasoningStepType::Thinking => write!(f, "thinking"),
            ReasoningStepType::ToolCall => write!(f, "tool_call"),
            ReasoningStepType::ToolResult => write!(f, "tool_result"),
            ReasoningStepType::Conclusion => write!(f, "conclusion"),
        }
    }
}

/// Single step in the reasoning process.
#[derive(Debug, Clone, Serialize)]
pub struct ReasoningStep {
    /// Step number
    pub step_number: usize,
    /// Step type
    pub step_type: ReasoningStepType,
    /// Step content
    pub content: String,
    /// Tool name (for tool calls)
    pub tool_name: Option<String>,
    /// Tool parameters (for tool calls)
    pub tool_parameters: Option<HashMap<String, serde_json::Value>>,
    /// Tool result (for tool results)
    pub tool_result: Option<serde_json::Value>,
    /// Confidence score
    pub confidence: f64,
    /// Timestamp in milliseconds
    pub timestamp: i64,
}

/// Complete trace of the reasoning process.
#[derive(Debug, Clone, Serialize)]
pub struct ReasoningTrace {
    /// All reasoning steps
    pub steps: Vec<ReasoningStep>,
    /// Total tools used
    pub total_tools_used: usize,
    /// Total thinking steps
    pub total_thinking_steps: usize,
    /// Start time in milliseconds
    pub start_time: i64,
    /// End time in milliseconds
    pub end_time: i64,
}

/// Configuration for ReasoningWithToolsAgent.
#[derive(Debug, Clone)]
pub struct ReasoningWithToolsConfig {
    /// Maximum reasoning steps
    pub max_reasoning_steps: usize,
    /// Custom tool use prompt
    pub tool_use_prompt: Option<String>,
    /// Enable reasoning trace
    pub enable_trace: bool,
    /// Confidence threshold
    pub confidence_threshold: f64,
}

impl Default for ReasoningWithToolsConfig {
    fn default() -> Self {
        Self {
            max_reasoning_steps: 20,
            tool_use_prompt: None,
            enable_trace: true,
            confidence_threshold: 0.8,
        }
    }
}

/// Agent that can use tools during reasoning (not just after).
///
/// This pattern enables the model to:
/// 1. Start reasoning about a problem
/// 2. Realize it needs information
/// 3. Call a tool to get that information
/// 4. Continue reasoning with the new information
/// 5. Repeat as needed
///
/// # Example
///
/// ```no_run
/// use agenkit::core::{Agent, Message, Tool};
/// use agenkit::patterns::{ReasoningWithToolsAgent, ReasoningWithToolsConfig};
/// use std::sync::Arc;
///
/// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
/// # let llm: Arc<dyn Agent> = todo!();
/// # let tools: Vec<Arc<dyn Tool>> = vec![];
/// let agent = ReasoningWithToolsAgent::new(
///     llm,
///     tools,
///     ReasoningWithToolsConfig {
///         max_reasoning_steps: 20,
///         enable_trace: true,
///         ..Default::default()
///     },
/// );
///
/// let result = agent.process(
///     Message::with_text("user", "Calculate compound interest")
/// ).await?;
/// # Ok(())
/// # }
/// ```
pub struct ReasoningWithToolsAgent {
    llm: Arc<dyn Agent>,
    tools: HashMap<String, Arc<dyn Tool>>,
    max_reasoning_steps: usize,
    tool_use_prompt: String,
    enable_trace: bool,
    #[allow(dead_code)]
    confidence_threshold: f64,
}

impl ReasoningWithToolsAgent {
    /// Create a new reasoning with tools agent.
    pub fn new(
        llm: Arc<dyn Agent>,
        tools: Vec<Arc<dyn Tool>>,
        config: ReasoningWithToolsConfig,
    ) -> Self {
        let tools_map: HashMap<String, Arc<dyn Tool>> = tools
            .into_iter()
            .map(|t| (t.name().to_string(), t))
            .collect();

        let tool_use_prompt = config
            .tool_use_prompt
            .unwrap_or_else(|| Self::default_tool_prompt(&tools_map));

        Self {
            llm,
            tools: tools_map,
            max_reasoning_steps: config.max_reasoning_steps,
            tool_use_prompt,
            enable_trace: config.enable_trace,
            confidence_threshold: config.confidence_threshold,
        }
    }

    /// Generate default tool usage prompt.
    fn default_tool_prompt(tools: &HashMap<String, Arc<dyn Tool>>) -> String {
        let tool_descriptions: Vec<String> = tools
            .values()
            .map(|t| format!("- {}: {}", t.name(), t.description()))
            .collect();

        format!(
            "You can use tools WHILE reasoning about the problem.\n\
             When you need information or computation, use a tool immediately.\n\
             Don't wait until you finish reasoning - use tools as needed.\n\n\
             Available tools:\n{}\n\n\
             To use a tool, output:\n\
             TOOL_CALL: <tool_name>\n\
             PARAMETERS: {{\"param1\": \"value1\", ...}}\n\n\
             Continue reasoning after you get the tool result.",
            tool_descriptions.join("\n")
        )
    }

    /// Parse tool call from text.
    fn parse_tool_call(
        &self,
        text: &str,
    ) -> (
        Option<String>,
        Option<HashMap<String, serde_json::Value>>,
        String,
    ) {
        if !text.contains("TOOL_CALL:") {
            return (None, None, text.to_string());
        }

        let parts: Vec<&str> = text.splitn(2, "TOOL_CALL:").collect();
        let before = parts[0];
        let after = parts[1];

        // Get tool name
        let lines: Vec<&str> = after.split('\n').collect();
        let tool_name = lines[0].trim().to_string();

        // Extract parameters
        let mut parameters = HashMap::new();
        if after.contains("PARAMETERS:") {
            let param_parts: Vec<&str> = after.splitn(2, "PARAMETERS:").collect();
            if param_parts.len() > 1 {
                let param_text = param_parts[1].trim();
                if let Some(start) = param_text.find('{') {
                    if let Some(end) = param_text.rfind('}') {
                        let json_str = &param_text[start..=end];
                        if let Ok(parsed) =
                            serde_json::from_str::<HashMap<String, serde_json::Value>>(json_str)
                        {
                            parameters = parsed;
                        }
                    }
                }
            }
        }

        (Some(tool_name), Some(parameters), before.to_string())
    }

    /// Check if text contains a final conclusion.
    fn is_conclusion(&self, text: &str) -> bool {
        let conclusion_markers = [
            "FINAL ANSWER:",
            "CONCLUSION:",
            "Therefore,",
            "In conclusion,",
            "The answer is",
        ];

        let text_upper = text.to_uppercase();
        conclusion_markers
            .iter()
            .any(|marker| text_upper.contains(&marker.to_uppercase()))
    }

    /// Extract final answer from conclusion text.
    fn extract_answer(&self, text: &str) -> String {
        let markers = ["FINAL ANSWER:", "CONCLUSION:", "The answer is"];
        let text_upper = text.to_uppercase();

        for marker in &markers {
            if let Some(idx) = text_upper.find(&marker.to_uppercase()) {
                return text[idx + marker.len()..].trim().to_string();
            }
        }

        text.to_string()
    }

    /// Get current timestamp in milliseconds.
    fn current_time_millis() -> i64 {
        Utc::now().timestamp_millis()
    }
}

#[async_trait::async_trait]
impl Agent for ReasoningWithToolsAgent {
    fn name(&self) -> &str {
        "reasoning_with_tools"
    }

    fn capabilities(&self) -> Vec<String> {
        vec![
            "reasoning".to_string(),
            "tool-use".to_string(),
            "interleaved-thinking".to_string(),
        ]
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let mut trace = if self.enable_trace {
            Some(ReasoningTrace {
                steps: Vec::new(),
                total_tools_used: 0,
                total_thinking_steps: 0,
                start_time: Self::current_time_millis(),
                end_time: 0,
            })
        } else {
            None
        };

        // Enhance message with tool instructions
        let enhanced_content = format!(
            "{}\n\nUSER QUESTION:\n{}\n\nBegin reasoning. Use tools as needed while thinking.",
            self.tool_use_prompt,
            message.content_as_str().unwrap_or("")
        );

        let mut current_context = enhanced_content;
        let mut final_answer = String::new();

        for step_num in 0..self.max_reasoning_steps {
            // Get next reasoning step from LLM
            let response = self
                .llm
                .process(Message::with_text("user", &current_context))
                .await?;

            let response_text = response.content_as_str().unwrap_or("");

            // Check if this is a tool call
            let (tool_name_opt, parameters_opt, remaining_text) =
                self.parse_tool_call(response_text);

            if let Some(tool_name) = tool_name_opt {
                if let Some(tool) = self.tools.get(&tool_name) {
                    // Record thinking before tool call
                    if let Some(ref mut trace) = trace {
                        if !remaining_text.trim().is_empty() {
                            trace.steps.push(ReasoningStep {
                                step_number: step_num,
                                step_type: ReasoningStepType::Thinking,
                                content: remaining_text.clone(),
                                tool_name: None,
                                tool_parameters: None,
                                tool_result: None,
                                confidence: 0.0,
                                timestamp: Self::current_time_millis(),
                            });
                            trace.total_thinking_steps += 1;
                        }
                    }

                    // Execute tool
                    let params = parameters_opt.unwrap_or_default();
                    let tool_result = tool.execute(params.clone()).await;

                    match tool_result {
                        Ok(result) => {
                            // Record tool call and result
                            if let Some(ref mut trace) = trace {
                                trace.steps.push(ReasoningStep {
                                    step_number: step_num,
                                    step_type: ReasoningStepType::ToolCall,
                                    content: format!("Called {}", tool_name),
                                    tool_name: Some(tool_name.clone()),
                                    tool_parameters: Some(params),
                                    tool_result: None,
                                    confidence: 0.0,
                                    timestamp: Self::current_time_millis(),
                                });

                                trace.steps.push(ReasoningStep {
                                    step_number: step_num,
                                    step_type: ReasoningStepType::ToolResult,
                                    content: format!("{:?}", result.output),
                                    tool_name: Some(tool_name.clone()),
                                    tool_parameters: None,
                                    tool_result: Some(result.output.clone()),
                                    confidence: 0.0,
                                    timestamp: Self::current_time_millis(),
                                });
                                trace.total_tools_used += 1;
                            }

                            // Update context with tool result
                            current_context = format!(
                                "Previous reasoning: {}\n\nTOOL RESULT from {}:\n{:?}\n\nContinue reasoning with this information.",
                                current_context, tool_name, result.output
                            );
                        }
                        Err(err) => {
                            let error_msg = format!("Tool {} failed: {}", tool_name, err);
                            if let Some(ref mut trace) = trace {
                                trace.steps.push(ReasoningStep {
                                    step_number: step_num,
                                    step_type: ReasoningStepType::ToolResult,
                                    content: error_msg.clone(),
                                    tool_name: Some(tool_name),
                                    tool_parameters: None,
                                    tool_result: None,
                                    confidence: 0.0,
                                    timestamp: Self::current_time_millis(),
                                });
                            }

                            current_context = format!(
                                "{}\n\nERROR: {}\n\nContinue reasoning without this tool.",
                                current_context, error_msg
                            );
                        }
                    }

                    continue;
                }
            }

            // Check if we have a final answer
            if self.is_conclusion(response_text) {
                final_answer = self.extract_answer(response_text);
                if let Some(ref mut trace) = trace {
                    trace.steps.push(ReasoningStep {
                        step_number: step_num,
                        step_type: ReasoningStepType::Conclusion,
                        content: final_answer.clone(),
                        tool_name: None,
                        tool_parameters: None,
                        tool_result: None,
                        confidence: 1.0,
                        timestamp: Self::current_time_millis(),
                    });
                }
                break;
            }

            // Regular thinking step
            if let Some(ref mut trace) = trace {
                trace.steps.push(ReasoningStep {
                    step_number: step_num,
                    step_type: ReasoningStepType::Thinking,
                    content: response_text.to_string(),
                    tool_name: None,
                    tool_parameters: None,
                    tool_result: None,
                    confidence: 0.0,
                    timestamp: Self::current_time_millis(),
                });
                trace.total_thinking_steps += 1;
            }

            // Update context for next iteration
            current_context = format!(
                "{}\n\n{}\n\nContinue reasoning or provide final answer.",
                current_context, response_text
            );
        }

        // Finalize trace
        if let Some(ref mut trace) = trace {
            trace.end_time = Self::current_time_millis();
        }

        // If no answer found, use last context
        if final_answer.is_empty() {
            final_answer = current_context;
        }

        // Create response with trace
        let mut metadata = HashMap::new();
        if let Some(trace) = trace {
            let duration_seconds = (trace.end_time - trace.start_time) as f64 / 1000.0;
            metadata.insert(
                "reasoning_steps".to_string(),
                serde_json::json!(trace.steps.len()),
            );
            metadata.insert(
                "tools_used".to_string(),
                serde_json::json!(trace.total_tools_used),
            );
            metadata.insert(
                "duration_seconds".to_string(),
                serde_json::json!(duration_seconds),
            );
        }

        Ok(Message {
            role: "assistant".to_string(),
            content: serde_json::json!(final_answer),
            metadata,
            timestamp: Utc::now(),
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::core::ToolResult;
    use async_trait::async_trait;

    // Mock LLM agent
    struct MockLLM {
        responses: Vec<String>,
        call_count: std::sync::Arc<std::sync::Mutex<usize>>,
    }

    #[async_trait]
    impl Agent for MockLLM {
        fn name(&self) -> &str {
            "mock_llm"
        }

        fn capabilities(&self) -> Vec<String> {
            vec!["mock".to_string()]
        }

        async fn process(&self, _message: Message) -> Result<Message, AgentError> {
            let mut count = self.call_count.lock().unwrap();
            let response = self
                .responses
                .get(*count)
                .unwrap_or(&self.responses[self.responses.len() - 1]);
            *count += 1;

            Ok(Message::with_text("assistant", response))
        }
    }

    // Mock tool
    struct MockTool {
        name: String,
        result: serde_json::Value,
    }

    #[async_trait]
    impl Tool for MockTool {
        fn name(&self) -> &str {
            &self.name
        }

        fn description(&self) -> &str {
            "Mock tool"
        }

        async fn execute(
            &self,
            _parameters: HashMap<String, serde_json::Value>,
        ) -> Result<ToolResult, AgentError> {
            Ok(ToolResult::success(self.result.clone()))
        }
    }

    #[tokio::test]
    async fn test_reasoning_with_tools_basic() {
        let llm = Arc::new(MockLLM {
            responses: vec!["FINAL ANSWER: 42".to_string()],
            call_count: Arc::new(std::sync::Mutex::new(0)),
        });

        let agent = ReasoningWithToolsAgent::new(llm, vec![], ReasoningWithToolsConfig::default());

        let message = Message::with_text("user", "What is the answer?");
        let result = agent.process(message).await.unwrap();

        assert_eq!(result.content_as_str().unwrap(), "42");
    }

    #[tokio::test]
    async fn test_reasoning_with_tools_tool_call() {
        let llm = Arc::new(MockLLM {
            responses: vec![
                "TOOL_CALL: calculator\nPARAMETERS: {\"operation\": \"add\"}".to_string(),
                "FINAL ANSWER: The result is 10".to_string(),
            ],
            call_count: Arc::new(std::sync::Mutex::new(0)),
        });

        let calculator = Arc::new(MockTool {
            name: "calculator".to_string(),
            result: serde_json::json!(10),
        });

        let agent = ReasoningWithToolsAgent::new(
            llm,
            vec![calculator],
            ReasoningWithToolsConfig::default(),
        );

        let message = Message::with_text("user", "Calculate something");
        let result = agent.process(message).await.unwrap();

        assert!(result.content_as_str().unwrap().contains("10"));
    }

    #[tokio::test]
    async fn test_reasoning_step_type_display() {
        assert_eq!(ReasoningStepType::Thinking.to_string(), "thinking");
        assert_eq!(ReasoningStepType::ToolCall.to_string(), "tool_call");
        assert_eq!(ReasoningStepType::ToolResult.to_string(), "tool_result");
        assert_eq!(ReasoningStepType::Conclusion.to_string(), "conclusion");
    }
}
