//! LiteLLM adapter example.
//!
//! Demonstrates how to use the LiteLLM adapter to connect to various LLM providers
//! through the LiteLLM proxy.
//!
//! # Setup
//!
//! 1. Install LiteLLM:
//!    ```bash
//!    pip install litellm[proxy]
//!    ```
//!
//! 2. Start the LiteLLM proxy:
//!    ```bash
//!    litellm --model gpt-3.5-turbo
//!    # Or for other models:
//!    # litellm --model claude-3-5-sonnet-20241022
//!    # litellm --model bedrock/anthropic.claude-v2
//!    ```
//!
//! 3. Run this example:
//!    ```bash
//!    cargo run --example litellm_example --features native
//!    ```
use agenkit::adapters::litellm::{LiteLLMAdapter, LiteLLMConfig};
use agenkit::core::{Agent, Message};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("LiteLLM Adapter Example");
    println!("======================\n");

    // Example 1: Basic usage with default configuration
    println!("Example 1: Basic usage (default configuration)");
    println!("----------------------------------------------");

    let config = LiteLLMConfig {
        base_url: "http://localhost:4000".to_string(),
        model: "gpt-3.5-turbo".to_string(),
        ..Default::default()
    };

    let adapter = LiteLLMAdapter::new(config);

    let message = Message::with_text("user", "What is the capital of France?");
    println!("User: {}", message.content_as_str().unwrap());

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
        }
        Err(e) => {
            eprintln!("Error: {}", e);
            eprintln!("\nMake sure LiteLLM proxy is running on http://localhost:4000");
            eprintln!("Start it with: litellm --model gpt-3.5-turbo");
        }
    }

    println!("\n");

    // Example 2: Custom configuration with different model
    println!("Example 2: Custom configuration");
    println!("--------------------------------");

    let config = LiteLLMConfig {
        base_url: "http://localhost:4000".to_string(),
        model: "gpt-4".to_string(),
        temperature: Some(0.9),
        max_tokens: Some(2048),
        top_p: Some(0.95),
        api_key: None, // Optional: add API key if needed
        timeout_seconds: 120,
    };

    let adapter = LiteLLMAdapter::new(config);
    println!("Agent capabilities: {:?}", adapter.capabilities());

    let message = Message::with_text("user", "Tell me a short joke about programming.");
    println!("\nUser: {}", message.content_as_str().unwrap());

    match adapter.process(message).await {
        Ok(response) => {
            println!("Assistant: {}", response.content_as_str().unwrap_or(""));
        }
        Err(e) => {
            eprintln!("Error: {}", e);
        }
    }

    println!("\n");

    // Example 3: Using different providers through LiteLLM
    println!("Example 3: Different providers");
    println!("-------------------------------");
    println!("LiteLLM supports 100+ providers. Examples:\n");
    println!("OpenAI models:");
    println!("  - gpt-4, gpt-4-turbo, gpt-4o, gpt-3.5-turbo\n");
    println!("Anthropic models:");
    println!("  - claude-3-5-sonnet-20241022, claude-3-opus-20240229\n");
    println!("AWS Bedrock models:");
    println!("  - bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0\n");
    println!("Google Gemini models:");
    println!("  - gemini/gemini-pro, gemini/gemini-2.0-flash-exp\n");
    println!("Local Ollama models:");
    println!("  - ollama/llama2, ollama/mistral\n");
    println!("Azure OpenAI:");
    println!("  - azure/gpt-4\n");
    println!("Cohere:");
    println!("  - command-r-plus\n");

    println!("To use different models, start LiteLLM with:");
    println!("  litellm --model <model-name>");

    Ok(())
}
