///! OpenAI-Compatible LLM Adapter Example
///!
///! This example demonstrates using Agenkit with OpenAI-compatible inference services
///! like vLLM, llama.cpp, SGLang, and TensorRT-LLM.
///!
///! # Setup Instructions
///!
///! ## 1. vLLM (recommended for production):
///! ```bash
///! docker run --gpus all -p 8000:8000 vllm/vllm-openai \
///!   --model meta-llama/Llama-2-7b-chat-hf
///! ```
///!
///! ## 2. llama.cpp (lightweight, CPU-friendly):
///! ```bash
///! git clone https://github.com/ggerganov/llama.cpp
///! cd llama.cpp && make
///! ./server -m models/llama-2-7b-chat.gguf -c 2048 --port 8080
///! ```
///!
///! ## 3. SGLang (optimized for complex prompts):
///! ```bash
///! pip install sglang
///! python -m sglang.launch_server \
///!   --model-path meta-llama/Llama-2-7b-chat-hf --port 30000
///! ```
///!
///! # Benefits
///! - Run LLMs locally (no cloud API costs)
///! - Keep data private (on-premises)
///! - Same code works with all services
///! - Easy migration between providers
///!
///! # Usage
///! ```bash
///! cargo run --example openai_compatible_example --features native
///! ```

use agenkit::adapters::openai_compatible::{
    providers, OpenAICompatibleAgent, OpenAICompatibleConfig,
};
use agenkit::core::{Agent, Message};

fn print_separator(title: &str) {
    println!("\n{}", "=".repeat(80));
    if !title.is_empty() {
        println!("{}", title);
        println!("{}", "=".repeat(80));
    }
}

/// Example 1: vLLM Local Deployment
///
/// vLLM is the most popular choice for high-throughput inference.
async fn vllm_example() {
    print_separator("Example 1: vLLM Local Deployment");

    println!("\nSetup:");
    println!("  docker run --gpus all -p 8000:8000 vllm/vllm-openai \\");
    println!("    --model meta-llama/Llama-2-7b-chat-hf");
    println!();

    // Create vLLM adapter using provider helper
    let config = providers::vllm("meta-llama/Llama-2-7b-chat-hf");
    let agent = OpenAICompatibleAgent::new(config);

    println!("✓ Connected to vLLM service");
    println!("  Provider: {}", agent.name());
    println!("  Capabilities: {:?}", agent.capabilities());
    println!();

    let msg = Message::with_text("user", "What is machine learning in one sentence?");
    println!("📤 User: {}", msg.content_as_str().unwrap_or(""));

    match agent.process(msg).await {
        Ok(response) => {
            println!("📥 Assistant: {}", response.content_as_str().unwrap_or(""));

            // Print metadata
            if let Some(provider) = response.metadata.get("provider") {
                println!("\n📊 Metadata:");
                println!("  Provider: {}", provider);
                println!(
                    "  Base URL: {}",
                    response.metadata.get("base_url").unwrap()
                );
                println!("  Model: {}", response.metadata.get("model").unwrap());
                if let Some(usage) = response.metadata.get("usage") {
                    println!("  Usage: {}", usage);
                }
            }
        }
        Err(e) => {
            println!("❌ Error (service may not be running): {}", e);
            println!("   Make sure vLLM is running on http://localhost:8000");
        }
    }
}

/// Example 2: llama.cpp Server
///
/// llama.cpp is lightweight and CPU-friendly, perfect for development.
async fn llamacpp_example() {
    print_separator("Example 2: llama.cpp Server");

    println!("\nSetup:");
    println!("  ./llama.cpp/server -m models/llama-2-7b-chat.gguf \\");
    println!("    -c 2048 --port 8080");
    println!();

    // Create llama.cpp adapter with custom parameters
    let mut config = providers::llamacpp("llama-2-7b-chat");
    config.temperature = 0.7;
    config.max_tokens = 100;

    let agent = OpenAICompatibleAgent::new(config);

    println!("✓ Connected to llama.cpp server");
    println!("  Provider: {}", agent.name());
    println!();

    let msg = Message::with_text("user", "Write a haiku about coding.");
    println!("📤 User: {}", msg.content_as_str().unwrap_or(""));

    match agent.process(msg).await {
        Ok(response) => {
            println!("📥 Assistant:\n{}", response.content_as_str().unwrap_or(""));
        }
        Err(e) => {
            println!("❌ Error (service may not be running): {}", e);
            println!("   Make sure llama.cpp is running on http://localhost:8080");
        }
    }
}

/// Example 3: Multi-Service Comparison
///
/// Demonstrates how the same code works with different services.
async fn multi_service_example() {
    print_separator("Example 3: Multi-Service Comparison");

    println!("\nThis example shows how the same code works with different services.\n");

    let services = vec![
        (
            "vLLM",
            providers::vllm("meta-llama/Llama-2-7b-chat-hf"),
        ),
        ("llama.cpp", providers::llamacpp("llama-2-7b-chat")),
        (
            "SGLang",
            providers::sglang("meta-llama/Llama-2-7b-chat-hf"),
        ),
    ];

    let msg = Message::with_text("user", "What is a GPU in one sentence?");

    for (name, config) in services {
        println!("Testing {}...", name);

        let mut config = config;
        config.max_tokens = 100;

        let agent = OpenAICompatibleAgent::new(config);

        match agent.process(msg.clone()).await {
            Ok(response) => {
                println!("  ✅ {} responded:", name);
                let content = response.content_as_str().unwrap_or("");
                let truncated = if content.len() > 80 {
                    format!("{}...", &content[..77])
                } else {
                    content.to_string()
                };
                println!("     {}", truncated);
                if let Some(provider) = response.metadata.get("provider") {
                    println!("     Provider: {}", provider);
                }
                println!();
            }
            Err(e) => {
                println!("  ❌ {} not available: {}\n", name, e);
            }
        }
    }

    println!("💡 Key Point: The same Agenkit code works with all services!");
}

/// Example 4: Custom Configuration
///
/// Shows how to create a custom configuration for any OpenAI-compatible service.
async fn custom_config_example() {
    print_separator("Example 4: Custom Configuration");

    println!("\nCreating custom configuration for a hypothetical service...\n");

    let config = OpenAICompatibleConfig {
        base_url: "http://localhost:9000/v1".to_string(),
        model: "my-custom-model".to_string(),
        provider: Some("custom-service".to_string()),
        temperature: 0.5,
        max_tokens: 2048,
        top_p: 0.95,
        timeout_seconds: 30,
        ..Default::default()
    };

    let agent = OpenAICompatibleAgent::new(config);

    println!("✓ Created agent with custom configuration");
    println!("  Name: {}", agent.name());
    println!("  Capabilities: {:?}", agent.capabilities());
}

/// Print setup instructions for all services.
fn print_setup_instructions() {
    print_separator("Setup Instructions");

    println!("\n1️⃣  vLLM:");
    println!("   docker run --gpus all -p 8000:8000 vllm/vllm-openai \\");
    println!("       --model meta-llama/Llama-2-7b-chat-hf\n");

    println!("2️⃣  llama.cpp:");
    println!("   git clone https://github.com/ggerganov/llama.cpp");
    println!("   cd llama.cpp && make");
    println!("   ./server -m models/llama-2-7b-chat.gguf -c 2048 --port 8080\n");

    println!("3️⃣  SGLang:");
    println!("   pip install sglang");
    println!("   python -m sglang.launch_server \\");
    println!("       --model-path meta-llama/Llama-2-7b-chat-hf \\");
    println!("       --port 30000\n");

    println!("4️⃣  TensorRT-LLM:");
    println!("   docker run --gpus all -p 8001:8001 \\");
    println!("       nvcr.io/nvidia/tritonserver:23.10-trtllm-python-py3 \\");
    println!("       tritonserver --model-repository=/models\n");

    println!("💡 Benefits:");
    println!("   • Run LLMs locally (no cloud API costs)");
    println!("   • Keep data private (on-premises)");
    println!("   • Same code works with all services");
    println!("   • Easy migration between providers\n");
}

#[tokio::main]
async fn main() {
    println!("╔{}╗", "=".repeat(78));
    println!(
        "║{}║",
        format!(
            "{:^78}",
            "OpenAI-Compatible LLM Adapter Examples"
        )
    );
    println!("╚{}╝", "=".repeat(78));
    println!();
    println!("This example demonstrates using Agenkit with OpenAI-compatible");
    println!("inference services like vLLM, llama.cpp, SGLang, and TensorRT-LLM.");
    println!();
    println!("Note: These examples require a running inference service.");
    println!("See the examples below for setup instructions.");
    println!();

    // Run examples
    vllm_example().await;
    llamacpp_example().await;
    multi_service_example().await;
    custom_config_example().await;

    // Print setup instructions
    print_setup_instructions();

    println!("✅ Example Complete!");
    println!();
    println!("Next steps:");
    println!("  • Start a local inference service");
    println!("  • Run: cargo run --example openai_compatible_example --features native");
    println!("  • Try different services and models");
}
