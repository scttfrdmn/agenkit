/**
 * Human-in-loop Pattern Usage Example
 *
 * Human approval gates for high-stakes decisions
 *
 * Use cases:
 * - Financial approvals
 * - Content moderation
 * - Critical system changes
 *
 * Build: cd build && cmake .. && make
 * Run: ./examples/human-in-loop_usage
 */

#include <iostream>
#include <memory>
#include <vector>
#include <string>
#include <thread>
#include <chrono>

#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include "agenkit/patterns/human_in_loop.hpp"

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
    std::cout << "=== Human-in-loop Pattern Demo ===" << std::endl;

    auto agent1 = std::make_shared<SimpleAgent>("Agent1");
    auto agent2 = std::make_shared<SimpleAgent>("Agent2");
    auto agent3 = std::make_shared<SimpleAgent>("Agent3");

    // Create pattern (adjust based on pattern type)
    // auto pattern = std::make_shared<HumaninloopAgent>(...);

    std::cout << "\n✅ Human-in-loop pattern example" << std::endl;
    std::cout << "\nNote: This is a minimal template." << std::endl;
    std::cout << "See Python examples for complete implementations." << std::endl;

    return 0;
}
