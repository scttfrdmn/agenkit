/**
 * @file planning_example.cpp
 * @brief Example demonstrating Planning pattern
 */

#include <iostream>
#include "agenkit/patterns/planning.hpp"

using namespace agenkit;

// Mock planner LLM that creates plans
class PlannerLLM : public core::Agent {
public:
    std::string name() const override { return "planner_llm"; }

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override {
        std::string task = message.content_as_str();
        std::string plan;

        if (task.find("team event") != std::string::npos) {
            plan = "1. Choose date and venue\n"
                   "2. Create invitation list\n"
                   "3. Send invitations\n"
                   "4. Arrange catering\n"
                   "5. Prepare event materials";
        } else if (task.find("research report") != std::string::npos) {
            plan = "1. Research topic background\n"
                   "2. Collect data and sources\n"
                   "3. Analyze findings\n"
                   "4. Write draft\n"
                   "5. Review and edit\n"
                   "6. Finalize report";
        } else {
            plan = "1. Analyze requirements\n"
                   "2. Create approach\n"
                   "3. Execute plan\n"
                   "4. Verify results";
        }

        auto msg = core::Message::with_text("assistant", plan);
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::ok(msg)
        );
    }
};

int main() {
    std::cout << "=== Agenkit C++ Planning Example ===\n\n";

    // Example 1: Plan for organizing event
    std::cout << "=== Example 1: Plan Team Event ===\n";
    {
        auto planner = std::make_shared<PlannerLLM>();
        patterns::PlanningAgent agent(planner, 10);

        auto msg = core::Message::with_text("user", "Organize a team event");
        auto result = agent.process(std::move(msg)).get();

        if (result.is_ok()) {
            std::cout << result.unwrap().content_as_str() << "\n";

            auto plan = agent.get_plan();
            if (plan.has_value()) {
                std::cout << "\n=== Plan Details ===\n";
                std::cout << "Goal: " << plan->goal << "\n";
                std::cout << "Total steps: " << plan->steps.size() << "\n";
                std::cout << "Progress: " << plan->get_progress() << "%\n";
            }
        }
    }

    // Example 2: Research report plan
    std::cout << "\n\n=== Example 2: Create Research Report ===\n";
    {
        auto planner = std::make_shared<PlannerLLM>();
        patterns::PlanningAgent agent(planner, 10);

        auto msg = core::Message::with_text("user", "Create a research report on AI");
        auto result = agent.process(std::move(msg)).get();

        if (result.is_ok()) {
            std::cout << result.unwrap().content_as_str() << "\n";
        }
    }

    std::cout << "\n=== Key Insights ===\n";
    std::cout << "1. Plan creation: Break tasks into steps\n";
    std::cout << "2. Sequential execution: Steps executed in order\n";
    std::cout << "3. Progress tracking: Monitor completion percentage\n";
    std::cout << "4. Step status: Track pending/in-progress/completed/failed\n";

    std::cout << "\n=== Example Complete ===\n";
    return 0;
}
