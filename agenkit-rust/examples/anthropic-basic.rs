//! Basic Anthropic Claude adapter example.
//!
//! Demonstrates:
//! - Simple text completion with Claude models
//! - Model comparison (Sonnet 4 vs Haiku)
//! - System prompts for role setting
//! - Metadata extraction and token usage
//!
//! Setup:
//!   export ANTHROPIC_API_KEY=your-key
//!   cargo run --example anthropic_basic --features native

use agenkit::adapters::anthropic::{AnthropicAgent, AnthropicConfig};
use agenkit::core::{Agent, Message};

fn print_separator(title: &str) {
    println!("\n{}\n{}\n{}\n", "=".repeat(60), title, "=".repeat(60));
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    print_separator("AgentKit Rust - Anthropic Claude Basic Example");

    let api_key =
        std::env::var("ANTHROPIC_API_KEY").expect("ANTHROPIC_API_KEY environment variable not set");

    // Example 1: Simple completion with Claude Sonnet 4
    print_separator("Example 1: Simple Completion with Claude Sonnet 4");

    let config = AnthropicConfig {
        api_key: api_key.clone(),
        model: "claude-sonnet-4-20250514".to_string(),
        max_tokens: 150,
        temperature: 1.0,
        ..Default::default()
    };

    let agent = AnthropicAgent::new(config);

    let msg = Message::with_text(
        "user",
        "Explain the concept of ownership in Rust in 2 sentences.",
    );
    println!("Prompt: {}", msg.content_as_str().unwrap_or(""));

    match agent.process(msg).await {
        Ok(response) => {
            println!("\nResponse:");
            println!("{}", response.content_as_str().unwrap_or(""));

            // Display metadata
            if let Some(model) = response.metadata.get("model") {
                println!("\nModel: {}", model);
            }
            if let Some(usage) = response.metadata.get("usage") {
                println!("Token usage: {}", usage);
            }
        }
        Err(e) => eprintln!("Error: {}", e),
    }

    // Example 2: System prompt for role setting
    print_separator("Example 2: Using System Prompts");

    let system_config = AnthropicConfig {
        api_key: api_key.clone(),
        model: "claude-3-5-sonnet-20241022".to_string(),
        max_tokens: 200,
        ..Default::default()
    };

    let agent = AnthropicAgent::new(system_config);

    // Claude handles system prompts separately
    let system_msg = Message::with_text(
        "system",
        "You are a helpful code reviewer. Provide concise, actionable feedback.",
    );

    println!(
        "System Prompt: {}",
        system_msg.content_as_str().unwrap_or("")
    );

    match agent.process(system_msg).await {
        Ok(response) => {
            println!("\nResponse:");
            println!("{}", response.content_as_str().unwrap_or(""));
        }
        Err(e) => eprintln!("Error: {}", e),
    }

    // Now ask a user question (in a real app, you'd maintain conversation history)
    let user_msg = Message::with_text(
        "user",
        "Review this code: fn add(a: i32, b: i32) -> i32 { a + b }",
    );

    println!("\nUser Prompt: {}", user_msg.content_as_str().unwrap_or(""));

    match agent.process(user_msg).await {
        Ok(response) => {
            println!("\nResponse:");
            println!("{}", response.content_as_str().unwrap_or(""));
        }
        Err(e) => eprintln!("Error: {}", e),
    }

    // Example 3: Model comparison (Sonnet vs Haiku)
    print_separator("Example 3: Model Comparison (Sonnet vs Haiku)");

    let prompt = "What are three key principles of good API design?";
    println!("Prompt: {}\n", prompt);

    // Claude Sonnet (more capable)
    println!("Claude 3.5 Sonnet Response:");
    let sonnet_config = AnthropicConfig {
        api_key: api_key.clone(),
        model: "claude-3-5-sonnet-20241022".to_string(),
        max_tokens: 200,
        ..Default::default()
    };
    let sonnet = AnthropicAgent::new(sonnet_config);
    let msg = Message::with_text("user", prompt);

    match sonnet.process(msg).await {
        Ok(response) => {
            println!("{}", response.content_as_str().unwrap_or(""));
            if let Some(usage) = response.metadata.get("usage") {
                println!("Tokens: {}", usage);
            }
        }
        Err(e) => eprintln!("Error: {}", e),
    }

    println!("\n{}\n", "-".repeat(60));

    // Claude Haiku (faster, cheaper)
    println!("Claude 3.5 Haiku Response:");
    let haiku_config = AnthropicConfig {
        api_key: api_key.clone(),
        model: "claude-3-5-haiku-20241022".to_string(),
        max_tokens: 200,
        ..Default::default()
    };
    let haiku = AnthropicAgent::new(haiku_config);
    let msg = Message::with_text("user", prompt);

    match haiku.process(msg).await {
        Ok(response) => {
            println!("{}", response.content_as_str().unwrap_or(""));
            if let Some(usage) = response.metadata.get("usage") {
                println!("Tokens: {}", usage);
            }
        }
        Err(e) => eprintln!("Error: {}", e),
    }

    // Example 4: Temperature effects
    print_separator("Example 4: Temperature Effects");

    let creative_prompt =
        "Generate a creative variable name for a function that calculates fibonacci numbers.";
    println!("Prompt: {}\n", creative_prompt);

    // Temperature 0.5 (balanced)
    println!("Temperature 0.5 (Balanced):");
    let balanced_config = AnthropicConfig {
        api_key: api_key.clone(),
        model: "claude-3-5-sonnet-20241022".to_string(),
        max_tokens: 100,
        temperature: 0.5,
        ..Default::default()
    };
    let balanced = AnthropicAgent::new(balanced_config);
    let msg = Message::with_text("user", creative_prompt);

    match balanced.process(msg).await {
        Ok(response) => println!("{}", response.content_as_str().unwrap_or("")),
        Err(e) => eprintln!("Error: {}", e),
    }

    println!("\n{}\n", "-".repeat(60));

    // Temperature 1.0 (more creative)
    println!("Temperature 1.0 (Creative):");
    let creative_config = AnthropicConfig {
        api_key: api_key.clone(),
        model: "claude-3-5-sonnet-20241022".to_string(),
        max_tokens: 100,
        temperature: 1.0,
        ..Default::default()
    };
    let creative = AnthropicAgent::new(creative_config);
    let msg = Message::with_text("user", creative_prompt);

    match creative.process(msg).await {
        Ok(response) => println!("{}", response.content_as_str().unwrap_or("")),
        Err(e) => eprintln!("Error: {}", e),
    }

    print_separator("✓ All Anthropic examples completed!");

    println!("Key Takeaways:");
    println!("  • Claude Sonnet 4 is the most capable model (Nov 2025)");
    println!("  • Claude Haiku is faster and more cost-effective");
    println!("  • System prompts help set the assistant's role");
    println!("  • Temperature controls response variability (0-1 range)");
    println!("  • Claude provides detailed token usage in metadata");
    println!("{}", "-".repeat(60));

    Ok(())
}
