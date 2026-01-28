///! Example demonstrating Google Gemini streaming support.
///!
///! This example shows how to stream responses from Gemini in real-time,
///! displaying text as it arrives from the API.
///!
///! Run with:
///! ```bash
///! export GEMINI_API_KEY="your-key-here"
///! cargo run --example gemini_streaming --features native
///! ```

use agenkit::adapters::gemini::{GeminiAdapter, GeminiConfig};
use agenkit::core::Message;
use futures::stream::StreamExt;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Load API key from environment
    let api_key = std::env::var("GEMINI_API_KEY")
        .or_else(|_| std::env::var("GOOGLE_API_KEY"))
        .expect("GEMINI_API_KEY or GOOGLE_API_KEY environment variable must be set");

    // Configure Gemini
    let config = GeminiConfig {
        api_key,
        model: "gemini-2.0-flash-exp".to_string(),
        temperature: Some(0.7),
        max_tokens: Some(1024),
        ..Default::default()
    };

    let adapter = GeminiAdapter::new(config)?;

    println!("=== Google Gemini Streaming Example ===\n");
    println!("Asking Gemini to count to 10...\n");
    println!("Response (streaming):");
    println!("{}", "-".repeat(60));

    // Create messages
    let messages = vec![Message::with_text("user", "Count to 10, one number per line.")];

    // Stream response
    let mut stream = adapter.stream(messages).await;
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

    // Example 2: Creative writing
    println!("\n\n=== Creative Writing Example ===\n");
    println!("Asking Gemini to write a haiku about AI...\n");
    println!("Response (streaming):");
    println!("{}", "-".repeat(60));

    let messages = vec![Message::with_text(
        "user",
        "Write a haiku about artificial intelligence.",
    )];

    let mut stream = adapter.stream(messages).await;
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

    // Example 3: Multi-turn conversation
    println!("\n\n=== Multi-turn Conversation Example ===\n");
    println!("Having a conversation with Gemini...\n");

    let messages = vec![
        Message::with_text("user", "What's 2+2?"),
        Message::with_text("assistant", "2+2 equals 4."),
        Message::with_text("user", "What about 3+3?"),
    ];

    println!("Response (streaming):");
    println!("{}", "-".repeat(60));

    let mut stream = adapter.stream(messages).await;

    while let Some(result) = stream.next().await {
        match result {
            Ok(chunk) => {
                if let Some(text) = chunk.content_as_str() {
                    print!("{}", text);
                    std::io::Write::flush(&mut std::io::stdout())?;
                }
            }
            Err(e) => {
                eprintln!("\nError: {:?}", e);
                return Err(e.into());
            }
        }
    }

    println!("\n{}", "-".repeat(60));
    println!("\nAll examples complete!");

    Ok(())
}
