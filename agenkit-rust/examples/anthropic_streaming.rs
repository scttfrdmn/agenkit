//! Example demonstrating Anthropic Claude streaming support.
//!
//! This example shows how to stream responses from Claude in real-time,
//! displaying text as it arrives from the API.
//!
//! Run with:
//! ```bash
//! export ANTHROPIC_API_KEY="your-key-here"
//! cargo run --example anthropic_streaming --features native
//! ```
use agenkit::adapters::anthropic::{AnthropicAgent, AnthropicConfig};
use agenkit::core::Message;
use futures::stream::StreamExt;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Load API key from environment
    let api_key = std::env::var("ANTHROPIC_API_KEY")
        .expect("ANTHROPIC_API_KEY environment variable must be set");

    // Configure Claude
    let config = AnthropicConfig {
        api_key,
        model: "claude-3-5-sonnet-20241022".to_string(),
        max_tokens: 1024,
        temperature: 1.0,
        ..Default::default()
    };

    let agent = AnthropicAgent::new(config);

    println!("=== Anthropic Claude Streaming Example ===\n");
    println!("Asking Claude to count to 10...\n");
    println!("Response (streaming):");
    println!("{}", "-".repeat(60));

    // Create message
    let message = Message::with_text("user", "Count to 10, one number per line.");

    // Stream response
    let mut stream = agent.stream(message).await;
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
    println!("Asking Claude to write a short story...\n");
    println!("Response (streaming):");
    println!("{}", "-".repeat(60));

    let message = Message::with_text(
        "user",
        "Write a very short story (3 sentences) about a robot learning to paint.",
    );

    let mut stream = agent.stream(message).await;
    let mut full_response = String::new();

    while let Some(result) = stream.next().await {
        match result {
            Ok(chunk) => {
                if let Some(text) = chunk.content_as_str() {
                    print!("{}", text);
                    std::io::Write::flush(&mut std::io::stdout())?;
                    full_response.push_str(text);

                    // Simulate real-time effect
                    tokio::time::sleep(tokio::time::Duration::from_millis(20)).await;
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
