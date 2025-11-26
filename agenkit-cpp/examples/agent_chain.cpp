/**
 * @file agent_chain.cpp
 * @brief Example demonstrating agent chaining and composition
 *
 * This example shows how to:
 * - Chain multiple agents together
 * - Pass messages between agents
 * - Build complex workflows from simple agents
 * - Handle errors in agent chains
 */

#include <iostream>
#include <memory>
#include <vector>
#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include "agenkit/adapters/echo_agent.hpp"

using namespace agenkit;

/**
 * @brief Transform agent that prefixes messages
 */
class PrefixAgent : public core::Agent {
public:
    PrefixAgent(std::string prefix) : prefix_(std::move(prefix)) {}

    std::string name() const override {
        return "prefix-" + prefix_;
    }

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override {
        // Get original content
        std::string content = message.content_as_str();

        // Add prefix
        std::string transformed = prefix_ + content;

        // Create response
        auto response = core::Message::with_text("assistant", transformed);

        // Copy metadata
        response.with_metadata("original_content", content)
                .with_metadata("prefix", prefix_);

        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::ok(response)
        );
    }

    std::vector<std::string> capabilities() const override {
        return {"transform", "prefix"};
    }

private:
    std::string prefix_;
};

/**
 * @brief Transform agent that converts to uppercase
 */
class UppercaseAgent : public core::Agent {
public:
    std::string name() const override {
        return "uppercase";
    }

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override {
        std::string content = message.content_as_str();

        // Convert to uppercase
        for (char& c : content) {
            c = static_cast<char>(std::toupper(static_cast<unsigned char>(c)));
        }

        auto response = core::Message::with_text("assistant", content);
        response.with_metadata("transformed", "uppercase");

        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::ok(response)
        );
    }

    std::vector<std::string> capabilities() const override {
        return {"transform", "uppercase"};
    }
};

/**
 * @brief Agent chain that processes messages through multiple agents
 */
class AgentChain {
public:
    void add_agent(std::shared_ptr<core::Agent> agent) {
        agents_.push_back(std::move(agent));
    }

    core::Result<core::Message, core::AgentError>
    process(core::Message message) {
        core::Message current = std::move(message);

        std::cout << "Processing through " << agents_.size() << " agents...\n\n";

        for (size_t i = 0; i < agents_.size(); i++) {
            auto& agent = agents_[i];

            std::cout << "[" << (i + 1) << "/" << agents_.size() << "] "
                      << agent->name() << ": \"" << current.content_as_str() << "\"\n";

            // Process with current agent
            auto future = agent->process(std::move(current));
            auto result = future.get();

            if (result.is_err()) {
                std::cerr << "Error in agent " << agent->name() << ": "
                          << result.unwrap_err().message() << "\n";
                return result;
            }

            current = result.unwrap();
        }

        std::cout << "\n";
        return core::Result<core::Message, core::AgentError>::ok(current);
    }

private:
    std::vector<std::shared_ptr<core::Agent>> agents_;
};

int main() {
    std::cout << "=== Agenkit C++ Agent Chain Example ===\n\n";

    // Example 1: Simple prefix chain
    std::cout << "Example 1: Prefix Chain\n";
    std::cout << "------------------------\n";

    AgentChain chain1;
    chain1.add_agent(std::make_shared<PrefixAgent>("Hello, "));
    chain1.add_agent(std::make_shared<PrefixAgent>("dear "));

    auto msg1 = core::Message::with_text("user", "world!");
    auto result1 = chain1.process(std::move(msg1));

    if (result1.is_ok()) {
        std::cout << "Final result: \"" << result1.unwrap().content_as_str() << "\"\n";
    }

    std::cout << "\n";

    // Example 2: Transform chain
    std::cout << "Example 2: Transform Chain\n";
    std::cout << "---------------------------\n";

    AgentChain chain2;
    chain2.add_agent(std::make_shared<PrefixAgent>("Welcome: "));
    chain2.add_agent(std::make_shared<UppercaseAgent>());
    chain2.add_agent(std::make_shared<PrefixAgent>("[NOTICE] "));

    auto msg2 = core::Message::with_text("user", "new user detected");
    auto result2 = chain2.process(std::move(msg2));

    if (result2.is_ok()) {
        std::cout << "Final result: \"" << result2.unwrap().content_as_str() << "\"\n";
    }

    std::cout << "\n";

    // Example 3: Complex chain
    std::cout << "Example 3: Complex Pipeline\n";
    std::cout << "----------------------------\n";

    AgentChain chain3;
    chain3.add_agent(std::make_shared<PrefixAgent>("Step 1: "));
    chain3.add_agent(std::make_shared<adapters::EchoAgent>());
    chain3.add_agent(std::make_shared<UppercaseAgent>());
    chain3.add_agent(std::make_shared<PrefixAgent>(">>> "));
    chain3.add_agent(std::make_shared<PrefixAgent>("FINAL: "));

    auto msg3 = core::Message::with_text("user", "processing...");
    auto result3 = chain3.process(std::move(msg3));

    if (result3.is_ok()) {
        auto final_msg = result3.unwrap();
        std::cout << "Final result: \"" << final_msg.content_as_str() << "\"\n";
        std::cout << "Metadata: " << final_msg.metadata().dump(2) << "\n";
    }

    std::cout << "\n=== Example Complete ===\n";

    return 0;
}
