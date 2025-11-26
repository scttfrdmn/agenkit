/**
 * @file echo_agent.cpp
 * @brief Simple example demonstrating the Echo agent
 *
 * This example shows how to:
 * - Create an echo agent
 * - Send messages to the agent
 * - Handle the response
 */

#include <iostream>
#include "agenkit/adapters/echo_agent.hpp"
#include "agenkit/core/message.hpp"

using namespace agenkit;

int main() {
    std::cout << "=== Agenkit C++ Echo Agent Example ===" << std::endl;
    std::cout << std::endl;

    // Create an echo agent
    adapters::EchoAgent agent;
    std::cout << "Created agent: " << agent.name() << std::endl;

    // Show capabilities
    std::cout << "Capabilities: ";
    for (const auto& cap : agent.capabilities()) {
        std::cout << cap << " ";
    }
    std::cout << std::endl << std::endl;

    // Send a message
    std::cout << "Sending message: \"Hello, C++ agent!\"" << std::endl;
    auto message = core::Message::with_text("user", "Hello, C++ agent!");

    // Add some metadata
    message.with_metadata("example", "echo_agent")
           .with_metadata("language", "C++");

    // Process the message
    auto future = agent.process(std::move(message));
    auto result = future.get();

    // Handle the result
    if (result.is_ok()) {
        auto response = result.unwrap();
        std::cout << "Response from " << response.role() << ": "
                  << response.content_as_str() << std::endl;

        // Show the full JSON representation
        std::cout << std::endl << "Full response as JSON:" << std::endl;
        std::cout << response.to_json().dump(2) << std::endl;
    } else {
        auto error = result.unwrap_err();
        std::cerr << "Error: " << error.message() << std::endl;
        return 1;
    }

    std::cout << std::endl << "Example completed successfully!" << std::endl;
    return 0;
}
