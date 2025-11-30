//! ReAct Pattern Example
//!
//! Demonstrates the ReAct (Reasoning + Acting) pattern where agents reason
//! about actions and execute tools in an iterative loop.

use agenkit::core::{Agent, AgentError, Message, Tool, ToolResult};
use agenkit::patterns::{ReActAgent, ReActConfig};
use async_trait::async_trait;
use std::collections::HashMap;
use std::sync::Arc;

/// Simple calculator tool that performs basic arithmetic
struct CalculatorTool;

#[async_trait]
impl Tool for CalculatorTool {
    fn name(&self) -> &str {
        "calculator"
    }

    fn description(&self) -> &str {
        "Performs basic arithmetic calculations. Input should be an expression like '2+2' or '15% of 240'"
    }

    async fn execute(
        &self,
        params: HashMap<String, serde_json::Value>,
    ) -> Result<ToolResult, AgentError> {
        let input = params
            .get("input")
            .and_then(|v| v.as_str())
            .unwrap_or("");

        println!("   🧮 Calculator executing: {}", input);

        // Simple evaluation (in real code, use a proper expression evaluator)
        let result = if input.contains("+") {
            let parts: Vec<&str> = input.split('+').collect();
            if parts.len() == 2 {
                let a: f64 = parts[0].trim().parse().unwrap_or(0.0);
                let b: f64 = parts[1].trim().parse().unwrap_or(0.0);
                (a + b).to_string()
            } else {
                "Error: Invalid expression".to_string()
            }
        } else if input.contains("% of") || input.contains("percent of") {
            // Parse "X% of Y" or "X percent of Y"
            let cleaned = input.replace("percent", "%");
            let parts: Vec<&str> = cleaned.split("% of").collect();
            if parts.len() == 2 {
                let percent: f64 = parts[0].trim().parse().unwrap_or(0.0);
                let value: f64 = parts[1].trim().parse().unwrap_or(0.0);
                (value * percent / 100.0).to_string()
            } else {
                "Error: Invalid percentage expression".to_string()
            }
        } else if input.contains("*") {
            let parts: Vec<&str> = input.split('*').collect();
            if parts.len() == 2 {
                let a: f64 = parts[0].trim().parse().unwrap_or(0.0);
                let b: f64 = parts[1].trim().parse().unwrap_or(0.0);
                (a * b).to_string()
            } else {
                "Error: Invalid expression".to_string()
            }
        } else {
            "Error: Unsupported operation".to_string()
        };

        Ok(ToolResult {
            output: serde_json::json!(result),
            success: !result.starts_with("Error"),
            error: if result.starts_with("Error") {
                Some(result)
            } else {
                None
            },
            metadata: HashMap::new(),
        })
    }
}

/// Search tool that looks up information
struct SearchTool;

#[async_trait]
impl Tool for SearchTool {
    fn name(&self) -> &str {
        "search"
    }

    fn description(&self) -> &str {
        "Searches for information on a given topic. Input should be a search query."
    }

    async fn execute(
        &self,
        params: HashMap<String, serde_json::Value>,
    ) -> Result<ToolResult, AgentError> {
        let query = params
            .get("input")
            .and_then(|v| v.as_str())
            .unwrap_or("");

        println!("   🔍 Search executing: {}", query);

        // Simulate search results
        let result = match query.to_lowercase().as_str() {
            q if q.contains("rust") => {
                "Rust is a systems programming language focused on safety, speed, and concurrency."
            }
            q if q.contains("agenkit") => {
                "Agenkit is a cross-language AI agent framework supporting Python, Go, TypeScript, and Rust."
            }
            q if q.contains("react") || q.contains("reasoning") => {
                "ReAct combines reasoning and acting by interleaving thought processes with tool actions."
            }
            _ => "No relevant information found for this query.",
        };

        Ok(ToolResult {
            output: serde_json::json!(result),
            success: true,
            error: None,
            metadata: HashMap::new(),
        })
    }
}

/// Mock reasoning agent that simulates LLM-style responses
struct MockReasoningAgent {
    scenario: String,
}

#[async_trait]
impl Agent for MockReasoningAgent {
    fn name(&self) -> &str {
        "MockReasoning"
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let content = message.content_as_str().unwrap_or("");

        // Simulate different reasoning based on scenario
        let response = if self.scenario == "calculator" {
            if content.contains("What is 15% of 240") {
                if content.contains("Observation:") {
                    // We've seen the result, provide final answer
                    "Thought: I have the calculation result\nFinal Answer: 15% of 240 is 36"
                } else {
                    // First step - need to calculate
                    "Thought: I need to calculate 15% of 240\nAction: calculator\nAction Input: 15% of 240"
                }
            } else {
                "Thought: Unknown question\nFinal Answer: I don't know"
            }
        } else if self.scenario == "search" {
            if content.contains("What is Rust") {
                if content.contains("Observation:") {
                    // We've seen the search result
                    "Thought: I found information about Rust\nFinal Answer: Rust is a systems programming language focused on safety, speed, and concurrency."
                } else {
                    // Need to search
                    "Thought: I should search for information about Rust\nAction: search\nAction Input: Rust programming language"
                }
            } else {
                "Thought: Unknown question\nFinal Answer: I don't know"
            }
        } else if self.scenario == "multi-step" {
            if !content.contains("Observation:") {
                // First step
                "Thought: I should first search for what ReAct means\nAction: search\nAction Input: ReAct reasoning"
            } else if content.contains("ReAct combines") {
                // Second step - we have search result
                "Thought: Now I understand ReAct, let me calculate an example\nAction: calculator\nAction Input: 10 + 5"
            } else if content.contains("15") {
                // Third step - we have calculation result
                "Thought: I have both pieces of information\nFinal Answer: ReAct combines reasoning and acting. As an example, 10 + 5 = 15."
            } else {
                "Thought: Something went wrong\nFinal Answer: Unable to complete"
            }
        } else {
            "Thought: Unknown scenario\nFinal Answer: Error"
        };

        Ok(Message::with_text("assistant", response))
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("🎭 ReAct Pattern Example\n");

    // Example 1: Simple calculation with ReAct
    println!("{}", "=".repeat(60));
    println!("📋 Example 1: Simple Calculation");
    println!("{}", "=".repeat(60));

    let reasoning_agent = Arc::new(MockReasoningAgent {
        scenario: "calculator".to_string(),
    });
    let calculator = Arc::new(CalculatorTool) as Arc<dyn Tool>;

    let config = ReActConfig {
        agent: reasoning_agent,
        tools: vec![calculator],
        max_steps: 5,
        verbose: true,
        prompt_template: None,
    };

    let react_agent = ReActAgent::new(config)?;

    println!("\n➡️  Query: What is 15% of 240?");
    let message = Message::with_text("user", "What is 15% of 240?");
    let result = react_agent.process(message).await?;

    println!("\n✅ Result:");
    println!("{}", result.content_as_str().unwrap_or(""));

    // Example 2: Information search with ReAct
    println!("\n\n{}", "=".repeat(60));
    println!("📋 Example 2: Information Search");
    println!("{}", "=".repeat(60));

    let reasoning_agent2 = Arc::new(MockReasoningAgent {
        scenario: "search".to_string(),
    });
    let search = Arc::new(SearchTool) as Arc<dyn Tool>;

    let config2 = ReActConfig {
        agent: reasoning_agent2,
        tools: vec![search],
        max_steps: 5,
        verbose: true,
        prompt_template: None,
    };

    let react_agent2 = ReActAgent::new(config2)?;

    println!("\n➡️  Query: What is Rust?");
    let message2 = Message::with_text("user", "What is Rust?");
    let result2 = react_agent2.process(message2).await?;

    println!("\n✅ Result:");
    println!("{}", result2.content_as_str().unwrap_or(""));

    // Example 3: Multi-step reasoning with multiple tools
    println!("\n\n{}", "=".repeat(60));
    println!("📋 Example 3: Multi-Step Reasoning");
    println!("{}", "=".repeat(60));

    let reasoning_agent3 = Arc::new(MockReasoningAgent {
        scenario: "multi-step".to_string(),
    });
    let calculator3 = Arc::new(CalculatorTool) as Arc<dyn Tool>;
    let search3 = Arc::new(SearchTool) as Arc<dyn Tool>;

    let config3 = ReActConfig {
        agent: reasoning_agent3,
        tools: vec![calculator3, search3],
        max_steps: 10,
        verbose: true,
        prompt_template: None,
    };

    let react_agent3 = ReActAgent::new(config3)?;

    println!("\n➡️  Query: Explain ReAct and show a calculation example");
    let message3 = Message::with_text("user", "Explain ReAct and show a calculation example");
    let result3 = react_agent3.process(message3).await?;

    println!("\n✅ Result:");
    println!("{}", result3.content_as_str().unwrap_or(""));

    println!("\n✨ ReAct pattern examples complete!\n");
    println!("💡 Key takeaways:");
    println!("   - ReAct combines reasoning (thought) with acting (tool use)");
    println!("   - Agent iterates: Thought → Action → Observation → repeat");
    println!("   - Tools extend agent capabilities beyond pure language");
    println!("   - Transparent reasoning process visible in verbose mode");

    Ok(())
}
