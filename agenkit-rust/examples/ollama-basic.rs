//! Basic Ollama adapter example for local LLM inference.
//!
//! Demonstrates:
//! - Local model inference without API keys
//! - Multiple model support (Llama, Mistral, CodeLlama)
//! - Custom endpoint configuration
//! - Privacy-focused local inference
//!
//! Setup:
//!   # Install Ollama from https://ollama.ai
//!   ollama pull llama2
//!   ollama pull mistral
//!   cargo run --example ollama_basic --features native

use agenkit::adapters::ollama::{OllamaAgent, OllamaConfig};
use agenkit::core::{Agent, Message};

fn print_separator(title: &str) {
    println!("\n{}\n{}\n{}\n", "=".repeat(60), title, "=".repeat(60));
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    print_separator("AgentKit Rust - Ollama Local LLM Example");

    println!("Prerequisites:");
    println!("  1. Install Ollama from https://ollama.ai");
    println!("  2. Run: ollama pull llama2");
    println!("  3. Run: ollama pull mistral");
    println!("\nVerify Ollama is running: http://localhost:11434\n");

    // Example 1: Simple completion with Llama 2
    print_separator("Example 1: Simple Completion with Llama 2");

    let config = OllamaConfig {
        model: "llama2".to_string(),
        temperature: 0.7,
        api_base: "http://localhost:11434".to_string(),
        timeout_seconds: 120,
    };

    let agent = OllamaAgent::new(config);

    let msg = Message::with_text(
        "user",
        "Explain the difference between stack and heap memory in 2 sentences.",
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
            if let Some(duration) = response.metadata.get("total_duration_ns") {
                println!(
                    "Duration: {} ms",
                    duration.as_u64().unwrap_or(0) / 1_000_000
                );
            }
            if let Some(usage) = response.metadata.get("usage") {
                println!("Token usage: {}", usage);
            }
        }
        Err(e) => {
            eprintln!("Error: {}", e);
            eprintln!("\nMake sure Ollama is running and llama2 is installed:");
            eprintln!("  ollama serve");
            eprintln!("  ollama pull llama2");
        }
    }

    // Example 2: Model comparison (Llama vs Mistral)
    print_separator("Example 2: Model Comparison (Llama 2 vs Mistral)");

    let prompt = "What is the main advantage of Rust over C++?";
    println!("Prompt: {}\n", prompt);

    // Llama 2
    println!("Llama 2 Response:");
    let llama_config = OllamaConfig {
        model: "llama2".to_string(),
        temperature: 0.7,
        ..Default::default()
    };
    let llama = OllamaAgent::new(llama_config);
    let msg = Message::with_text("user", prompt);

    match llama.process(msg).await {
        Ok(response) => {
            println!("{}", response.content_as_str().unwrap_or(""));
            if let Some(duration) = response.metadata.get("total_duration_ns") {
                println!(
                    "Duration: {} ms",
                    duration.as_u64().unwrap_or(0) / 1_000_000
                );
            }
        }
        Err(e) => eprintln!("Error: {}", e),
    }

    println!("\n{}\n", "-".repeat(60));

    // Mistral
    println!("Mistral Response:");
    let mistral_config = OllamaConfig {
        model: "mistral".to_string(),
        temperature: 0.7,
        ..Default::default()
    };
    let mistral = OllamaAgent::new(mistral_config);
    let msg = Message::with_text("user", prompt);

    match mistral.process(msg).await {
        Ok(response) => {
            println!("{}", response.content_as_str().unwrap_or(""));
            if let Some(duration) = response.metadata.get("total_duration_ns") {
                println!(
                    "Duration: {} ms",
                    duration.as_u64().unwrap_or(0) / 1_000_000
                );
            }
        }
        Err(e) => {
            eprintln!("Error: {}", e);
            eprintln!("Make sure mistral is installed: ollama pull mistral");
        }
    }

    // Example 3: Temperature effects
    print_separator("Example 3: Temperature Effects");

    let creative_prompt = "Write a one-sentence tagline for a code editor focused on simplicity.";
    println!("Prompt: {}\n", creative_prompt);

    // Low temperature
    println!("Low Temperature (0.3):");
    let low_temp_config = OllamaConfig {
        model: "llama2".to_string(),
        temperature: 0.3,
        ..Default::default()
    };
    let low_temp = OllamaAgent::new(low_temp_config);
    let msg = Message::with_text("user", creative_prompt);

    match low_temp.process(msg).await {
        Ok(response) => println!("{}", response.content_as_str().unwrap_or("")),
        Err(e) => eprintln!("Error: {}", e),
    }

    println!("\n{}\n", "-".repeat(60));

    // High temperature
    println!("High Temperature (0.9):");
    let high_temp_config = OllamaConfig {
        model: "llama2".to_string(),
        temperature: 0.9,
        ..Default::default()
    };
    let high_temp = OllamaAgent::new(high_temp_config);
    let msg = Message::with_text("user", creative_prompt);

    match high_temp.process(msg).await {
        Ok(response) => println!("{}", response.content_as_str().unwrap_or("")),
        Err(e) => eprintln!("Error: {}", e),
    }

    // Example 4: Custom endpoint (for remote Ollama)
    print_separator("Example 4: Custom Endpoint Configuration");

    println!("You can connect to a remote Ollama instance:");
    let remote_config = OllamaConfig {
        model: "llama2".to_string(),
        api_base: "http://remote-server:11434".to_string(),
        temperature: 0.7,
        timeout_seconds: 180,
    };

    println!("Config: api_base = {}", remote_config.api_base);
    println!("This allows running inference on a more powerful server");
    println!("while keeping your local code lightweight.\n");

    print_separator("✓ All Ollama examples completed!");

    println!("Key Takeaways:");
    println!("  • Ollama enables local LLM inference without API keys");
    println!("  • No data sent to external servers (privacy-focused)");
    println!("  • Supports Llama, Mistral, CodeLlama, and many more");
    println!("  • Can connect to remote Ollama instances");
    println!("  • Free to use, no rate limits or costs");
    println!("\nAvailable Models:");
    println!("  • llama2 (7B) - General purpose");
    println!("  • llama2:13b - More capable");
    println!("  • mistral (7B) - Fast and efficient");
    println!("  • codellama (7B) - Code generation");
    println!("  • phi (2.7B) - Small but capable");
    println!("\nTo list all models: ollama list");
    println!("{}", "-".repeat(60));

    Ok(())
}
