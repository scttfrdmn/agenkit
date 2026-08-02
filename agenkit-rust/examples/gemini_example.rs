//! Google Gemini adapter example.
//!
//! Demonstrates how to use the Gemini adapter to interact with Google's Gemini models.
//!
//! # Setup
//!
//! 1. Get a Google API key from https://makersuite.google.com/app/apikey
//!
//! 2. Set the API key as an environment variable:
//!    ```bash
//!    export GEMINI_API_KEY="your-api-key"
//!    # Or:
//!    export GOOGLE_API_KEY="your-api-key"
//!    ```
//!
//! 3. Run this example:
//!    ```bash
//!    cargo run --example gemini_example --features native
//!    ```
use agenkit::adapters::gemini::{GeminiAdapter, GeminiConfig};
use agenkit::core::{Agent, Message};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("Google Gemini Adapter Example");
    println!("=============================\n");

    // Example 1: Basic usage with default configuration
    println!("Example 1: Basic usage (Gemini 2.0 Flash)");
    println!("-----------------------------------------");

    let config = GeminiConfig {
        api_key: std::env::var("GEMINI_API_KEY")
            .or_else(|_| std::env::var("GOOGLE_API_KEY"))
            .unwrap_or_else(|_| {
                eprintln!("Error: GEMINI_API_KEY or GOOGLE_API_KEY environment variable not set");
                eprintln!("Get your API key from: https://makersuite.google.com/app/apikey");
                std::process::exit(1);
            }),
        model: "gemini-2.0-flash-exp".to_string(),
        ..Default::default()
    };

    let adapter = match GeminiAdapter::new(config) {
        Ok(adapter) => adapter,
        Err(e) => {
            eprintln!("Error creating adapter: {}", e);
            return Ok(());
        }
    };

    println!("Agent name: {}", adapter.name());
    println!("Agent capabilities: {:?}", adapter.capabilities());

    let message = Message::with_text("user", "What is the capital of France?");
    println!("\nUser: {}", message.content_as_str().unwrap());

    match adapter.process(message).await {
        Ok(response) => {
            println!("Assistant: {}", response.content_as_str().unwrap_or(""));
            println!("\nMetadata:");
            if let Some(model) = response.metadata.get("model") {
                println!("  Model: {}", model);
            }
            if let Some(usage) = response.metadata.get("usage") {
                println!("  Usage: {}", usage);
            }
            if let Some(finish_reason) = response.metadata.get("finish_reason") {
                println!("  Finish reason: {}", finish_reason);
            }
        }
        Err(e) => {
            eprintln!("Error: {}", e);
            return Err(Box::new(e) as Box<dyn std::error::Error>);
        }
    }

    println!("\n");

    // Example 2: Using Gemini 1.5 Pro with custom configuration
    println!("Example 2: Gemini 1.5 Pro with custom settings");
    println!("----------------------------------------------");

    let config = GeminiConfig {
        api_key: std::env::var("GEMINI_API_KEY")
            .or_else(|_| std::env::var("GOOGLE_API_KEY"))
            .unwrap_or_else(|_| {
                eprintln!("Error: GEMINI_API_KEY or GOOGLE_API_KEY environment variable not set");
                std::process::exit(1);
            }),
        model: "gemini-1.5-pro".to_string(),
        temperature: Some(0.9),
        max_tokens: Some(4096),
        top_p: Some(0.95),
        top_k: Some(20),
        stop_sequences: Vec::new(),
        timeout_seconds: 120,
    };

    let adapter = match GeminiAdapter::new(config) {
        Ok(adapter) => adapter,
        Err(e) => {
            eprintln!("Error creating adapter: {}", e);
            return Ok(());
        }
    };

    let message = Message::with_text("user", "Write a haiku about programming in Rust.");
    println!("User: {}", message.content_as_str().unwrap());

    match adapter.process(message).await {
        Ok(response) => {
            println!("Assistant: {}", response.content_as_str().unwrap_or(""));
        }
        Err(e) => {
            eprintln!("Error: {}", e);
        }
    }

    println!("\n");

    // Example 3: Multi-turn conversation
    println!("Example 3: Multi-turn conversation");
    println!("-----------------------------------");

    let config = GeminiConfig {
        api_key: std::env::var("GEMINI_API_KEY")
            .or_else(|_| std::env::var("GOOGLE_API_KEY"))
            .unwrap_or_else(|_| {
                eprintln!("Error: GEMINI_API_KEY or GOOGLE_API_KEY environment variable not set");
                std::process::exit(1);
            }),
        model: "gemini-2.0-flash-exp".to_string(),
        ..Default::default()
    };

    let adapter = match GeminiAdapter::new(config) {
        Ok(adapter) => adapter,
        Err(e) => {
            eprintln!("Error creating adapter: {}", e);
            return Ok(());
        }
    };

    // First message
    let msg1 = Message::with_text("user", "Hello! What's your name?");
    println!("User: {}", msg1.content_as_str().unwrap());

    match adapter.process(msg1).await {
        Ok(response) => {
            println!("Assistant: {}", response.content_as_str().unwrap_or(""));
        }
        Err(e) => {
            eprintln!("Error: {}", e);
        }
    }

    // Second message
    let msg2 = Message::with_text(
        "user",
        "Can you explain what the Gemini API is in one sentence?",
    );
    println!("\nUser: {}", msg2.content_as_str().unwrap());

    match adapter.process(msg2).await {
        Ok(response) => {
            println!("Assistant: {}", response.content_as_str().unwrap_or(""));
        }
        Err(e) => {
            eprintln!("Error: {}", e);
        }
    }

    println!("\n");

    // Example 4: System message support
    println!("Example 4: System message (converted to user message)");
    println!("-----------------------------------------------------");

    let config = GeminiConfig {
        api_key: std::env::var("GEMINI_API_KEY")
            .or_else(|_| std::env::var("GOOGLE_API_KEY"))
            .unwrap_or_else(|_| {
                eprintln!("Error: GEMINI_API_KEY or GOOGLE_API_KEY environment variable not set");
                std::process::exit(1);
            }),
        model: "gemini-2.0-flash-exp".to_string(),
        ..Default::default()
    };

    let adapter = match GeminiAdapter::new(config) {
        Ok(adapter) => adapter,
        Err(e) => {
            eprintln!("Error creating adapter: {}", e);
            return Ok(());
        }
    };

    // System messages are converted to user messages in Gemini
    let system_msg = Message::with_text(
        "system",
        "You are a helpful assistant that speaks like a pirate.",
    );
    println!("System: {}", system_msg.content_as_str().unwrap());

    let user_msg = Message::with_text("user", "Tell me about Rust programming.");
    println!("User: {}", user_msg.content_as_str().unwrap());

    // Note: In a real implementation, you'd send both messages together
    // For this example, we'll just send the user message
    match adapter.process(user_msg).await {
        Ok(response) => {
            println!("Assistant: {}", response.content_as_str().unwrap_or(""));
        }
        Err(e) => {
            eprintln!("Error: {}", e);
        }
    }

    println!("\n");

    // Example 5: Available models
    println!("Example 5: Available Gemini models");
    println!("-----------------------------------");
    println!("Gemini 2.0 Flash (experimental): gemini-2.0-flash-exp");
    println!("Gemini 1.5 Pro: gemini-1.5-pro");
    println!("Gemini 1.5 Flash: gemini-1.5-flash");
    println!("Gemini Pro: gemini-pro");

    Ok(())
}
