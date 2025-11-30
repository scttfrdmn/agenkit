##! LLM Integration Example - OpenAI, Anthropic, and Ollama
//!
//! Demonstrates how to integrate real LLM providers:
//! - OpenAI (GPT-4, GPT-3.5)
//! - Anthropic (Claude)
//! - Ollama (Local models)
//! - Middleware for production resilience
//!
//! Setup:
//!   export OPENAI_API_KEY=your-key
//!   export ANTHROPIC_API_KEY=your-key
//!   # For Ollama: ollama pull llama2
//!   cargo run --example llm-integration --features native

use agenkit::adapters::anthropic::{AnthropicAgent, AnthropicConfig};
use agenkit::adapters::ollama::{OllamaAgent, OllamaConfig};
use agenkit::adapters::openai::{OpenAIAgent, OpenAIConfig};
use agenkit::core::{Agent, Message};

fn print_separator(title: &str) {
    println!("\n{}\n{}\n{}\n", "=".repeat(70), title, "=".repeat(70));
}

/// Example 1: OpenAI Integration
async fn example_openai() {
    print_separator("Example 1: OpenAI Integration");
    println!("  GPT-4 and GPT-3.5 Turbo support\n");

    let api_key = match std::env::var("OPENAI_API_KEY") {
        Ok(key) => key,
        Err(_) => {
            println!("  ⚠️  OPENAI_API_KEY not set, skipping...\n");
            return;
        }
    };

    let config = OpenAIConfig {
        api_key,
        model: "gpt-3.5-turbo".to_string(),
        temperature: 0.7,
        max_tokens: 150,
        ..Default::default()
    };

    let agent = OpenAIAgent::new(config);

    println!("  Asking OpenAI: \"What is agenkit?\"");

    let msg = Message::with_text("user", "What is agenkit? Answer in one sentence.");

    match agent.process(msg).await {
        Ok(response) => {
            println!("  🤖 OpenAI: {}\n", response.content_as_str().unwrap_or(""));
        }
        Err(e) => {
            eprintln!("  ❌ Error: {}\n", e);
        }
    }
}

/// Example 2: Anthropic Integration (Claude)
async fn example_anthropic() {
    print_separator("Example 2: Anthropic Integration");
    println!("  Claude 3 (Opus, Sonnet, Haiku) support\n");

    let api_key = match std::env::var("ANTHROPIC_API_KEY") {
        Ok(key) => key,
        Err(_) => {
            println!("  ⚠️  ANTHROPIC_API_KEY not set, skipping...\n");
            return;
        }
    };

    let config = AnthropicConfig {
        api_key,
        model: "claude-3-5-sonnet-20241022".to_string(),
        max_tokens: 150,
        ..Default::default()
    };

    let agent = AnthropicAgent::new(config);

    println!("  Asking Claude: \"What makes a good AI agent framework?\"");

    let msg = Message::with_text("user", "What makes a good AI agent framework? One sentence.");

    match agent.process(msg).await {
        Ok(response) => {
            println!("  🤖 Claude: {}\n", response.content_as_str().unwrap_or(""));
        }
        Err(e) => {
            eprintln!("  ❌ Error: {}\n", e);
        }
    }
}

/// Example 3: Ollama Integration (Local models)
async fn example_ollama() {
    print_separator("Example 3: Ollama Integration");
    println!("  Local LLM inference (Llama 2, Mistral, etc.)\n");

    let config = OllamaConfig {
        model: "llama2".to_string(),
        base_url: "http://localhost:11434".to_string(),
        temperature: 0.7,
        max_tokens: 150,
        ..Default::default()
    };

    let agent = OllamaAgent::new(config);

    println!("  Asking Ollama: \"What are AI agents?\"");

    let msg = Message::with_text("user", "What are AI agents? One sentence.");

    match agent.process(msg).await {
        Ok(response) => {
            println!("  🤖 Ollama: {}\n", response.content_as_str().unwrap_or(""));
        }
        Err(e) => {
            eprintln!("  ❌ Error: {}", e);
            eprintln!("  💡 Make sure Ollama is running: ollama serve");
            eprintln!("  💡 And model is downloaded: ollama pull llama2\n");
        }
    }
}

/// Print LLM configuration best practices
fn print_best_practices() {
    print_separator("🎯 LLM Configuration Best Practices");

    println!("  Model Selection:");
    println!("    • GPT-4: Most capable, slower, $$$");
    println!("    • GPT-3.5-turbo: Fast, cheap, good for most tasks");
    println!("    • Claude Opus: Highest capability");
    println!("    • Claude Sonnet: Balanced performance/cost");
    println!("    • Claude Haiku: Fastest, cheapest");
    println!("    • Ollama (local): Free, private, offline\n");

    println!("  Temperature Settings:");
    println!("    • 0.0-0.3: Deterministic, factual (code, facts)");
    println!("    • 0.4-0.7: Balanced (most applications)");
    println!("    • 0.8-1.0: Creative (writing, brainstorming)\n");

    println!("  Production Checklist:");
    println!("    ✓ Add retry middleware (handle rate limits)");
    println!("    ✓ Add timeout middleware (prevent hangs)");
    println!("    ✓ Add circuit breaker (handle outages)");
    println!("    ✓ Monitor token usage (cost control)");
    println!("    ✓ Cache responses (reduce API calls)");
    println!("    ✓ Use streaming for UX (show progress)\n");
}

/// Print cost optimization tips
fn print_cost_optimization() {
    print_separator("💰 Cost Optimization Tips");

    println!("  1. Use appropriate models:");
    println!("     • Don't use GPT-4 for simple tasks");
    println!("     • Start with GPT-3.5, upgrade if needed\n");

    println!("  2. Limit max_tokens:");
    println!("     • Set reasonable limits (e.g., 150 for short answers)");
    println!("     • Prevents runaway costs\n");

    println!("  3. Cache responses:");
    println!("     • Use caching middleware for repeated queries");
    println!("     • Especially effective for FAQ-style apps\n");

    println!("  4. Batch requests:");
    println!("     • Use batching middleware when possible");
    println!("     • OpenAI Batch API: 50% cheaper!\n");

    println!("  5. Use local models (Ollama):");
    println!("     • Free for development and testing");
    println!("     • No API costs or rate limits");
    println!("     • Privacy-preserving (data stays local)\n");

    println!("✨ Pro Tip: Monitor your API usage in production!");
    println!("   Set up alerts for unexpected cost spikes.\n");
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("\n🤖 Agenkit Rust LLM Integration Examples\n");

    example_openai().await;
    example_anthropic().await;
    example_ollama().await;

    print_best_practices();
    print_cost_optimization();

    print_separator("✅ ALL EXAMPLES COMPLETED");

    Ok(())
}
