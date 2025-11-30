/**
 * @file llm-integration.cpp
 * @brief LLM Integration Example - OpenAI, Anthropic, and Ollama
 *
 * Demonstrates how to integrate real LLM providers:
 * - OpenAI (GPT-4, GPT-3.5)
 * - Anthropic (Claude)
 * - Ollama (Local models)
 * - Middleware for production resilience
 *
 * Setup:
 *   export OPENAI_API_KEY=your-key
 *   export ANTHROPIC_API_KEY=your-key
 *   # For Ollama: ollama pull llama2
 *   cmake -B build -S .
 *   cmake --build build
 *   ./build/examples/llm-integration
 */

#include "agenkit/adapters/openai_agent.hpp"
#include "agenkit/adapters/claude_agent.hpp"
#include "agenkit/adapters/ollama_agent.hpp"
#include "agenkit/core/message.hpp"
#include <iostream>
#include <cstdlib>

using namespace agenkit;
using namespace agenkit::adapters;
using namespace agenkit::core;

void print_separator(const std::string& title = "") {
    std::cout << "\n";
    std::cout << std::string(70, '=') << "\n";
    if (!title.empty()) {
        std::cout << title << "\n";
        std::cout << std::string(70, '=') << "\n";
    }
    std::cout << "\n";
}

// Example 1: OpenAI Integration
void example_openai() {
    print_separator("Example 1: OpenAI Integration");
    std::cout << "  GPT-4 and GPT-3.5 Turbo support\n\n";

    const char* api_key = std::getenv("OPENAI_API_KEY");
    if (!api_key) {
        std::cout << "  ⚠️  OPENAI_API_KEY not set, skipping...\n\n";
        return;
    }

    try {
        OpenAIConfig config;
        config.api_key = api_key;
        config.model = "gpt-3.5-turbo";
        config.temperature = 0.7;
        config.max_tokens = 150;

        OpenAIAgent gpt(config);

        std::cout << "  Asking OpenAI: \"What is agenkit?\"\n";

        auto msg = Message::with_text("user", "What is agenkit? Answer in one sentence.");
        auto future = gpt.process(std::move(msg));
        auto result = future.get();

        if (result.is_ok()) {
            const auto& response = result.unwrap();
            std::cout << "  🤖 OpenAI: " << response.content_as_str() << "\n\n";
        } else {
            std::cerr << "  ❌ Error: " << result.unwrap_err().message() << "\n\n";
        }
    } catch (const std::exception& e) {
        std::cerr << "  ❌ Exception: " << e.what() << "\n\n";
    }
}

// Example 2: Anthropic Integration (Claude)
void example_anthropic() {
    print_separator("Example 2: Anthropic Integration");
    std::cout << "  Claude 3 (Opus, Sonnet, Haiku) support\n\n";

    const char* api_key = std::getenv("ANTHROPIC_API_KEY");
    if (!api_key) {
        std::cout << "  ⚠️  ANTHROPIC_API_KEY not set, skipping...\n\n";
        return;
    }

    try {
        ClaudeConfig config;
        config.api_key = api_key;
        config.model = "claude-3-5-sonnet-20241022";
        config.max_tokens = 150;

        ClaudeAgent claude(config);

        std::cout << "  Asking Claude: \"What makes a good AI agent framework?\"\n";

        auto msg = Message::with_text("user", "What makes a good AI agent framework? One sentence.");
        auto future = claude.process(std::move(msg));
        auto result = future.get();

        if (result.is_ok()) {
            const auto& response = result.unwrap();
            std::cout << "  🤖 Claude: " << response.content_as_str() << "\n\n";
        } else {
            std::cerr << "  ❌ Error: " << result.unwrap_err().message() << "\n\n";
        }
    } catch (const std::exception& e) {
        std::cerr << "  ❌ Exception: " << e.what() << "\n\n";
    }
}

// Example 3: Ollama Integration (Local models)
void example_ollama() {
    print_separator("Example 3: Ollama Integration");
    std::cout << "  Local LLM inference (Llama 2, Mistral, etc.)\n\n";

    try {
        OllamaConfig config;
        config.model = "llama2";
        config.base_url = "http://localhost:11434";
        config.temperature = 0.7;
        config.max_tokens = 150;

        OllamaAgent ollama(config);

        std::cout << "  Asking Ollama: \"What are AI agents?\"\n";

        auto msg = Message::with_text("user", "What are AI agents? One sentence.");
        auto future = ollama.process(std::move(msg));
        auto result = future.get();

        if (result.is_ok()) {
            const auto& response = result.unwrap();
            std::cout << "  🤖 Ollama: " << response.content_as_str() << "\n\n";
        } else {
            std::cerr << "  ❌ Error: " << result.unwrap_err().message() << "\n";
            std::cerr << "  💡 Make sure Ollama is running: ollama serve\n";
            std::cerr << "  💡 And model is downloaded: ollama pull llama2\n\n";
        }
    } catch (const std::exception& e) {
        std::cerr << "  ❌ Exception: " << e.what() << "\n";
        std::cerr << "  💡 Make sure Ollama is running: ollama serve\n";
        std::cerr << "  💡 And model is downloaded: ollama pull llama2\n\n";
    }
}

// Print LLM configuration best practices
void print_best_practices() {
    print_separator("🎯 LLM Configuration Best Practices");

    std::cout << "  Model Selection:\n";
    std::cout << "    • GPT-4: Most capable, slower, $$$\n";
    std::cout << "    • GPT-3.5-turbo: Fast, cheap, good for most tasks\n";
    std::cout << "    • Claude Opus: Highest capability\n";
    std::cout << "    • Claude Sonnet: Balanced performance/cost\n";
    std::cout << "    • Claude Haiku: Fastest, cheapest\n";
    std::cout << "    • Ollama (local): Free, private, offline\n\n";

    std::cout << "  Temperature Settings:\n";
    std::cout << "    • 0.0-0.3: Deterministic, factual (code, facts)\n";
    std::cout << "    • 0.4-0.7: Balanced (most applications)\n";
    std::cout << "    • 0.8-1.0: Creative (writing, brainstorming)\n\n";

    std::cout << "  Production Checklist:\n";
    std::cout << "    ✓ Add retry middleware (handle rate limits)\n";
    std::cout << "    ✓ Add timeout middleware (prevent hangs)\n";
    std::cout << "    ✓ Add circuit breaker (handle outages)\n";
    std::cout << "    ✓ Monitor token usage (cost control)\n";
    std::cout << "    ✓ Cache responses (reduce API calls)\n";
    std::cout << "    ✓ Use streaming for UX (show progress)\n\n";
}

// Print cost optimization tips
void print_cost_optimization() {
    print_separator("💰 Cost Optimization Tips");

    std::cout << "  1. Use appropriate models:\n";
    std::cout << "     • Don't use GPT-4 for simple tasks\n";
    std::cout << "     • Start with GPT-3.5, upgrade if needed\n\n";

    std::cout << "  2. Limit max_tokens:\n";
    std::cout << "     • Set reasonable limits (e.g., 150 for short answers)\n";
    std::cout << "     • Prevents runaway costs\n\n";

    std::cout << "  3. Cache responses:\n";
    std::cout << "     • Use caching middleware for repeated queries\n";
    std::cout << "     • Especially effective for FAQ-style apps\n\n";

    std::cout << "  4. Batch requests:\n";
    std::cout << "     • Use batching middleware when possible\n";
    std::cout << "     • OpenAI Batch API: 50% cheaper!\n\n";

    std::cout << "  5. Use local models (Ollama):\n";
    std::cout << "     • Free for development and testing\n";
    std::cout << "     • No API costs or rate limits\n";
    std::cout << "     • Privacy-preserving (data stays local)\n\n";

    std::cout << "✨ Pro Tip: Monitor your API usage in production!\n";
    std::cout << "   Set up alerts for unexpected cost spikes.\n\n";
}

int main() {
    std::cout << "\n🤖 Agenkit C++ LLM Integration Examples\n\n";

    example_openai();
    example_anthropic();
    example_ollama();

    print_best_practices();
    print_cost_optimization();

    print_separator("✅ ALL EXAMPLES COMPLETED");

    return 0;
}
