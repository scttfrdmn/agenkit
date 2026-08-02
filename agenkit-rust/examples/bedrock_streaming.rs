///! Example demonstrating Amazon Bedrock streaming support.
///!
///! This example shows how to stream responses from Bedrock foundation models
///! in real-time, displaying text as it arrives from the API.
///!
///! Run with:
///! ```bash
///! export AWS_REGION="us-east-1"
///! export AWS_ACCESS_KEY_ID="your-key-id"
///! export AWS_SECRET_ACCESS_KEY="your-secret-key"
///! cargo run --example bedrock_streaming --features native
///! ```
use agenkit::adapters::bedrock::{BedrockAdapter, BedrockConfig};
use agenkit::core::Message;
use futures::stream::StreamExt;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Configure Bedrock (uses AWS credential chain by default)
    let config = BedrockConfig {
        region: std::env::var("AWS_REGION").unwrap_or_else(|_| "us-east-1".to_string()),
        model: "anthropic.claude-3-5-sonnet-20241022-v2:0".to_string(),
        temperature: Some(0.7),
        max_tokens: Some(1024),
        ..Default::default()
    };

    let adapter = BedrockAdapter::new(config).await?;

    println!("=== Amazon Bedrock Streaming Example ===\n");
    println!("Using Claude 3.5 Sonnet on Bedrock...\n");
    println!("Response (streaming):");
    println!("{}", "-".repeat(60));

    // Create messages
    let messages = vec![Message::with_text(
        "user",
        "Count to 10, one number per line.",
    )];

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

    // Example 2: Story generation
    println!("\n\n=== Story Generation Example ===\n");
    println!("Asking Claude to write a short story...\n");
    println!("Response (streaming):");
    println!("{}", "-".repeat(60));

    let messages = vec![Message::with_text(
        "user",
        "Write a very short story (3 sentences) about a robot learning to paint.",
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

    // Example 3: With system message
    println!("\n\n=== System Message Example ===\n");
    println!("Using a system message for behavior control...\n");

    let messages = vec![
        Message::with_text(
            "system",
            "You are a helpful math tutor. Keep responses concise.",
        ),
        Message::with_text("user", "What's 15 * 23?"),
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
