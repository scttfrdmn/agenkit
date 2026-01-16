//! Rust test harness for cross-language equivalence testing.
//!
//! Implements the JSON protocol for executing pattern tests.

use agenkit::core::{Agent, AgentError, Message};
use agenkit::patterns::{
    ConversationalAgent, ParallelAgent, ReActAgent, ReActConfig, ReflectionAgent,
    ReflectionConfig, SequentialAgent, Task, TaskConfig,
};
use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::io::{self, BufRead};
use std::time::Instant;

const PROTOCOL_VERSION: &str = "1.0";
const VERSION: &str = "0.46.0";

/// Request message from the test runner
#[derive(Debug, Deserialize)]
struct Request {
    protocol_version: String,
    request_id: String,
    command: String,
    payload: serde_json::Value,
}

/// Response message to the test runner
#[derive(Debug, Serialize)]
struct Response {
    protocol_version: String,
    request_id: String,
    status: String,
    result: Option<serde_json::Value>,
    error: Option<ErrorInfo>,
}

/// Error information
#[derive(Debug, Serialize)]
struct ErrorInfo {
    #[serde(rename = "type")]
    error_type: String,
    message: String,
    details: HashMap<String, serde_json::Value>,
}

/// Test execution payload
#[derive(Debug, Deserialize)]
struct ExecuteTestPayload {
    pattern: String,
    scenario_id: String,
    input: TestInput,
}

/// Test input data
#[derive(Debug, Deserialize)]
struct TestInput {
    #[serde(default)]
    message: Option<MessageData>,
    #[serde(default)]
    messages: Option<Vec<MessageData>>,
    #[serde(default)]
    config: HashMap<String, serde_json::Value>,
}

/// Message data from JSON
#[derive(Debug, Clone, Deserialize, Serialize)]
struct MessageData {
    role: String,
    content: String,
    #[serde(default)]
    metadata: HashMap<String, serde_json::Value>,
}

/// Test result
#[derive(Debug, Serialize)]
struct TestResult {
    output: TestOutput,
    execution_info: ExecutionInfo,
}

/// Test output
#[derive(Debug, Serialize)]
struct TestOutput {
    message: MessageData,
    behavior: BehaviorInfo,
}

/// Behavioral characteristics
#[derive(Debug, Serialize)]
struct BehaviorInfo {
    turns: u32,
    tool_calls: Vec<String>,
    sub_agents: Vec<String>,
}

/// Execution information
#[derive(Debug, Serialize)]
struct ExecutionInfo {
    duration_ms: f64,
    llm_calls: u32,
    tokens_used: u32,
}

/// Mock agent for testing - returns predictable responses
#[derive(Clone)]
struct MockAgent {
    responses: Vec<String>,
    call_count: std::sync::Arc<std::sync::Mutex<usize>>,
    name_str: String,
}

impl MockAgent {
    fn new() -> Self {
        Self {
            responses: vec![
                "1. First, let's analyze the problem.\n2. Then, we'll solve it step by step.\n3. Finally, we arrive at the answer: 42.".to_string(),
            ],
            call_count: std::sync::Arc::new(std::sync::Mutex::new(0)),
            name_str: "mock_agent".to_string(),
        }
    }

    fn with_name(name: &str) -> Self {
        Self {
            responses: vec![
                "Mock response from agent.".to_string(),
            ],
            call_count: std::sync::Arc::new(std::sync::Mutex::new(0)),
            name_str: name.to_string(),
        }
    }

    fn with_responses(responses: Vec<String>, name: &str) -> Self {
        Self {
            responses,
            call_count: std::sync::Arc::new(std::sync::Mutex::new(0)),
            name_str: name.to_string(),
        }
    }
}

#[async_trait]
impl Agent for MockAgent {
    fn name(&self) -> &str {
        &self.name_str
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let content = message.content_as_str().unwrap_or("");
        let content_lower = content.to_lowercase();

        // ReAct pattern - calculation (15 * 24 = 360)
        if (content.contains("15 * 24") || content.contains("What is 15"))
            && !content_lower.contains("color") {
            if content.contains("Observation: 360") || content.contains("What's your next thought/action?") {
                // After observation - return final answer
                return Ok(Message::with_text(
                    "assistant",
                    "Thought: I now have the calculation result\nAction: Final Answer\nAction Input: The result of 15 * 24 is 360.",
                ));
            } else {
                // Initial query - request calculator tool
                return Ok(Message::with_text(
                    "assistant",
                    r#"Thought: I need to use the calculator tool to compute 15 * 24
Action: calculator
Action Input: {"a": 15, "b": 24}"#,
                ));
            }
        }

        // ReAct pattern - simple factual questions (no tools needed)
        if content_lower.contains("color") && content_lower.contains("sky") {
            return Ok(Message::with_text(
                "assistant",
                "Thought: This is a simple factual question I can answer directly\nAction: Final Answer\nAction Input: The sky is blue during the day due to Rayleigh scattering of sunlight.",
            ));
        }

        // Task pattern - impossible task (should fail)
        if content_lower.contains("impossible") {
            return Err(AgentError::ProcessingError("Task cannot be completed".to_string()));
        }

        // Reflection pattern - poetry about technology
        if content_lower.contains("poem") && content_lower.contains("technology") {
            return Ok(Message::with_text(
                "assistant",
                "Here's a poem about technology:\n\nCircuits hum with electric dreams,\nConnecting worlds through digital streams.\nInnovation's spark lights up the night,\nTechnology guides us to new height.",
            ));
        }

        // Reflection pattern - critique prompt
        if content_lower.contains("critique") || content_lower.contains("improve") {
            return Ok(Message::with_text(
                "assistant",
                "Quality Score: 7/10\n\nFeedback: The poem captures technology well but could be more specific. Consider adding more vivid imagery.\n\nSuggestion: Add references to specific technologies or their impact on society.",
            ));
        }

        // Conversational pattern - name recall
        if content_lower.contains("what") && content_lower.contains("name") {
            // Simple response for now - actual conversational pattern has history
            return Ok(Message::with_text(
                "assistant",
                "I don't have access to previous conversation history in this context.",
            ));
        }

        // Default response
        let mut count = self.call_count.lock().unwrap();
        let response_text = &self.responses[*count % self.responses.len()];
        *count += 1;
        drop(count);

        Ok(Message::with_text("assistant", response_text))
    }
}

/// Handle health_check command
fn health_check(request_id: &str) -> Response {
    Response {
        protocol_version: PROTOCOL_VERSION.to_string(),
        request_id: request_id.to_string(),
        status: "success".to_string(),
        result: Some(serde_json::json!({
            "healthy": true,
            "uptime_seconds": 0.0,
        })),
        error: None,
    }
}

/// Handle get_info command
fn get_info(request_id: &str) -> Response {
    let patterns_supported = vec![
        "Reflection",
        "Sequential",
        "Parallel",
        "ReAct",
        "Conversational",
        "Task",
    ];

    Response {
        protocol_version: PROTOCOL_VERSION.to_string(),
        request_id: request_id.to_string(),
        status: "success".to_string(),
        result: Some(serde_json::json!({
            "language": "rust",
            "version": VERSION,
            "patterns_supported": patterns_supported,
            "capabilities": {
                "streaming": true,
                "async": true,
                "llm_providers": ["openai", "anthropic"],
            },
        })),
        error: None,
    }
}

/// Handle execute_test command
async fn execute_test(request_id: &str, payload: serde_json::Value) -> Response {
    // Parse payload
    let test_payload: ExecuteTestPayload = match serde_json::from_value(payload) {
        Ok(p) => p,
        Err(e) => {
            return Response {
                protocol_version: PROTOCOL_VERSION.to_string(),
                request_id: request_id.to_string(),
                status: "error".to_string(),
                result: None,
                error: Some(ErrorInfo {
                    error_type: "ValidationError".to_string(),
                    message: format!("Invalid payload: {}", e),
                    details: HashMap::new(),
                }),
            };
        }
    };

    // Parse input message
    let message = if let Some(msg_data) = test_payload.input.message {
        Message::with_text(&msg_data.role, &msg_data.content)
    } else if let Some(messages) = test_payload.input.messages {
        if messages.is_empty() {
            Message::with_text("user", "")
        } else {
            let last_msg = &messages[messages.len() - 1];
            Message::with_text(&last_msg.role, &last_msg.content)
        }
    } else {
        Message::with_text("user", "")
    };

    let config = test_payload.input.config;
    let pattern = test_payload.pattern.as_str();

    // Execute pattern
    let start = Instant::now();
    let result = execute_pattern(pattern, message, config).await;
    let duration_ms = start.elapsed().as_secs_f64() * 1000.0;

    match result {
        Ok(output_message) => {
            // Extract behavior information from metadata
            let mut turns = 1u32;
            let mut tool_calls = Vec::new();
            let mut sub_agents = Vec::new();

            if let Some(metadata_obj) = output_message.metadata.get("metadata").and_then(|v| v.as_object()) {
                // ReAct pattern
                if let Some(steps) = metadata_obj.get("react_steps").and_then(|v| v.as_array()) {
                    for step in steps {
                        if let Some(action) = step.get("action").and_then(|v| v.as_str()) {
                            if action.to_lowercase() != "final answer" {
                                tool_calls.push(action.to_string());
                            }
                        }
                    }
                    turns = (steps.len() * 2 + 1) as u32;
                }

                // Sequential pattern
                if let Some(stages) = metadata_obj.get("pipeline_stages").and_then(|v| v.as_array()) {
                    for stage in stages {
                        if let Some(agent) = stage.get("agent").and_then(|v| v.as_str()) {
                            sub_agents.push(agent.to_string());
                        }
                    }
                }

                // Parallel pattern
                if let Some(count) = metadata_obj.get("agent_count").and_then(|v| v.as_u64()) {
                    // Extract agent names if available
                    for i in 0..count {
                        sub_agents.push(format!("agent_{}", i));
                    }
                }

                // Reflection pattern
                if let Some(iterations) = metadata_obj.get("reflection_iterations").and_then(|v| v.as_u64()) {
                    turns = (iterations * 2) as u32;
                }
            }

            // Convert message to MessageData
            let message_data = MessageData {
                role: output_message.role.clone(),
                content: output_message.content_as_str().unwrap_or("").to_string(),
                metadata: output_message.metadata.clone(),
            };

            Response {
                protocol_version: PROTOCOL_VERSION.to_string(),
                request_id: request_id.to_string(),
                status: "success".to_string(),
                result: Some(serde_json::json!(TestResult {
                    output: TestOutput {
                        message: message_data,
                        behavior: BehaviorInfo {
                            turns,
                            tool_calls,
                            sub_agents,
                        },
                    },
                    execution_info: ExecutionInfo {
                        duration_ms,
                        llm_calls: 0,
                        tokens_used: 0,
                    },
                })),
                error: None,
            }
        }
        Err(e) => Response {
            protocol_version: PROTOCOL_VERSION.to_string(),
            request_id: request_id.to_string(),
            status: "error".to_string(),
            result: None,
            error: Some(ErrorInfo {
                error_type: "ExecutionError".to_string(),
                message: e.to_string(),
                details: HashMap::new(),
            }),
        },
    }
}

/// Execute a specific pattern
async fn execute_pattern(
    pattern: &str,
    message: Message,
    config: HashMap<String, serde_json::Value>,
) -> Result<Message, AgentError> {
    match pattern {
        "Reflection" => {
            let mock_agent = MockAgent::new();
            let max_iterations = config
                .get("max_iterations")
                .and_then(|v| v.as_u64())
                .unwrap_or(3) as usize;

            let reflection_config = ReflectionConfig {
                generator: std::sync::Arc::new(mock_agent.clone()),
                critic: std::sync::Arc::new(mock_agent),
                max_iterations,
                quality_threshold: 0.9,
                improvement_threshold: 0.05,
                critique_format: agenkit::patterns::CritiqueFormat::Structured,
                verbose: false,
            };

            let agent = ReflectionAgent::new(reflection_config)?;
            agent.process(message).await
        }
        "Sequential" => {
            // Get agent config
            let agent_configs = config.get("agents").and_then(|v| v.as_array());
            let agents: Vec<std::sync::Arc<dyn Agent>> = if let Some(configs) = agent_configs {
                configs
                    .iter()
                    .filter_map(|cfg| {
                        cfg.get("name")
                            .and_then(|n| n.as_str())
                            .map(|name| std::sync::Arc::new(MockAgent::with_name(name)) as std::sync::Arc<dyn Agent>)
                    })
                    .collect()
            } else {
                vec![
                    std::sync::Arc::new(MockAgent::with_name("agent1")),
                    std::sync::Arc::new(MockAgent::with_name("agent2")),
                ]
            };

            let agent = SequentialAgent::new(agents)?;
            agent.process(message).await
        }
        "Parallel" => {
            // Get agent config
            let agent_configs = config.get("agents").and_then(|v| v.as_array());
            let agents: Vec<std::sync::Arc<dyn Agent>> = if let Some(configs) = agent_configs {
                configs
                    .iter()
                    .filter_map(|cfg| {
                        cfg.get("name")
                            .and_then(|n| n.as_str())
                            .map(|name| std::sync::Arc::new(MockAgent::with_name(name)) as std::sync::Arc<dyn Agent>)
                    })
                    .collect()
            } else {
                vec![
                    std::sync::Arc::new(MockAgent::with_name("agent1")),
                    std::sync::Arc::new(MockAgent::with_name("agent2")),
                ]
            };

            // Simple aggregator function that combines messages
            fn simple_aggregator(messages: &[Message]) -> Message {
                if messages.is_empty() {
                    return Message::with_text("assistant", "No results");
                }
                let combined_content = messages
                    .iter()
                    .map(|m| m.content_as_str().unwrap_or(""))
                    .collect::<Vec<_>>()
                    .join(" ");
                let mut result = Message::with_text("assistant", combined_content);
                result
                    .metadata
                    .insert("aggregated".to_string(), serde_json::json!(true));
                result
            }

            let agent = ParallelAgent::new(agents, simple_aggregator)?;
            agent.process(message).await
        }
        "ReAct" => {
            let mock_agent = MockAgent::new();
            let max_steps = config
                .get("max_iterations")
                .and_then(|v| v.as_u64())
                .unwrap_or(5) as usize;

            // Create mock tools
            let tools: Vec<std::sync::Arc<dyn agenkit::core::Tool>> = if let Some(tools_config) = config.get("tools").and_then(|v| v.as_array()) {
                tools_config
                    .iter()
                    .filter_map(|t| t.get("name").and_then(|n| n.as_str()))
                    .map(|name| create_mock_tool(name))
                    .collect()
            } else {
                vec![]
            };

            let react_config = ReActConfig {
                agent: std::sync::Arc::new(mock_agent),
                tools,
                max_steps,
                verbose: false,
                prompt_template: None,
            };

            let agent = ReActAgent::new(react_config)?;
            agent.process(message).await
        }
        "Conversational" => {
            let mock_agent = MockAgent::new();
            let max_history = config
                .get("max_history")
                .and_then(|v| v.as_u64())
                .unwrap_or(10) as usize;

            let conv_config = agenkit::patterns::ConversationalConfig {
                llm: std::sync::Arc::new(mock_agent),
                max_history,
                system_prompt: None,
                include_system: true,
            };

            let agent = ConversationalAgent::new(conv_config)?;
            agent.process(message).await
        }
        "Task" => {
            let mock_agent = MockAgent::new();
            let retries = config
                .get("retries")
                .and_then(|v| v.as_u64())
                .unwrap_or(0) as usize;

            let task_config = TaskConfig {
                timeout: None,
                retries,
            };

            let task = Task::new(std::sync::Arc::new(mock_agent), task_config);
            task.execute(message).await
        }
        _ => Err(AgentError::ProcessingError(format!(
            "Pattern '{}' not implemented in Rust harness",
            pattern
        ))),
    }
}

/// Create a mock tool for testing
fn create_mock_tool(name: &str) -> std::sync::Arc<dyn agenkit::core::Tool> {
    struct MockTool {
        name: String,
        description: String,
    }

    #[async_trait]
    impl agenkit::core::Tool for MockTool {
        fn name(&self) -> &str {
            &self.name
        }

        fn description(&self) -> &str {
            &self.description
        }

        async fn execute(
            &self,
            _params: HashMap<String, serde_json::Value>,
        ) -> Result<agenkit::core::ToolResult, AgentError> {
            let result = match self.name.as_str() {
                "calculator" => agenkit::core::ToolResult {
                    output: serde_json::json!("360"),
                    success: true,
                    error: None,
                    metadata: HashMap::new(),
                },
                "search" => agenkit::core::ToolResult {
                    output: serde_json::json!("Temperature in Paris: 20°C"),
                    success: true,
                    error: None,
                    metadata: HashMap::new(),
                },
                "unit_converter" => agenkit::core::ToolResult {
                    output: serde_json::json!("68°F"),
                    success: true,
                    error: None,
                    metadata: HashMap::new(),
                },
                _ => agenkit::core::ToolResult {
                    output: serde_json::json!("mock result"),
                    success: true,
                    error: None,
                    metadata: HashMap::new(),
                },
            };

            Ok(result)
        }
    }

    std::sync::Arc::new(MockTool {
        name: name.to_string(),
        description: format!("Mock {} tool", name),
    })
}

/// Handle a request and generate a response
async fn handle_request(request: Request) -> Response {
    // Validate protocol version
    if request.protocol_version != PROTOCOL_VERSION {
        return Response {
            protocol_version: PROTOCOL_VERSION.to_string(),
            request_id: request.request_id,
            status: "error".to_string(),
            result: None,
            error: Some(ErrorInfo {
                error_type: "ProtocolError".to_string(),
                message: format!(
                    "Protocol version mismatch: expected {}, got {}",
                    PROTOCOL_VERSION, request.protocol_version
                ),
                details: HashMap::new(),
            }),
        };
    }

    // Route command
    match request.command.as_str() {
        "health_check" => health_check(&request.request_id),
        "get_info" => get_info(&request.request_id),
        "execute_test" => execute_test(&request.request_id, request.payload).await,
        _ => Response {
            protocol_version: PROTOCOL_VERSION.to_string(),
            request_id: request.request_id,
            status: "error".to_string(),
            result: None,
            error: Some(ErrorInfo {
                error_type: "CommandNotFound".to_string(),
                message: format!("Unknown command: {}", request.command),
                details: HashMap::new(),
            }),
        },
    }
}

#[tokio::main]
async fn main() {
    // Read request from stdin
    let stdin = io::stdin();
    let mut handle = stdin.lock();
    let mut request_json = String::new();

    match handle.read_line(&mut request_json) {
        Ok(_) => {}
        Err(e) => {
            let error_response = Response {
                protocol_version: PROTOCOL_VERSION.to_string(),
                request_id: "unknown".to_string(),
                status: "error".to_string(),
                result: None,
                error: Some(ErrorInfo {
                    error_type: "IOError".to_string(),
                    message: format!("Failed to read stdin: {}", e),
                    details: HashMap::new(),
                }),
            };
            println!("{}", serde_json::to_string(&error_response).unwrap());
            std::process::exit(4);
        }
    }

    // Parse request
    let request: Request = match serde_json::from_str(&request_json) {
        Ok(r) => r,
        Err(e) => {
            let error_response = Response {
                protocol_version: PROTOCOL_VERSION.to_string(),
                request_id: "unknown".to_string(),
                status: "error".to_string(),
                result: None,
                error: Some(ErrorInfo {
                    error_type: "ProtocolError".to_string(),
                    message: format!("Invalid JSON: {}", e),
                    details: HashMap::new(),
                }),
            };
            println!("{}", serde_json::to_string(&error_response).unwrap());
            std::process::exit(2);
        }
    };

    // Handle request
    let response = handle_request(request).await;

    // Write response to stdout
    match serde_json::to_string(&response) {
        Ok(json) => {
            println!("{}", json);
            std::process::exit(if response.status == "success" { 0 } else { 1 });
        }
        Err(e) => {
            let error_response = Response {
                protocol_version: PROTOCOL_VERSION.to_string(),
                request_id: response.request_id,
                status: "error".to_string(),
                result: None,
                error: Some(ErrorInfo {
                    error_type: "SerializationError".to_string(),
                    message: format!("Failed to serialize response: {}", e),
                    details: HashMap::new(),
                }),
            };
            println!("{}", serde_json::to_string(&error_response).unwrap());
            std::process::exit(4);
        }
    }
}
