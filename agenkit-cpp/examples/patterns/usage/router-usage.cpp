/**
 * Router Pattern Usage Example
 *
 * Conditional agent selection based on input classification
 *
 * Use cases:
 * - Intent-based routing
 * - Specialized agent dispatch
 * - Dynamic workflow selection
 *
 * Build: cd build && cmake .. && make
 * Run: ./examples/router_usage
 */

#include <iostream>
#include <memory>
#include <vector>
#include <string>
#include <thread>
#include <chrono>

#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include "agenkit/patterns/router.hpp"

using namespace agenkit;
using namespace std::chrono_literals;

class SimpleAgent : public Agent {
public:
    explicit SimpleAgent(const std::string& name) : agent_name(name) {}

    std::string name() const override {
        return agent_name;
    }

    std::vector<std::string> capabilities() const override {
        return {"demo"};
    }

    Message process(const Message& message) override {
        std::cout << "   🤖 " << agent_name << " processing..." << std::endl;
        std::this_thread::sleep_for(100ms);

        Message result;
        result.role = "agent";
        result.content = agent_name + " processed: " + message.content;
        return result;
    }

private:
    std::string agent_name;
};

int main() {
    std::cout << "=== Router Pattern Demo ===" << std::endl;

    auto agent1 = std::make_shared<SimpleAgent>("Agent1");
    auto agent2 = std::make_shared<SimpleAgent>("Agent2");
    auto agent3 = std::make_shared<SimpleAgent>("Agent3");

    // Create pattern (adjust based on pattern type)
    // auto pattern = std::make_shared<RouterAgent>(...);

    std::cout << "\n✅ Router pattern example" << std::endl;
    std::cout << "\nNote: This is a minimal template." << std::endl;
    std::cout << "See Python examples for complete implementations." << std::endl;

    return 0;
}
