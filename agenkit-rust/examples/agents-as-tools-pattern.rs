//! Agents-as-Tools Pattern Example
//!
//! Demonstrates wrapping specialist agents as tools that can be called by other agents.

use agenkit::core::{Agent, AgentError, Message, Tool};
use agenkit::patterns::agent_as_tool;
use async_trait::async_trait;
use std::collections::HashMap;
use std::sync::Arc;

/// Specialist agent for code-related tasks
struct CodeSpecialist;

#[async_trait]
impl Agent for CodeSpecialist {
    fn name(&self) -> &str {
        "CodeSpecialist"
    }

    fn capabilities(&self) -> Vec<String> {
        vec!["coding".to_string(), "debugging".to_string()]
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let query = message.content_as_str().unwrap_or("");
        let response = format!(
            "🔧 Code Specialist Analysis:\n\
             Task: {}\n\
             \n\
             Suggested implementation:\n\
             ```rust\n\
             fn solution() {{\n\
                 // Implementation here\n\
                 println!(\"Solving: {}\");\n\
             }}\n\
             ```",
            query, query
        );
        Ok(Message::with_text("assistant", response))
    }
}

/// Specialist agent for data analysis
struct DataSpecialist;

#[async_trait]
impl Agent for DataSpecialist {
    fn name(&self) -> &str {
        "DataSpecialist"
    }

    fn capabilities(&self) -> Vec<String> {
        vec!["data_analysis".to_string(), "sql".to_string()]
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let query = message.content_as_str().unwrap_or("");
        let response = format!(
            "📊 Data Specialist Analysis:\n\
             Task: {}\n\
             \n\
             Recommended approach:\n\
             1. Load and clean data\n\
             2. Exploratory analysis\n\
             3. Statistical modeling\n\
             4. Visualization",
            query
        );
        Ok(Message::with_text("assistant", response))
    }
}

/// Specialist agent for writing and documentation
struct WritingSpecialist;

#[async_trait]
impl Agent for WritingSpecialist {
    fn name(&self) -> &str {
        "WritingSpecialist"
    }

    fn capabilities(&self) -> Vec<String> {
        vec!["writing".to_string(), "documentation".to_string()]
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let query = message.content_as_str().unwrap_or("");
        let response = format!(
            "✍️  Writing Specialist Analysis:\n\
             Task: {}\n\
             \n\
             Document structure:\n\
             # Introduction\n\
             - Overview and context\n\
             \n\
             # Main Content\n\
             - Detailed information\n\
             \n\
             # Conclusion\n\
             - Summary and next steps",
            query
        );
        Ok(Message::with_text("assistant", response))
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("🛠️  Agents-as-Tools Pattern Example\n");

    // Create specialist agents
    let code_agent = Arc::new(CodeSpecialist);
    let data_agent = Arc::new(DataSpecialist);
    let writing_agent = Arc::new(WritingSpecialist);

    // Wrap agents as tools
    let code_tool = agent_as_tool(
        code_agent,
        "code_specialist",
        "Expert in programming, code review, and debugging. Use for code-related tasks.",
    )?;

    let data_tool = agent_as_tool(
        data_agent,
        "data_specialist",
        "Expert in data analysis, SQL, and visualization. Use for data-related tasks.",
    )?;

    let writing_tool = agent_as_tool(
        writing_agent,
        "writing_specialist",
        "Expert in writing and documentation. Use for content creation tasks.",
    )?;

    // Demonstrate using tools
    println!("📋 Available Specialist Tools:");
    println!("   1. {} - {}", code_tool.name(), code_tool.description());
    println!("   2. {} - {}", data_tool.name(), data_tool.description());
    println!(
        "   3. {} - {}",
        writing_tool.name(),
        writing_tool.description()
    );

    // Example 1: Call code specialist
    println!("\n🔹 Example 1: Code Task");
    println!("   Query: Write a function to merge two sorted arrays");

    let mut params = HashMap::new();
    params.insert(
        "query".to_string(),
        serde_json::json!("Write a function to merge two sorted arrays"),
    );

    let result = code_tool.execute(params).await?;
    println!("\n   Response:\n{}", result.output.as_str().unwrap_or(""));

    // Example 2: Call data specialist
    println!("\n🔹 Example 2: Data Task");
    println!("   Query: Analyze customer churn patterns");

    let mut params = HashMap::new();
    params.insert(
        "query".to_string(),
        serde_json::json!("Analyze customer churn patterns"),
    );

    let result = data_tool.execute(params).await?;
    println!("\n   Response:\n{}", result.output.as_str().unwrap_or(""));

    // Example 3: Call writing specialist
    println!("\n🔹 Example 3: Writing Task");
    println!("   Query: Write API documentation for a REST endpoint");

    let mut params = HashMap::new();
    params.insert(
        "query".to_string(),
        serde_json::json!("Write API documentation for a REST endpoint"),
    );

    let result = writing_tool.execute(params).await?;
    println!("\n   Response:\n{}", result.output.as_str().unwrap_or(""));

    println!("\n✨ All specialists executed successfully!");
    println!(
        "\n💡 In a real supervisor agent, these tools would be registered with a tool registry"
    );
    println!("   and the supervisor would automatically select the appropriate specialist.");

    Ok(())
}
