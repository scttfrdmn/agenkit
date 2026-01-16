///! Amazon Bedrock adapter example.
///!
///! Demonstrates how to use the Bedrock adapter to interact with AWS Bedrock foundation models.
///!
///! # Setup
///!
///! 1. Configure AWS credentials (one of the following):
///!    - Set environment variables:
///!      ```bash
///!      export AWS_ACCESS_KEY_ID="your-access-key"
///!      export AWS_SECRET_ACCESS_KEY="your-secret-key"
///!      export AWS_REGION="us-east-1"
///!      ```
///!    - Configure AWS CLI: `aws configure`
///!    - Use IAM role (if running on EC2/ECS/Lambda)
///!
///! 2. Enable model access in AWS Bedrock console:
///!    - Go to AWS Bedrock console
///!    - Request access to models (e.g., Claude, Llama, Mistral)
///!
///! 3. Run this example:
///!    ```bash
///!    cargo run --example bedrock_example --features native
///!    ```
use agenkit::adapters::bedrock::{BedrockAdapter, BedrockConfig};
use agenkit::core::{Agent, Message};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("Amazon Bedrock Adapter Example");
    println!("==============================\n");

    // Example 1: Basic usage with default configuration (Claude 3.5 Sonnet)
    println!("Example 1: Basic usage (Claude 3.5 Sonnet)");
    println!("-------------------------------------------");

    let config = BedrockConfig {
        region: std::env::var("AWS_REGION").unwrap_or_else(|_| "us-east-1".to_string()),
        model: "anthropic.claude-3-5-sonnet-20241022-v2:0".to_string(),
        ..Default::default()
    };

    match BedrockAdapter::new(config).await {
        Ok(adapter) => {
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
                    if let Some(stop_reason) = response.metadata.get("stop_reason") {
                        println!("  Stop reason: {}", stop_reason);
                    }
                }
                Err(e) => {
                    eprintln!("Error processing message: {}", e);
                }
            }
        }
        Err(e) => {
            eprintln!("Error creating Bedrock adapter: {}", e);
            eprintln!("\nMake sure you have:");
            eprintln!("1. AWS credentials configured");
            eprintln!("2. Access to Bedrock models enabled in AWS console");
            eprintln!("3. Correct region specified");
        }
    }

    println!("\n");

    // Example 2: Using different model (Claude 3 Haiku - faster, cheaper)
    println!("Example 2: Claude 3 Haiku (faster model)");
    println!("-----------------------------------------");

    let config = BedrockConfig {
        region: std::env::var("AWS_REGION").unwrap_or_else(|_| "us-east-1".to_string()),
        model: "anthropic.claude-3-haiku-20240307-v1:0".to_string(),
        temperature: Some(0.9),
        max_tokens: Some(2048),
        ..Default::default()
    };

    if let Ok(adapter) = BedrockAdapter::new(config).await {
        let message = Message::with_text("user", "Write a haiku about cloud computing.");
        println!("User: {}", message.content_as_str().unwrap());

        match adapter.process(message).await {
            Ok(response) => {
                println!("Assistant: {}", response.content_as_str().unwrap_or(""));
            }
            Err(e) => {
                eprintln!("Error: {}", e);
            }
        }
    }

    println!("\n");

    // Example 3: Using explicit credentials
    println!("Example 3: Using explicit credentials");
    println!("--------------------------------------");

    let config = BedrockConfig {
        region: "us-east-1".to_string(),
        model: "anthropic.claude-3-5-sonnet-20241022-v2:0".to_string(),
        access_key_id: std::env::var("AWS_ACCESS_KEY_ID").ok(),
        secret_access_key: std::env::var("AWS_SECRET_ACCESS_KEY").ok(),
        session_token: std::env::var("AWS_SESSION_TOKEN").ok(),
        ..Default::default()
    };

    if config.access_key_id.is_some() && config.secret_access_key.is_some() {
        println!("Using explicit AWS credentials from environment variables");
        if let Ok(adapter) = BedrockAdapter::new(config).await {
            println!("Adapter created successfully with explicit credentials");
        }
    } else {
        println!("No explicit credentials provided, would use default credential chain");
    }

    println!("\n");

    // Example 4: System message support
    println!("Example 4: System message support");
    println!("----------------------------------");

    let config = BedrockConfig {
        region: std::env::var("AWS_REGION").unwrap_or_else(|_| "us-east-1".to_string()),
        model: "anthropic.claude-3-5-sonnet-20241022-v2:0".to_string(),
        ..Default::default()
    };

    if let Ok(adapter) = BedrockAdapter::new(config).await {
        // System messages are handled separately in Bedrock
        let system_msg = Message::with_text(
            "system",
            "You are a helpful assistant that explains things concisely.",
        );
        println!("System: {}", system_msg.content_as_str().unwrap());

        let user_msg = Message::with_text("user", "Explain quantum computing in one sentence.");
        println!("User: {}", user_msg.content_as_str().unwrap());

        // Note: In a real implementation, you'd pass both messages together
        // For this example, we'll just send the user message
        match adapter.process(user_msg).await {
            Ok(response) => {
                println!("Assistant: {}", response.content_as_str().unwrap_or(""));
            }
            Err(e) => {
                eprintln!("Error: {}", e);
            }
        }
    }

    println!("\n");

    // Example 5: Available models
    println!("Example 5: Available Bedrock models");
    println!("------------------------------------");
    println!("\nClaude models (Anthropic):");
    println!("  - anthropic.claude-3-5-sonnet-20241022-v2:0 (most capable)");
    println!("  - anthropic.claude-3-opus-20240229-v1:0 (large context)");
    println!("  - anthropic.claude-3-haiku-20240307-v1:0 (fast & affordable)");
    println!("\nLlama models (Meta):");
    println!("  - meta.llama3-70b-instruct-v1:0");
    println!("  - meta.llama3-8b-instruct-v1:0");
    println!("\nMistral models:");
    println!("  - mistral.mistral-large-2402-v1:0");
    println!("  - mistral.mistral-7b-instruct-v0:2");
    println!("\nAmazon Titan models:");
    println!("  - amazon.titan-text-premier-v1:0");
    println!("  - amazon.titan-text-express-v1");

    println!("\n");

    // Example 6: Configuration options
    println!("Example 6: Configuration options");
    println!("---------------------------------");
    println!("Temperature: Controls randomness (0.0 = deterministic, 1.0 = creative)");
    println!("Max tokens: Maximum length of response");
    println!("Top P: Nucleus sampling parameter");
    println!("Stop sequences: Strings that stop generation");
    println!("Region: AWS region (us-east-1, us-west-2, etc.)");

    Ok(())
}
