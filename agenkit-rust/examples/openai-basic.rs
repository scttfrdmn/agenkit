//! Basic OpenAI adapter example.
//!
//! Demonstrates:
//! - Simple text completion with GPT models
//! - Model comparison (GPT-4 vs GPT-3.5)
//! - Temperature effects on creativity
//! - Error handling and metadata extraction
//!
//! Setup:
//!   export OPENAI_API_KEY=your-key
//!   cargo run --example openai_basic --features native

use agenkit::adapters::openai::{OpenAIAgent, OpenAIConfig};
use agenkit::core::{Agent, Message};

fn print_separator(title: &str) {
    println!("\n{}\n{}\n{}\n", "=".repeat(60), title, "=".repeat(60));
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    print_separator("AgentKit Rust - OpenAI Basic Example");

    let api_key = std::env::var("OPENAI_API_KEY")
        .expect("OPENAI_API_KEY environment variable not set");

    // Example 1: Simple completion
    print_separator("Example 1: Simple Completion with GPT-4 Turbo");

    let config = OpenAIConfig {
        api_key: api_key.clone(),
        model: "gpt-4-turbo".to_string(),
        temperature: 0.7,
        max_tokens: 150,
        ..Default::default()
    };

    let agent = OpenAIAgent::new(config);

    let msg = Message::with_text("user", "Explain recursion in programming in 2 sentences.");
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

    // Example 2: Model comparison
    print_separator("Example 2: Model Comparison (GPT-4 vs GPT-3.5)");

    let prompt = "What are the key differences between Rust and C++?";
    println!("Prompt: {}\n", prompt);

    // GPT-4 Turbo
    println!("GPT-4 Turbo Response:");
    let gpt4_config = OpenAIConfig {
        api_key: api_key.clone(),
        model: "gpt-4-turbo".to_string(),
        temperature: 0.7,
        max_tokens: 200,
        ..Default::default()
    };
    let gpt4 = OpenAIAgent::new(gpt4_config);
    let msg = Message::with_text("user", prompt);

    match gpt4.process(msg).await {
        Ok(response) => {
            println!("{}", response.content_as_str().unwrap_or(""));
            if let Some(usage) = response.metadata.get("usage") {
                println!("Tokens: {}", usage);
            }
        }
        Err(e) => eprintln!("Error: {}", e),
    }

    println!("\n{}\n", "-".repeat(60));

    // GPT-3.5 Turbo
    println!("GPT-3.5 Turbo Response:");
    let gpt35_config = OpenAIConfig {
        api_key: api_key.clone(),
        model: "gpt-3.5-turbo".to_string(),
        temperature: 0.7,
        max_tokens: 200,
        ..Default::default()
    };
    let gpt35 = OpenAIAgent::new(gpt35_config);
    let msg = Message::with_text("user", prompt);

    match gpt35.process(msg).await {
        Ok(response) => {
            println!("{}", response.content_as_str().unwrap_or(""));
            if let Some(usage) = response.metadata.get("usage") {
                println!("Tokens: {}", usage);
            }
        }
        Err(e) => eprintln!("Error: {}", e),
    }

    // Example 3: Temperature effects
    print_separator("Example 3: Temperature Effects on Creativity");

    let creative_prompt = "Write a creative opening line for a science fiction story.";
    println!("Prompt: {}\n", creative_prompt);

    // Low temperature (focused)
    println!("Low Temperature (0.2) - Focused:");
    let low_temp_config = OpenAIConfig {
        api_key: api_key.clone(),
        model: "gpt-4-turbo".to_string(),
        temperature: 0.2,
        max_tokens: 100,
        ..Default::default()
    };
    let low_temp = OpenAIAgent::new(low_temp_config);
    let msg = Message::with_text("user", creative_prompt);

    match low_temp.process(msg).await {
        Ok(response) => println!("{}", response.content_as_str().unwrap_or("")),
        Err(e) => eprintln!("Error: {}", e),
    }

    println!("\n{}\n", "-".repeat(60));

    // High temperature (creative)
    println!("High Temperature (0.9) - Creative:");
    let high_temp_config = OpenAIConfig {
        api_key: api_key.clone(),
        model: "gpt-4-turbo".to_string(),
        temperature: 0.9,
        max_tokens: 100,
        ..Default::default()
    };
    let high_temp = OpenAIAgent::new(high_temp_config);
    let msg = Message::with_text("user", creative_prompt);

    match high_temp.process(msg).await {
        Ok(response) => println!("{}", response.content_as_str().unwrap_or("")),
        Err(e) => eprintln!("Error: {}", e),
    }

    // Example 4: Error handling
    print_separator("Example 4: Error Handling");

    println!("Testing with invalid API key:");
    let bad_config = OpenAIConfig {
        api_key: "invalid-key".to_string(),
        model: "gpt-4-turbo".to_string(),
        ..Default::default()
    };
    let bad_agent = OpenAIAgent::new(bad_config);
    let msg = Message::with_text("user", "Hello");

    match bad_agent.process(msg).await {
        Ok(_) => println!("Unexpected success"),
        Err(e) => println!("Expected error caught: {}", e),
    }

    print_separator("✓ All OpenAI examples completed!");

    println!("Key Takeaways:");
    println!("  • GPT-4 provides more detailed and nuanced responses");
    println!("  • GPT-3.5 is faster and more cost-effective");
    println!("  • Lower temperature = more focused and deterministic");
    println!("  • Higher temperature = more creative and varied");
    println!("  • Always handle errors gracefully");
    println!("{}", "-".repeat(60));

    Ok(())
}
