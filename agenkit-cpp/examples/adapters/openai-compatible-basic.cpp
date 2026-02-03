/**
 * @file openai-compatible-basic.cpp
 * @brief Example: Using OpenAI-compatible inference services
 *
 * This example demonstrates:
 * - OpenAI-compatible adapter for local/self-hosted LLMs
 * - Support for 8+ inference engines (vLLM, llama.cpp, SGLang, TensorRT-LLM, etc.)
 * - Provider helper functions for quick configuration
 * - Multiple service examples with the same code
 *
 * Supported Services:
 *   • vLLM - High-throughput batch inference
 *   • llama.cpp - Lightweight C++ implementation (CPU-friendly)
 *   • SGLang - Optimized for complex prompts
 *   • TensorRT-LLM - NVIDIA GPU optimized
 *   • OpenLLM - Multi-model serving platform
 *   • MLC LLM - Mobile and edge deployment
 *   • Text Generation Inference (TGI) - HuggingFace inference server
 *   • Inferflow - High-performance inference
 *
 * Setup (vLLM example):
 *   # Using Docker
 *   docker run --gpus all -p 8000:8000 vllm/vllm-openai \
 *       --model meta-llama/Llama-3.3-8B-Instruct
 *
 *   # Or using pip
 *   pip install vllm
 *   vllm serve meta-llama/Llama-3.3-8B-Instruct --port 8000
 *
 * Setup (llama.cpp example):
 *   # Build llama.cpp server
 *   git clone https://github.com/ggerganov/llama.cpp
 *   cd llama.cpp && make server
 *   ./server -m models/llama-2-7b-chat.gguf --port 8080
 */

#include <iostream>
#include <memory>
#include "agenkit/adapters/openai_compatible_agent.hpp"
#include "agenkit/core/message.hpp"

using namespace agenkit;

void example_vllm() {
    std::cout << "\n";
    std::cout << "================================================================\n";
    std::cout << "  Example 1: vLLM (High-throughput batch inference)\n";
    std::cout << "================================================================\n\n";

    // Use provider helper for vLLM
    auto config = adapters::OpenAICompatibleProviders::vllm("meta-llama/Llama-3.3-8B-Instruct");

    std::cout << "Configuration:\n";
    std::cout << "  Provider:  " << config.provider.value() << "\n";
    std::cout << "  Base URL:  " << config.base_url << "\n";
    std::cout << "  Model:     " << config.model << "\n";
    std::cout << "  Temp:      " << config.temperature << "\n\n";

    try {
        adapters::OpenAICompatibleAgent agent(config);

        std::cout << "Agent: " << agent.name() << "\n";
        std::cout << "Capabilities: ";
        for (const auto& cap : agent.capabilities()) {
            std::cout << cap << " ";
        }
        std::cout << "\n\n";

        // Example query
        std::string question = "What are the benefits of using vLLM for inference?";
        std::cout << "Q: " << question << "\n\n";

        auto msg = core::Message::with_text("user", question);
        auto future = agent.process(std::move(msg));
        auto result = future.get();

        if (result.is_ok()) {
            auto response = result.unwrap();
            std::cout << "A: " << response.content_as_str() << "\n\n";

            // Show metadata
            if (response.metadata().contains("usage")) {
                auto usage = response.metadata()["usage"];
                std::cout << "Tokens: "
                         << usage["prompt_tokens"].get<int>() << " prompt, "
                         << usage["completion_tokens"].get<int>() << " completion\n";
            }
            std::cout << "Provider: " << response.metadata()["provider"].get<std::string>() << "\n";
        } else {
            std::cerr << "❌ Error: " << result.unwrap_err().message() << "\n";
            std::cerr << "\nMake sure vLLM server is running:\n";
            std::cerr << "  docker run --gpus all -p 8000:8000 vllm/vllm-openai \\\n";
            std::cerr << "      --model meta-llama/Llama-3.3-8B-Instruct\n";
        }

    } catch (const std::exception& e) {
        std::cerr << "Exception: " << e.what() << "\n";
    }
}

void example_llamacpp() {
    std::cout << "\n";
    std::cout << "================================================================\n";
    std::cout << "  Example 2: llama.cpp (CPU-friendly, lightweight)\n";
    std::cout << "================================================================\n\n";

    // Use provider helper for llama.cpp
    auto config = adapters::OpenAICompatibleProviders::llamacpp("llama-3.3-8b-instruct");

    std::cout << "Configuration:\n";
    std::cout << "  Provider:  " << config.provider.value() << "\n";
    std::cout << "  Base URL:  " << config.base_url << "\n";
    std::cout << "  Model:     " << config.model << "\n\n";

    try {
        adapters::OpenAICompatibleAgent agent(config);

        std::cout << "Agent: " << agent.name() << "\n\n";

        // Example query
        std::string question = "Explain quantum computing in simple terms.";
        std::cout << "Q: " << question << "\n\n";

        auto msg = core::Message::with_text("user", question);
        auto future = agent.process(std::move(msg));
        auto result = future.get();

        if (result.is_ok()) {
            auto response = result.unwrap();
            std::cout << "A: " << response.content_as_str() << "\n\n";
        } else {
            std::cerr << "❌ Error: " << result.unwrap_err().message() << "\n";
            std::cerr << "\nMake sure llama.cpp server is running:\n";
            std::cerr << "  cd llama.cpp\n";
            std::cerr << "  ./server -m models/llama-3.3-8b-instruct.gguf --port 8080\n";
        }

    } catch (const std::exception& e) {
        std::cerr << "Exception: " << e.what() << "\n";
    }
}

void example_sglang() {
    std::cout << "\n";
    std::cout << "================================================================\n";
    std::cout << "  Example 3: SGLang (Optimized for complex prompts)\n";
    std::cout << "================================================================\n\n";

    // Use provider helper for SGLang
    auto config = adapters::OpenAICompatibleProviders::sglang("meta-llama/Llama-3.3-70B-Instruct");

    std::cout << "Configuration:\n";
    std::cout << "  Provider:  " << config.provider.value() << "\n";
    std::cout << "  Base URL:  " << config.base_url << "\n";
    std::cout << "  Model:     " << config.model << "\n\n";

    try {
        adapters::OpenAICompatibleAgent agent(config);

        std::cout << "Agent: " << agent.name() << "\n\n";

        // Example query with complex prompt
        std::string question = "Write a detailed comparison of Python vs C++ for ML inference, "
                             "considering performance, ease of use, and deployment options.";
        std::cout << "Q: " << question << "\n\n";

        auto msg = core::Message::with_text("user", question);
        auto future = agent.process(std::move(msg));
        auto result = future.get();

        if (result.is_ok()) {
            auto response = result.unwrap();
            std::cout << "A: " << response.content_as_str() << "\n\n";
        } else {
            std::cerr << "❌ Error: " << result.unwrap_err().message() << "\n";
            std::cerr << "\nMake sure SGLang server is running:\n";
            std::cerr << "  pip install sglang\n";
            std::cerr << "  sglang serve meta-llama/Llama-3.3-70B-Instruct --port 30000\n";
        }

    } catch (const std::exception& e) {
        std::cerr << "Exception: " << e.what() << "\n";
    }
}

void example_tensorrt() {
    std::cout << "\n";
    std::cout << "================================================================\n";
    std::cout << "  Example 4: TensorRT-LLM (NVIDIA GPU optimized)\n";
    std::cout << "================================================================\n\n";

    // Use provider helper for TensorRT-LLM
    auto config = adapters::OpenAICompatibleProviders::tensorrt("llama-3.3-70b-instruct");

    std::cout << "Configuration:\n";
    std::cout << "  Provider:  " << config.provider.value() << "\n";
    std::cout << "  Base URL:  " << config.base_url << "\n";
    std::cout << "  Model:     " << config.model << "\n\n";

    try {
        adapters::OpenAICompatibleAgent agent(config);

        std::cout << "Agent: " << agent.name() << "\n\n";

        // Example query
        std::string question = "What are the advantages of using TensorRT for LLM inference?";
        std::cout << "Q: " << question << "\n\n";

        auto msg = core::Message::with_text("user", question);
        auto future = agent.process(std::move(msg));
        auto result = future.get();

        if (result.is_ok()) {
            auto response = result.unwrap();
            std::cout << "A: " << response.content_as_str() << "\n\n";
        } else {
            std::cerr << "❌ Error: " << result.unwrap_err().message() << "\n";
            std::cerr << "\nMake sure TensorRT-LLM server is running on port 8001\n";
        }

    } catch (const std::exception& e) {
        std::cerr << "Exception: " << e.what() << "\n";
    }
}

void example_custom() {
    std::cout << "\n";
    std::cout << "================================================================\n";
    std::cout << "  Example 5: Custom Configuration (any OpenAI-compatible service)\n";
    std::cout << "================================================================\n\n";

    // Manual configuration for any OpenAI-compatible service
    adapters::OpenAICompatibleConfig config;
    config.base_url = "http://localhost:9000/v1";
    config.model = "custom-model";
    config.provider = "custom-provider";
    config.temperature = 0.8;
    config.max_tokens = 2048;
    config.timeout = std::chrono::milliseconds{120000};

    std::cout << "Configuration:\n";
    std::cout << "  Provider:  " << config.provider.value() << "\n";
    std::cout << "  Base URL:  " << config.base_url << "\n";
    std::cout << "  Model:     " << config.model << "\n";
    std::cout << "  Max Tokens:" << config.max_tokens << "\n\n";

    try {
        adapters::OpenAICompatibleAgent agent(config);

        std::cout << "Agent: " << agent.name() << "\n";
        std::cout << "This configuration works with ANY OpenAI-compatible service!\n\n";

    } catch (const std::exception& e) {
        std::cerr << "Exception: " << e.what() << "\n";
    }
}

int main(int argc, char* argv[]) {
    std::cout << "\n";
    std::cout << "╔════════════════════════════════════════════════════════════════╗\n";
    std::cout << "║  Agenkit C++ - OpenAI-Compatible Inference Services Example   ║\n";
    std::cout << "╚════════════════════════════════════════════════════════════════╝\n";

    // Run examples based on command line argument
    if (argc > 1) {
        std::string example = argv[1];
        if (example == "vllm" || example == "1") {
            example_vllm();
        } else if (example == "llamacpp" || example == "2") {
            example_llamacpp();
        } else if (example == "sglang" || example == "3") {
            example_sglang();
        } else if (example == "tensorrt" || example == "4") {
            example_tensorrt();
        } else if (example == "custom" || example == "5") {
            example_custom();
        } else {
            std::cout << "\nUsage: " << argv[0] << " [example]\n";
            std::cout << "Examples:\n";
            std::cout << "  1 or vllm     - vLLM example\n";
            std::cout << "  2 or llamacpp - llama.cpp example\n";
            std::cout << "  3 or sglang   - SGLang example\n";
            std::cout << "  4 or tensorrt - TensorRT-LLM example\n";
            std::cout << "  5 or custom   - Custom configuration example\n\n";
            return 1;
        }
    } else {
        // Run all examples
        example_vllm();
        example_llamacpp();
        example_sglang();
        example_tensorrt();
        example_custom();
    }

    std::cout << "\n";
    std::cout << "================================================================\n";
    std::cout << "\n✓ OpenAI-compatible examples complete!\n";
    std::cout << "\nKey Benefits:\n";
    std::cout << "  ✓ Single adapter works with 8+ inference engines\n";
    std::cout << "  ✓ Zero vendor lock-in - easy migration between services\n";
    std::cout << "  ✓ Consistent API across local and cloud deployments\n";
    std::cout << "  ✓ Cost-effective - use local/self-hosted models\n";
    std::cout << "\nSupported Services:\n";
    std::cout << "  • vLLM (high-throughput)\n";
    std::cout << "  • llama.cpp (CPU-friendly)\n";
    std::cout << "  • SGLang (complex prompts)\n";
    std::cout << "  • TensorRT-LLM (GPU-optimized)\n";
    std::cout << "  • OpenLLM, MLC LLM, TGI, Inferflow\n\n";

    return 0;
}
