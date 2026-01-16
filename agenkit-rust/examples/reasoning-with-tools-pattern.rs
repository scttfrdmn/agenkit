//! Reasoning with Tools Pattern Example
//!
//! Demonstrates interleaved reasoning and tool usage where tools are called
//! DURING the thinking process, not just after reasoning completes.
//!
//! Inspired by Claude 4 and o3's extended thinking capabilities.

use agenkit::core::{Agent, AgentError, Message, Tool, ToolResult};
use agenkit::patterns::{ReasoningWithToolsAgent, ReasoningWithToolsConfig};
use async_trait::async_trait;
use std::collections::HashMap;
use std::sync::Arc;

/// Mock LLM that simulates reasoning and tool calls
struct MockReasoningLLM {
    responses: Vec<String>,
    current: std::sync::Mutex<usize>,
}

impl MockReasoningLLM {
    fn new(responses: Vec<String>) -> Self {
        Self {
            responses,
            current: std::sync::Mutex::new(0),
        }
    }
}

#[async_trait]
impl Agent for MockReasoningLLM {
    fn name(&self) -> &str {
        "mock-reasoning-llm"
    }

    async fn process(&self, _message: Message) -> Result<Message, AgentError> {
        let mut idx = self.current.lock().unwrap();
        let response = if *idx < self.responses.len() {
            self.responses[*idx].clone()
        } else {
            "CONCLUSION: Done thinking".to_string()
        };
        *idx += 1;

        Ok(Message::with_text("assistant", response))
    }
}

/// Calculator tool for mathematical operations
struct CalculatorTool;

#[async_trait]
impl Tool for CalculatorTool {
    fn name(&self) -> &str {
        "calculator"
    }

    fn description(&self) -> &str {
        "Performs mathematical calculations"
    }

    async fn execute(
        &self,
        parameters: HashMap<String, serde_json::Value>,
    ) -> Result<ToolResult, AgentError> {
        let expression = parameters
            .get("expression")
            .and_then(|v| v.as_str())
            .ok_or_else(|| AgentError::InvalidInput("Missing expression".to_string()))?;

        // Simple eval for demo (in production, use proper parsing)
        let result = match expression {
            "2 + 2" => "4",
            "10 * 5" => "50",
            "100 / 4" => "25",
            "15 + 30" => "45",
            _ => "42", // Default answer
        };

        Ok(ToolResult::success(serde_json::json!(result)))
    }
}

/// Search tool for looking up information
struct SearchTool;

#[async_trait]
impl Tool for SearchTool {
    fn name(&self) -> &str {
        "search"
    }

    fn description(&self) -> &str {
        "Searches for information"
    }

    async fn execute(
        &self,
        parameters: HashMap<String, serde_json::Value>,
    ) -> Result<ToolResult, AgentError> {
        let query = parameters
            .get("query")
            .and_then(|v| v.as_str())
            .ok_or_else(|| AgentError::InvalidInput("Missing query".to_string()))?;

        let result = format!("Search results for: {}", query);
        Ok(ToolResult::success(serde_json::json!(result)))
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("=== Reasoning with Tools Pattern Examples ===\n");

    // Scenario 1: Basic Reasoning with Tool
    println!("--- Scenario 1: Basic Interleaved Reasoning ---");

    let llm = Arc::new(MockReasoningLLM::new(vec![
        "Let me think about this problem... I need to calculate 2 + 2.".to_string(),
        "TOOL_CALL: calculator\nPARAMETERS: {\"expression\": \"2 + 2\"}".to_string(),
        "The calculator returned 4. CONCLUSION: The answer is 4".to_string(),
    ]));

    let tools: Vec<Arc<dyn Tool>> = vec![Arc::new(CalculatorTool)];
    let config = ReasoningWithToolsConfig {
        max_reasoning_steps: 10,
        enable_trace: true,
        ..Default::default()
    };

    let agent = ReasoningWithToolsAgent::new(llm.clone(), tools, config);
    let message = Message::with_text("user", "What is 2 + 2?");
    let result = agent.process(message).await?;

    println!("Question: What is 2 + 2?");
    println!("Answer: {:?}", result.content);
    println!("✓ Tool was called DURING reasoning, not after\n");

    // Scenario 2: Multiple Tools
    println!("--- Scenario 2: Multiple Tool Usage ---");

    let llm = Arc::new(MockReasoningLLM::new(vec![
        "I need to search first.".to_string(),
        "TOOL_CALL: search\nPARAMETERS: {\"query\": \"Rust programming\"}".to_string(),
        "Good, now let me calculate something.".to_string(),
        "TOOL_CALL: calculator\nPARAMETERS: {\"expression\": \"15 + 30\"}".to_string(),
        "CONCLUSION: Search found info, calculation gives 45".to_string(),
    ]));

    let tools: Vec<Arc<dyn Tool>> = vec![Arc::new(CalculatorTool), Arc::new(SearchTool)];
    let config = ReasoningWithToolsConfig {
        max_reasoning_steps: 10,
        enable_trace: true,
        ..Default::default()
    };

    let agent = ReasoningWithToolsAgent::new(llm.clone(), tools, config);
    let message = Message::with_text("user", "Search for Rust and calculate 15 + 30");
    let result = agent.process(message).await?;

    println!("Question: Search for Rust and calculate 15 + 30");
    println!("Tools used: search, calculator");
    println!("Answer: {:?}", result.content);
    println!("✓ Multiple tools orchestrated through reasoning\n");

    // Scenario 3: Extended Thinking
    println!("--- Scenario 3: Extended Thinking Process ---");

    let llm = Arc::new(MockReasoningLLM::new(vec![
        "This is a complex problem. Let me break it down.".to_string(),
        "First, I need to calculate 10 * 5.".to_string(),
        "TOOL_CALL: calculator\nPARAMETERS: {\"expression\": \"10 * 5\"}".to_string(),
        "Good, that's 50. Now I need to think about the next step.".to_string(),
        "Let me verify with another calculation.".to_string(),
        "TOOL_CALL: calculator\nPARAMETERS: {\"expression\": \"100 / 4\"}".to_string(),
        "Perfect, that confirms my hypothesis.".to_string(),
        "CONCLUSION: The results are 50 and 25".to_string(),
    ]));

    let tools: Vec<Arc<dyn Tool>> = vec![Arc::new(CalculatorTool)];
    let config = ReasoningWithToolsConfig {
        max_reasoning_steps: 15,
        enable_trace: true,
        ..Default::default()
    };

    let agent = ReasoningWithToolsAgent::new(llm.clone(), tools, config);
    let message = Message::with_text("user", "Calculate 10 * 5 and 100 / 4");
    let result = agent.process(message).await?;

    println!("Question: Calculate 10 * 5 and 100 / 4");
    println!("Steps taken: Multiple reasoning steps with tool calls");
    println!("Answer: {:?}", result.content);

    if let Some(trace_json) = result.metadata.get("reasoning_trace") {
        println!("✓ Reasoning trace captured:");
        println!("  - Thinking steps");
        println!("  - Tool calls with parameters");
        println!("  - Tool results");
        println!("  - Full observability\n");
    }

    // Scenario 4: Tool Chaining
    println!("--- Scenario 4: Sequential Tool Usage ---");

    let llm = Arc::new(MockReasoningLLM::new(vec![
        "Step 1: Search for information.".to_string(),
        "TOOL_CALL: search\nPARAMETERS: {\"query\": \"population\"}".to_string(),
        "Step 2: Calculate based on results.".to_string(),
        "TOOL_CALL: calculator\nPARAMETERS: {\"expression\": \"10 * 5\"}".to_string(),
        "Step 3: Final analysis.".to_string(),
        "CONCLUSION: Population is 50 million".to_string(),
    ]));

    let tools: Vec<Arc<dyn Tool>> = vec![Arc::new(CalculatorTool), Arc::new(SearchTool)];
    let config = ReasoningWithToolsConfig {
        max_reasoning_steps: 10,
        enable_trace: true,
        ..Default::default()
    };

    let agent = ReasoningWithToolsAgent::new(llm.clone(), tools, config);
    let message = Message::with_text("user", "Find population and calculate");
    let result = agent.process(message).await?;

    println!("Question: Find population and calculate");
    println!("Process:");
    println!("  1. Reasoning → Search tool");
    println!("  2. Reasoning → Calculator tool");
    println!("  3. Reasoning → Conclusion");
    println!("✓ Tools used sequentially with reasoning between each\n");

    // Scenario 5: Max Steps Limit
    println!("--- Scenario 5: Max Steps Limit ---");

    let mut long_responses = Vec::new();
    for i in 1..=15 {
        long_responses.push(format!("Thinking step {}...", i));
    }
    long_responses.push("CONCLUSION: Done".to_string());

    let llm = Arc::new(MockReasoningLLM::new(long_responses));
    let tools: Vec<Arc<dyn Tool>> = vec![];
    let config = ReasoningWithToolsConfig {
        max_reasoning_steps: 5, // Max 5 steps
        enable_trace: false,
        ..Default::default()
    };

    let agent = ReasoningWithToolsAgent::new(llm.clone(), tools, config);
    let message = Message::with_text("user", "Think deeply");
    let result = agent.process(message).await?;

    println!("Question: Think deeply");
    println!("Max reasoning steps: 5");
    println!("Answer: {:?}", result.content);
    println!("✓ Reasoning terminated at max steps to prevent infinite loops\n");

    println!("=== All Reasoning with Tools Examples Complete! ===");
    println!("\nKey Takeaways:");
    println!("1. Tools called DURING reasoning, not just after");
    println!("2. Multiple reasoning steps before and after tool use");
    println!("3. Full observability with reasoning traces");
    println!("4. Support for multiple tools in one reasoning session");
    println!("5. Sequential tool chaining with reasoning between");
    println!("6. Max steps limit prevents infinite loops");
    println!("7. Suitable for complex, multi-step problem solving");
    println!("\nInspired by:");
    println!("- Claude 4's extended thinking");
    println!("- o3's reasoning capabilities");
    println!("- Chain-of-thought prompting");

    Ok(())
}
