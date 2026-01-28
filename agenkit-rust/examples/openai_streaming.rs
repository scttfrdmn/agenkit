///! Example demonstrating OpenAI GPT streaming support.
///!
///! This example shows how to stream responses from OpenAI models in real-time,
///! displaying text as it arrives from the API.
///!
///! Run with:
///! ```bash
///! export OPENAI_API_KEY="your-key-here"
///! cargo run --example openai_streaming --features native
///! ```

use agenkit::adapters::openai::{OpenAIAgent, OpenAIConfig};
use agenkit::core::Message;
use futures::stream::StreamExt;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Configure OpenAI
    let config = OpenAIConfig {
        api_key: std::env::var("OPENAI_API_KEY")
            .expect("OPENAI_API_KEY environment variable not set"),
        model: "gpt-4o-mini".to_string(),
        temperature: 1.0,
        max_tokens: 1024,
        ..Default::default()
    };

    let adapter = OpenAIAgent::new(config);

    println!("=== OpenAI GPT Streaming Example ===\n");
    println!("Asking GPT to count to 10...\n");
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
    println!("Asking GPT to write a short story...\n");
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
