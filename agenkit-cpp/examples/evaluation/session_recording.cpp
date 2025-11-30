/**
 * @file session_recording.cpp
 * @brief Session recording and replay example
 *
 * Demonstrates:
 * - Recording agent interactions automatically
 * - Storing recordings to file or memory
 * - Replaying sessions through different agent versions
 * - Comparing replay results for A/B testing
 *
 * Compile: See examples/CMakeLists.txt
 * Run: ./session_recording
 */

#include "agenkit/evaluation/recorder.hpp"
#include "agenkit/adapters/echo_agent.hpp"
#include <iostream>
#include <memory>

using namespace agenkit;
using namespace agenkit::evaluation;

int main() {
    std::cout << "Session Recording Example" << std::endl;
    std::cout << "=========================" << std::endl << std::endl;

    // Step 1: Create storage and recorder
    std::cout << "Step 1: Creating Session Recorder" << std::endl;
    auto storage = std::make_shared<InMemoryRecordingStorage>();
    SessionRecorder recorder(storage);
    std::cout << "✓ Created recorder with in-memory storage" << std::endl << std::endl;

    // Step 2: Wrap an agent for recording
    std::cout << "Step 2: Wrapping Agent for Recording" << std::endl;
    auto echo_agent = std::make_shared<adapters::EchoAgent>();
    auto wrapped_agent = recorder.wrap(echo_agent);
    std::cout << "✓ Wrapped echo agent for automatic recording" << std::endl << std::endl;

    // Step 3: Use the agent (automatically recorded)
    std::cout << "Step 3: Using Agent (Automatically Recorded)" << std::endl;
    recorder.start_session("test-session", "Echo", nlohmann::json::object());

    std::vector<std::string> test_inputs = {
        "Hello, world!",
        "How are you?",
        "Test message 3"
    };

    for (const auto& input : test_inputs) {
        auto message = core::Message::with_text("user", input);
        message.with_metadata("session_id", "test-session");

        auto future = wrapped_agent->process(message);
        auto result = future.get();

        if (result.is_ok()) {
            std::cout << "✓ Processed: " << input << std::endl;
        }
    }
    std::cout << std::endl;

    // Step 4: Finalize and save recording
    std::cout << "Step 4: Finalizing Recording" << std::endl;
    auto recording = recorder.finalize_session("test-session");
    std::cout << "✓ Recording saved" << std::endl;
    std::cout << "  Session ID: " << recording.session_id() << std::endl;
    std::cout << "  Interactions: " << recording.interaction_count() << std::endl;
    std::cout << "  Duration: " << recording.duration_seconds() << "s" << std::endl << std::endl;

    // Step 5: Replay session
    std::cout << "Step 5: Replaying Session" << std::endl;
    SessionReplay replay;
    auto replay_results = replay.replay(recording, echo_agent, "replay-1");
    std::cout << "✓ Replay completed" << std::endl;
    std::cout << "  Interactions: " << replay_results["interactions"].size() << std::endl;
    std::cout << "  Total latency: " << replay_results["total_latency_ms"] << "ms" << std::endl;
    std::cout << "  Errors: " << replay_results["error_count"] << std::endl << std::endl;

    std::cout << "Session Recording Complete!" << std::endl;
    std::cout << "\nUse Cases:" << std::endl;
    std::cout << "- Production debugging (replay failed sessions)" << std::endl;
    std::cout << "- A/B testing (replay with different agent versions)" << std::endl;
    std::cout << "- Regression testing (ensure consistency)" << std::endl;
    std::cout << "- Performance analysis (compare latencies)" << std::endl;

    return 0;
}
