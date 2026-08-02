//! Example demonstrating LiteLLM streaming support.
//!
//! This example shows how to stream responses through LiteLLM proxy
//! in real-time, displaying text as it arrives from the API.
//!
//! Prerequisites:
//! - Install LiteLLM: `pip install litellm[proxy]`
//! - Start LiteLLM proxy: `litellm --model gpt-3.5-turbo`
//! - Or use Docker: `docker run -p 4000:4000 ghcr.io/berriai/litellm:main-latest`
//!
//! Run with:
//! ```bash
//! export LITELLM_API_KEY="your-key-here"  # Optional for local proxy
//! cargo run --example litellm_streaming --features native
//! ```
use agenkit::adapters::litellm::{LiteLLMAdapter, LiteLLMConfig};
use agenkit::core::Message;
use futures::stream::StreamExt;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Configure LiteLLM
    let config = LiteLLMConfig {
        model: "gpt-3.5-turbo".to_string(),
        base_url: "http://localhost:4000".to_string(),
        api_key: std::env::var("LITELLM_API_KEY").ok(),
        temperature: Some(1.0),
        max_tokens: Some(1024),
        ..Default::default()
    };

    let adapter = LiteLLMAdapter::new(config);

    println!("=== LiteLLM Streaming Example ===\n");
    println!("Using LiteLLM proxy...\n");
    println!("Response (streaming):");
    println!("{}", "-".repeat(60));

    // Create message
    let message = Message::with_text("user", "Count to 10, one number per line.");

    // Stream response
    let mut stream = adapter.stream(message).await;
    let mut full_response = String::new();

    while let Some(result) = stream.next().await {
        match result {
            Ok(chunk) => {
                if let Some(text) = chunk.content_as_str() {
                    print!("{}", text);
                    full_response.push_str(text);
                }
            }
            Err(e) => {
                eprintln!("\nError: {:?}", e);
                return Err(e.into());
            }
        }
    }

    println!("\n{}", "-".repeat(60));
    println!("\nFull response length: {} characters", full_response.len());

    // Example 2: Story generation
    println!("\n\n=== Story Generation Example ===\n");
    println!("Asking LiteLLM to write a short story...\n");
    println!("Response (streaming):");
    println!("{}", "-".repeat(60));

    let message = Message::with_text(
        "user",
        "Write a very short story (3 sentences) about a robot learning to paint.",
    );

    let mut stream = adapter.stream(message).await;
    let mut full_response = String::new();

    while let Some(result) = stream.next().await {
        match result {
            Ok(chunk) => {
                if let Some(text) = chunk.content_as_str() {
                    print!("{}", text);
                    full_response.push_str(text);
                }
            }
            Err(e) => {
                eprintln!("\nError: {:?}", e);
                return Err(e.into());
            }
        }
    }

    println!("\n{}", "-".repeat(60));
    println!("\nStreaming complete!");
    println!("Total characters received: {}", full_response.len());

    Ok(())
}
