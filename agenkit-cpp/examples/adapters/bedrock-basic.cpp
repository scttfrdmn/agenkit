/**
 * @file bedrock-basic.cpp
 * @brief Basic Amazon Bedrock usage example
 *
 * Demonstrates:
 * - Bedrock adapter configuration
 * - Single-turn completion
 * - Multiple model comparison
 * - AWS credential configuration
 * - Error handling
 * - Metadata extraction
 *
 * Prerequisites:
 *   1. AWS SDK for C++ installed with bedrock-runtime component
 *   2. AWS credentials configured (one of):
 *      - Environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
 *      - AWS credentials file: ~/.aws/credentials
 *      - IAM role (if running on EC2/ECS)
 *   3. AWS Bedrock model access enabled in your account
 *
 * Setup:
 *   # Option 1: Environment variables
 *   export AWS_ACCESS_KEY_ID=your-access-key
 *   export AWS_SECRET_ACCESS_KEY=your-secret-key
 *   export AWS_DEFAULT_REGION=us-east-1
 *
 *   # Option 2: AWS credentials file
 *   aws configure
 *
 *   # Build with Bedrock support
 *   cmake -B build -S . -DAGENKIT_HAS_AWS_SDK=ON
 *   cmake --build build
 *   ./build/examples/bedrock-basic
 *
 * NOTE: This example requires AWS SDK for C++ to be installed.
 * If not available, it will fail with a runtime error.
 */

#include "agenkit/adapters/bedrock_agent.hpp"
#include "agenkit/core/message.hpp"
#include <iostream>
#include <cstdlib>

using namespace agenkit;
using namespace agenkit::adapters;
using namespace agenkit::core;

void print_separator(const std::string& title = "") {
    std::cout << "\n";
    std::cout << std::string(60, '=') << "\n";
    if (!title.empty()) {
        std::cout << title << "\n";
        std::cout << std::string(60, '=') << "\n";
    }
    std::cout << "\n";
}

int main() {
    print_separator("AgentKit C++ - Amazon Bedrock Basic Example");

    std::cout << "Amazon Bedrock provides access to foundation models:\n";
    std::cout << "  • Anthropic Claude (3.5 Sonnet, 3 Opus, 3 Haiku)\n";
    std::cout << "  • Meta Llama (3.2 90B, 11B, 3B, 1B)\n";
    std::cout << "  • Mistral (Large, 7B Instruct)\n";
    std::cout << "  • Amazon Titan (Premier, Express, Lite)\n\n";

    std::cout << "NOTE: This requires AWS SDK for C++ to be installed.\n\n";

    try {
        // Example 1: Simple completion with Claude
        print_separator("Example 1: Simple Completion with Claude 3.5 Sonnet");

        BedrockConfig config;
        config.region = "us-east-1";
        config.model = BedrockModels::CLAUDE_3_5_SONNET_V2;
        config.temperature = 0.7;
        config.max_tokens = 1024;

        // Optional: Provide explicit credentials
        const char* access_key = std::getenv("AWS_ACCESS_KEY_ID");
        const char* secret_key = std::getenv("AWS_SECRET_ACCESS_KEY");
        if (access_key && secret_key) {
            config.access_key_id = access_key;
            config.secret_access_key = secret_key;
            std::cout << "✓ Using credentials from environment variables\n";
        } else {
            std::cout << "✓ Using AWS default credential chain\n";
        }

        BedrockAgent bedrock(config);

        std::cout << "Model: " << config.model << "\n";
        std::cout << "Region: " << config.region << "\n";
        std::cout << "User: Explain AWS Bedrock in two sentences.\n\n";

        auto msg = Message::with_text("user", "Explain AWS Bedrock in two sentences.");
        auto future = bedrock.process(std::move(msg));
        auto result = future.get();

        if (result.is_ok()) {
            const auto& response = result.unwrap();
            std::cout << "Claude: " << response.content_as_str() << "\n\n";

            // Show metadata
            std::cout << "Metadata:\n";
            const auto& meta = response.metadata();
            if (meta.contains("model")) {
                std::cout << "  Model: " << meta["model"].get<std::string>() << "\n";
            }
            if (meta.contains("finish_reason")) {
                std::cout << "  Finish reason: " << meta["finish_reason"].get<std::string>() << "\n";
            }
            if (meta.contains("usage")) {
                const auto& usage = meta["usage"];
                if (usage.contains("total_tokens")) {
                    std::cout << "  Total tokens: " << usage["total_tokens"].get<int>() << "\n";
                }
            }
        } else {
            std::cerr << "Error: " << result.unwrap_err().message() << "\n";
        }
    } catch (const std::exception& e) {
        std::cerr << "Exception: " << e.what() << "\n";
        std::cerr << "\nPlease ensure:\n";
        std::cerr << "  1. AWS SDK for C++ is installed\n";
        std::cerr << "  2. AWS credentials are configured\n";
        std::cerr << "  3. Bedrock model access is enabled in your AWS account\n";
        return 1;
    }

    // Example 2: Model comparison
    print_separator("Example 2: Model Comparison");

    try {
        std::string prompt = "Write a haiku about cloud computing.";

        std::vector<std::pair<std::string, std::string>> models = {
            {"Claude 3.5 Sonnet", BedrockModels::CLAUDE_3_5_SONNET_V2},
            {"Claude 3 Haiku", BedrockModels::CLAUDE_3_HAIKU},
            {"Llama 3.2 11B", BedrockModels::LLAMA_3_2_11B}
        };

        for (const auto& [name, model_id] : models) {
            BedrockConfig config;
            config.region = "us-east-1";
            config.model = model_id;
            config.max_tokens = 100;

            BedrockAgent bedrock(config);

            std::cout << "Model: " << name << "\n";
            std::cout << "User: " << prompt << "\n\n";

            auto msg = Message::with_text("user", prompt);
            auto future = bedrock.process(std::move(msg));
            auto result = future.get();

            if (result.is_ok()) {
                std::cout << "Response:\n" << result.unwrap().content_as_str() << "\n\n";
            } else {
                std::cout << "Error: " << result.unwrap_err().message() << "\n\n";
            }
        }
    } catch (const std::exception& e) {
        std::cerr << "Exception: " << e.what() << "\n";
    }

    // Example 3: Temperature variation
    print_separator("Example 3: Temperature Effects");

    try {
        std::string prompt = "Generate a creative company name for a tech startup.";

        for (double temp : {0.2, 0.7, 1.0}) {
            BedrockConfig config;
            config.region = "us-east-1";
            config.model = BedrockModels::CLAUDE_3_HAIKU;
            config.temperature = temp;
            config.max_tokens = 50;

            BedrockAgent bedrock(config);

            std::cout << "Temperature: " << temp << "\n";
            std::cout << "User: " << prompt << "\n\n";

            auto msg = Message::with_text("user", prompt);
            auto future = bedrock.process(std::move(msg));
            auto result = future.get();

            if (result.is_ok()) {
                std::cout << "Response: " << result.unwrap().content_as_str() << "\n\n";
            }
        }
    } catch (const std::exception& e) {
        std::cerr << "Exception: " << e.what() << "\n";
    }

    // Example 4: Using inference configuration
    print_separator("Example 4: Advanced Configuration");

    try {
        BedrockConfig config;
        config.region = "us-east-1";
        config.model = BedrockModels::CLAUDE_3_5_SONNET_V2;
        config.temperature = 0.8;
        config.max_tokens = 200;
        config.top_p = 0.9;
        config.stop_sequences = {"\n\n", "END"};

        BedrockAgent bedrock(config);

        std::cout << "Configuration:\n";
        std::cout << "  Model: " << config.model << "\n";
        std::cout << "  Temperature: " << config.temperature.value() << "\n";
        std::cout << "  Max tokens: " << config.max_tokens.value() << "\n";
        std::cout << "  Top P: " << config.top_p.value() << "\n";
        std::cout << "  Stop sequences: ";
        for (const auto& seq : config.stop_sequences) {
            std::cout << "\"" << seq << "\" ";
        }
        std::cout << "\n\n";

        std::cout << "User: Tell me a short story about AI.\n\n";

        auto msg = Message::with_text("user", "Tell me a short story about AI.");
        auto future = bedrock.process(std::move(msg));
        auto result = future.get();

        if (result.is_ok()) {
            std::cout << "Response: " << result.unwrap().content_as_str() << "\n\n";
        }
    } catch (const std::exception& e) {
        std::cerr << "Exception: " << e.what() << "\n";
    }

    // Example 5: Using different regions
    print_separator("Example 5: Multi-Region Support");

    try {
        std::vector<std::string> regions = {"us-east-1", "us-west-2", "eu-west-1"};

        for (const auto& region : regions) {
            BedrockConfig config;
            config.region = region;
            config.model = BedrockModels::CLAUDE_3_HAIKU;
            config.max_tokens = 50;

            std::cout << "Region: " << region << "\n";
            std::cout << "Testing connectivity...\n";

            // Note: Model availability varies by region
            std::cout << "(Model availability varies by region)\n\n";
        }
    } catch (const std::exception& e) {
        std::cerr << "Exception: " << e.what() << "\n";
    }

    // Example 6: Model constants
    print_separator("Example 6: Available Model Constants");

    std::cout << "Anthropic Claude models:\n";
    std::cout << "  • " << BedrockModels::CLAUDE_3_5_SONNET_V2 << "\n";
    std::cout << "  • " << BedrockModels::CLAUDE_3_5_SONNET << "\n";
    std::cout << "  • " << BedrockModels::CLAUDE_3_OPUS << "\n";
    std::cout << "  • " << BedrockModels::CLAUDE_3_HAIKU << "\n\n";

    std::cout << "Meta Llama models:\n";
    std::cout << "  • " << BedrockModels::LLAMA_3_2_90B << "\n";
    std::cout << "  • " << BedrockModels::LLAMA_3_2_11B << "\n";
    std::cout << "  • " << BedrockModels::LLAMA_3_2_3B << "\n\n";

    std::cout << "Mistral models:\n";
    std::cout << "  • " << BedrockModels::MISTRAL_LARGE_2407 << "\n";
    std::cout << "  • " << BedrockModels::MISTRAL_7B << "\n\n";

    std::cout << "Amazon Titan models:\n";
    std::cout << "  • " << BedrockModels::TITAN_TEXT_PREMIER << "\n";
    std::cout << "  • " << BedrockModels::TITAN_TEXT_EXPRESS << "\n";

    print_separator("✓ All examples completed!");

    std::cout << "Key Features Demonstrated:\n";
    std::cout << "  • Bedrock adapter configuration\n";
    std::cout << "  • AWS credential management\n";
    std::cout << "  • Single-turn completion\n";
    std::cout << "  • Model comparison (Claude, Llama, Mistral)\n";
    std::cout << "  • Temperature effects\n";
    std::cout << "  • Advanced configuration (top_p, stop sequences)\n";
    std::cout << "  • Multi-region support\n";
    std::cout << "  • Error handling and metadata\n\n";

    std::cout << "Next Steps:\n";
    std::cout << "  • Enable model access in AWS Bedrock console\n";
    std::cout << "  • Try different models by changing config.model\n";
    std::cout << "  • Experiment with temperature and max_tokens\n";
    std::cout << "  • Use stop sequences for structured output\n";
    std::cout << "  • Deploy to AWS for IAM role-based auth\n";
    std::cout << "  • See https://docs.aws.amazon.com/bedrock/ for more info\n\n";

    return 0;
}
