///! Example demonstrating Ollama streaming support.
///!
///! This example shows how to stream responses from local Ollama models
///! in real-time, displaying text as it arrives from the API.
///!
///! Prerequisites:
///! - Install Ollama: https://ollama.ai
///! - Pull a model: `ollama pull llama2`
///! - Start Ollama server (usually runs automatically)
///!
///! Run with:
///! ```bash
///! cargo run --example ollama_streaming --features native
///! ```
use agenkit::adapters::ollama::{OllamaAgent, OllamaConfig};
use agenkit::core::Message;
use futures::stream::StreamExt;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Configure Ollama
    let config = OllamaConfig {
        model: "llama2".to_string(),
        api_base: "http://localhost:11434".to_string(),
        temperature: 0.7,
        ..Default::default()
    };

    let adapter = OllamaAgent::new(config);

    println!("=== Ollama Streaming Example ===\n");
    println!("Using Llama 2 model...\n");
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
    println!("Asking Llama to write a short story...\n");
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
