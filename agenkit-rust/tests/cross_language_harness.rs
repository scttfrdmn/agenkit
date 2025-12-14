//! Rust test harness for cross-language equivalence testing.
//!
//! Implements the JSON protocol for executing pattern tests.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::io::{self, Read, Write};
use std::process;
use std::time::Instant;

const PROTOCOL_VERSION: &str = "1.0";
const VERSION: &str = "0.1.0";

// Exit codes
const EXIT_SUCCESS: i32 = 0;
const EXIT_ERROR: i32 = 1;
const EXIT_PROTOCOL_ERROR: i32 = 2;
const EXIT_INTERNAL_ERROR: i32 = 4;

// Protocol message structures
#[derive(Debug, Deserialize)]
struct Request {
    protocol_version: String,
    request_id: String,
    command: String,
    payload: HashMap<String, serde_json::Value>,
}

#[derive(Debug, Serialize)]
struct Response {
    protocol_version: String,
    request_id: String,
    status: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    result: Option<serde_json::Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    error: Option<ErrorInfo>,
}

#[derive(Debug, Serialize)]
struct ErrorInfo {
    r#type: String,
    message: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    details: Option<HashMap<String, serde_json::Value>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    stack_trace: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct Message {
    role: String,
    content: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    metadata: Option<HashMap<String, serde_json::Value>>,
}

#[derive(Debug, Serialize)]
struct TestOutput {
    output: OutputData,
    execution_info: ExecutionInfo,
}

#[derive(Debug, Serialize)]
struct OutputData {
    message: Message,
    behavior: BehaviorData,
}

#[derive(Debug, Serialize)]
struct BehaviorData {
    turns: u32,
    tool_calls: Vec<String>,
    sub_agents: Vec<String>,
}

#[derive(Debug, Serialize)]
struct ExecutionInfo {
    duration_ms: u64,
    llm_calls: u32,
    tokens_used: u32,
}

// Pattern registry
fn is_supported_pattern(pattern: &str) -> bool {
    matches!(
        pattern,
        "reflection"
            | "sequential"
            | "parallel"
            | "router"
            | "react"
            | "conversational"
            | "agents_as_tools"
            | "fallback"
            | "supervisor"
            | "planning"
            | "task"
            | "collaborative"
            | "human_in_loop"
            | "autonomous"
            | "multiagent"
            | "orchestration"
            | "memory"
            | "reasoning_with_tools"
    )
}

fn main() {
    // Read request from stdin
    let mut buffer = String::new();
    if let Err(e) = io::stdin().read_to_string(&mut buffer) {
        write_error_response(
            "",
            "InternalError",
            &format!("Failed to read stdin: {}", e),
            EXIT_INTERNAL_ERROR,
        );
    }

    // Parse request
    let request: Request = match serde_json::from_str(&buffer) {
        Ok(req) => req,
        Err(e) => {
            write_error_response(
                "",
                "ProtocolError",
                &format!("Invalid JSON: {}", e),
                EXIT_PROTOCOL_ERROR,
            );
        }
    };

    // Handle request
    let response = handle_request(&request);

    // Write response
    let response_json = match serde_json::to_string(&response) {
        Ok(json) => json,
        Err(e) => {
            write_error_response(
                &request.request_id,
                "InternalError",
                &format!("Failed to marshal response: {}", e),
                EXIT_INTERNAL_ERROR,
            );
        }
    };

    println!("{}", response_json);

    // Exit with appropriate code
    let exit_code = if response.status == "success" {
        EXIT_SUCCESS
    } else {
        EXIT_ERROR
    };
    process::exit(exit_code);
}

fn handle_request(request: &Request) -> Response {
    // Validate protocol version
    if request.protocol_version != PROTOCOL_VERSION {
        return Response {
            protocol_version: PROTOCOL_VERSION.to_string(),
            request_id: request.request_id.clone(),
            status: "error".to_string(),
            result: None,
            error: Some(ErrorInfo {
                r#type: "ProtocolError".to_string(),
                message: format!(
                    "Protocol version mismatch: expected {}, got {}",
                    PROTOCOL_VERSION, request.protocol_version
                ),
                details: None,
                stack_trace: None,
            }),
        };
    }

    // Route command
    let (result, error) = match request.command.as_str() {
        "execute_test" => execute_test(&request.payload),
        "get_info" => (Some(get_info()), None),
        "health_check" => (Some(health_check()), None),
        _ => (
            None,
            Some(ErrorInfo {
                r#type: "CommandNotFound".to_string(),
                message: format!("Unknown command: {}", request.command),
                details: None,
                stack_trace: None,
            }),
        ),
    };

    // Build response
    Response {
        protocol_version: PROTOCOL_VERSION.to_string(),
        request_id: request.request_id.clone(),
        status: if error.is_some() {
            "error".to_string()
        } else {
            "success".to_string()
        },
        result,
        error,
    }
}

fn execute_test(
    payload: &HashMap<String, serde_json::Value>,
) -> (Option<serde_json::Value>, Option<ErrorInfo>) {
    // Parse test payload
    let pattern = match payload.get("pattern").and_then(|v| v.as_str()) {
        Some(p) => p,
        None => {
            return (
                None,
                Some(ErrorInfo {
                    r#type: "ValidationError".to_string(),
                    message: "Pattern name is required".to_string(),
                    details: None,
                    stack_trace: None,
                }),
            );
        }
    };

    // Normalize pattern name to lowercase for case-insensitive matching
    let pattern_lower = pattern.to_lowercase();

    // Check scenario_id
    if payload.get("scenario_id").and_then(|v| v.as_str()).is_none() {
        return (
            None,
            Some(ErrorInfo {
                r#type: "ValidationError".to_string(),
                message: "Scenario ID is required".to_string(),
                details: None,
                stack_trace: None,
            }),
        );
    }

    // Check input
    let input = match payload.get("input") {
        Some(v) if v.is_object() => v,
        _ => {
            return (
                None,
                Some(ErrorInfo {
                    r#type: "ValidationError".to_string(),
                    message: "Input is required".to_string(),
                    details: None,
                    stack_trace: None,
                }),
            );
        }
    };

    // Check if pattern is supported
    if !is_supported_pattern(&pattern_lower) {
        return (
            None,
            Some(ErrorInfo {
                r#type: "PatternNotFound".to_string(),
                message: format!("Pattern '{}' not implemented in Rust harness", pattern),
                details: None,
                stack_trace: None,
            }),
        );
    }

    // Parse input message
    let message_data = match input.get("message") {
        Some(v) if v.is_object() => v,
        _ => {
            return (
                None,
                Some(ErrorInfo {
                    r#type: "ValidationError".to_string(),
                    message: "Input message is required".to_string(),
                    details: None,
                    stack_trace: None,
                }),
            );
        }
    };

    let message = Message {
        role: message_data
            .get("role")
            .and_then(|v| v.as_str())
            .unwrap_or("user")
            .to_string(),
        content: message_data
            .get("content")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string(),
        metadata: message_data
            .get("metadata")
            .and_then(|v| v.as_object())
            .map(|obj| {
                obj.iter()
                    .map(|(k, v)| (k.clone(), v.clone()))
                    .collect()
            }),
    };

    // Get configuration
    let config = input
        .get("config")
        .and_then(|v| v.as_object())
        .cloned()
        .unwrap_or_default();

    // Execute pattern
    let start_time = Instant::now();
    let output_message = execute_pattern(&pattern_lower, &message, &config);
    let duration = start_time.elapsed();

    // Build test output
    let output = TestOutput {
        output: OutputData {
            message: output_message,
            behavior: BehaviorData {
                turns: 1, // TODO: Track actual turns
                tool_calls: vec![],
                sub_agents: vec![],
            },
        },
        execution_info: ExecutionInfo {
            duration_ms: duration.as_millis() as u64,
            llm_calls: 0, // TODO: Track actual LLM calls
            tokens_used: 0, // TODO: Track actual token usage
        },
    };

    match serde_json::to_value(output) {
        Ok(v) => (Some(v), None),
        Err(e) => (
            None,
            Some(ErrorInfo {
                r#type: "InternalError".to_string(),
                message: format!("Failed to serialize output: {}", e),
                details: None,
                stack_trace: None,
            }),
        ),
    }
}

fn execute_pattern(
    pattern_name: &str,
    message: &Message,
    config: &serde_json::Map<String, serde_json::Value>,
) -> Message {
    // This is a simplified implementation that returns mock responses
    // TODO: Implement actual pattern execution based on pattern_name and config

    match pattern_name {
        "reflection" => execute_reflection(message, config),
        "sequential" => execute_sequential(message, config),
        "parallel" => execute_parallel(message, config),
        _ => {
            // Mock response for now
            let mut metadata = HashMap::new();
            metadata.insert(
                "pattern".to_string(),
                serde_json::Value::String(pattern_name.to_string()),
            );
            metadata.insert("mock".to_string(), serde_json::Value::Bool(true));

            Message {
                role: "assistant".to_string(),
                content: format!("Mock response for {} pattern", pattern_name),
                metadata: Some(metadata),
            }
        }
    }
}

fn execute_reflection(
    message: &Message,
    config: &serde_json::Map<String, serde_json::Value>,
) -> Message {
    // TODO: Implement actual reflection pattern execution
    // For now, return a mock response

    let max_iterations = config
        .get("max_iterations")
        .and_then(|v| v.as_i64())
        .unwrap_or(3);

    let mut metadata = HashMap::new();
    metadata.insert("iterations".to_string(), serde_json::Value::Number(1.into()));
    metadata.insert("improved".to_string(), serde_json::Value::Bool(true));
    metadata.insert(
        "max_iterations".to_string(),
        serde_json::Value::Number(max_iterations.into()),
    );

    Message {
        role: "assistant".to_string(),
        content: format!("Reflected response to: {}", message.content),
        metadata: Some(metadata),
    }
}

fn execute_sequential(
    message: &Message,
    config: &serde_json::Map<String, serde_json::Value>,
) -> Message {
    // TODO: Implement actual sequential pattern execution
    let agent_count = config
        .get("agents")
        .and_then(|v| v.as_array())
        .map(|a| a.len())
        .unwrap_or(0);

    let mut metadata = HashMap::new();
    metadata.insert(
        "agent_count".to_string(),
        serde_json::Value::Number(agent_count.into()),
    );

    Message {
        role: "assistant".to_string(),
        content: format!("Sequential result: {}", message.content),
        metadata: Some(metadata),
    }
}

fn execute_parallel(
    message: &Message,
    config: &serde_json::Map<String, serde_json::Value>,
) -> Message {
    // TODO: Implement actual parallel pattern execution
    let agent_count = config
        .get("agents")
        .and_then(|v| v.as_array())
        .map(|a| a.len())
        .unwrap_or(0);

    let mut metadata = HashMap::new();
    metadata.insert(
        "agent_count".to_string(),
        serde_json::Value::Number(agent_count.into()),
    );

    Message {
        role: "assistant".to_string(),
        content: format!("Parallel result: {}", message.content),
        metadata: Some(metadata),
    }
}

fn get_info() -> serde_json::Value {
    serde_json::json!({
        "language": "rust",
        "version": VERSION,
        "patterns_supported": [
            "reflection",
            "sequential",
            "parallel",
            "router",
            "react",
            "conversational",
            "agents_as_tools",
            "fallback",
            "supervisor",
            "planning",
            "task",
            "collaborative",
            "human_in_loop",
            "autonomous",
            "multiagent",
            "orchestration",
            "memory",
            "reasoning_with_tools"
        ],
        "capabilities": {
            "streaming": true,
            "async": true,
            "llm_providers": ["openai", "anthropic"]
        }
    })
}

fn health_check() -> serde_json::Value {
    serde_json::json!({
        "healthy": true,
        "uptime_seconds": 0.0
    })
}

fn write_error_response(request_id: &str, error_type: &str, message: &str, exit_code: i32) -> ! {
    let response = Response {
        protocol_version: PROTOCOL_VERSION.to_string(),
        request_id: request_id.to_string(),
        status: "error".to_string(),
        result: None,
        error: Some(ErrorInfo {
            r#type: error_type.to_string(),
            message: message.to_string(),
            details: None,
            stack_trace: None,
        }),
    };

    if let Ok(json) = serde_json::to_string(&response) {
        println!("{}", json);
    }

    process::exit(exit_code);
}
