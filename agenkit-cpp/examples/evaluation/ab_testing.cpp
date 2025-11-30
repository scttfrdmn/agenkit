/**
 * @file ab_testing.cpp
 * @brief A/B testing example using session replay
 */

#include "agenkit/evaluation/recorder.hpp"
#include "agenkit/adapters/echo_agent.hpp"
#include <iostream>
#include <memory>

using namespace agenkit;
using namespace agenkit::evaluation;

int main() {
    std::cout << "A/B Testing Example" << std::endl;
    std::cout << "===================" << std::endl << std::endl;

    // Step 1: Record baseline sessions
    std::cout << "Step 1: Recording Baseline Sessions" << std::endl;
    auto storage = std::make_shared<InMemoryRecordingStorage>();
    SessionRecorder recorder(storage);

    auto agent_v1 = std::make_shared<adapters::EchoAgent>("AgentV1");
    auto wrapped_v1 = recorder.wrap(agent_v1);

    recorder.start_session("ab-test", "AgentV1", nlohmann::json::object());

    std::vector<std::string> test_cases = {
        "Test case 1",
        "Test case 2",
        "Test case 3"
    };

    for (const auto& test : test_cases) {
        auto msg = core::Message::with_text("user", test);
        msg.with_metadata("session_id", "ab-test");
        auto future = wrapped_v1->process(msg);
        auto result = future.get();  // Consume result
        (void)result;
    }

    auto recording = recorder.finalize_session("ab-test");
    std::cout << "✓ Recorded " << recording.interaction_count() << " interactions" << std::endl << std::endl;

    // Step 2: Replay with Version A
    std::cout << "Step 2: Replaying with Version A" << std::endl;
    SessionReplay replay;
    auto agent_a = std::make_shared<adapters::EchoAgent>("AgentA");
    auto results_a = replay.replay(recording, agent_a);
    std::cout << "✓ Version A latency: " << results_a["total_latency_ms"] << "ms" << std::endl << std::endl;

    // Step 3: Replay with Version B
    std::cout << "Step 3: Replaying with Version B" << std::endl;
    auto agent_b = std::make_shared<adapters::EchoAgent>("AgentB");
    auto results_b = replay.replay(recording, agent_b);
    std::cout << "✓ Version B latency: " << results_b["total_latency_ms"] << "ms" << std::endl << std::endl;

    // Step 4: Compare results
    std::cout << "Step 4: Comparing Results" << std::endl;
    auto comparison = replay.compare(results_a, results_b);

    std::cout << "  Interaction count: " << comparison["interaction_count"] << std::endl;
    std::cout << "  Latency diff: " << comparison["latency_diff_ms"] << "ms" << std::endl;
    std::cout << "  Latency diff: " << comparison["latency_diff_percent"] << "%" << std::endl;
    std::cout << "  Output differences: " << comparison["output_differences"].size() << std::endl << std::endl;

    std::cout << "A/B testing helps validate changes before production rollout!" << std::endl;
    std::cout << "\nBenefits:" << std::endl;
    std::cout << "- Test new agent versions on real traffic" << std::endl;
    std::cout << "- Compare performance and quality" << std::endl;
    std::cout << "- Identify regressions early" << std::endl;
    std::cout << "- Make data-driven deployment decisions" << std::endl;

    return 0;
}
