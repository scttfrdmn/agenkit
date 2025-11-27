/**
 * @file task_example.cpp
 * @brief Example demonstrating Task pattern
 *
 * This example shows one-shot agent execution with lifecycle management,
 * timeout, and retry support.
 */

#include <iostream>
#include "agenkit/patterns/task.hpp"
#include <chrono>
#include <thread>

using namespace agenkit;

// Mock agent that simulates document summarization
class SummarizerAgent : public core::Agent {
private:
    std::chrono::milliseconds processing_time_;

public:
    SummarizerAgent(std::chrono::milliseconds processing_time = std::chrono::milliseconds(100))
        : processing_time_(processing_time) {}

    std::string name() const override { return "summarizer"; }

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override {
        std::string content = message.content_as_str();

        // Simulate processing time
        std::this_thread::sleep_for(processing_time_);

        // Extract document from message
        std::string summary;
        if (content.find("long document") != std::string::npos) {
            summary = "This is a concise summary of the key points from the document.";
        } else {
            summary = "Summary: " + content;
        }

        auto msg = core::Message::with_text("assistant", summary);
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::ok(msg)
        );
    }
};

// Agent that fails occasionally (for retry demo)
class UnreliableAgent : public core::Agent {
private:
    int call_count_;
    int succeed_on_attempt_;

public:
    UnreliableAgent(int succeed_on_attempt = 2)
        : call_count_(0), succeed_on_attempt_(succeed_on_attempt) {}

    std::string name() const override { return "unreliable"; }

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message /* message */) override {
        call_count_++;

        std::cout << "  Attempt #" << call_count_ << "... ";

        if (call_count_ < succeed_on_attempt_) {
            std::cout << "Failed!\n";
            return core::make_ready_future(
                core::Result<core::Message, core::AgentError>::err(
                    core::AgentError(core::AgentErrorType::Internal, "Temporary failure")
                )
            );
        }

        std::cout << "Success!\n";
        auto msg = core::Message::with_text("assistant", "Task completed successfully");
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::ok(msg)
        );
    }
};

// Custom task with cleanup tracking
class TrackedTask : public patterns::Task {
public:
    bool cleanup_executed = false;

    TrackedTask(std::shared_ptr<core::Agent> agent, patterns::TaskConfig config)
        : Task(agent, config) {}

    void cleanup() override {
        std::cout << "  [Cleanup executed]\n";
        cleanup_executed = true;
        Task::cleanup();
    }
};

int main() {
    std::cout << "=== Agenkit C++ Task Pattern Example ===\n\n";

    // Example 1: Basic task execution
    std::cout << "=== Example 1: Basic Task Execution ===\n";
    {
        auto agent = std::make_shared<SummarizerAgent>();
        patterns::Task task(agent);

        std::cout << "Executing one-shot summarization task...\n";

        auto msg = core::Message::with_text(
            "user",
            "Please summarize this long document about AI patterns."
        );

        auto result = task.execute(std::move(msg)).get();

        if (result.is_ok()) {
            std::cout << "Summary: " << result.unwrap().content_as_str() << "\n";
            std::cout << "Task completed: " << (task.is_completed() ? "Yes" : "No") << "\n";
        }

        // Cannot execute again
        auto msg2 = core::Message::with_text("user", "Another task");
        try {
            task.execute(std::move(msg2)).get();
        } catch (const std::runtime_error& e) {
            std::cout << "Expected error: " << e.what() << "\n";
        }
    }

    // Example 2: Task with timeout
    std::cout << "\n=== Example 2: Task with Timeout ===\n";
    {
        // Agent that takes 200ms
        auto slow_agent = std::make_shared<SummarizerAgent>(std::chrono::milliseconds(200));

        patterns::TaskConfig config;
        config.timeout = std::chrono::milliseconds(100); // Timeout at 100ms

        patterns::Task task(slow_agent, config);

        std::cout << "Executing task with 100ms timeout (agent takes 200ms)...\n";

        auto msg = core::Message::with_text("user", "Summarize this");
        auto result = task.execute(std::move(msg)).get();

        if (result.is_err()) {
            std::cout << "Task timed out (as expected)\n";
            std::cout << "Error: " << result.unwrap_err().message() << "\n";
        }
    }

    // Example 3: Task with successful execution under timeout
    std::cout << "\n=== Example 3: Task Completes Before Timeout ===\n";
    {
        auto fast_agent = std::make_shared<SummarizerAgent>(std::chrono::milliseconds(50));

        patterns::TaskConfig config;
        config.timeout = std::chrono::milliseconds(200); // Generous timeout

        patterns::Task task(fast_agent, config);

        std::cout << "Executing task with 200ms timeout (agent takes 50ms)...\n";

        auto msg = core::Message::with_text("user", "Quick summary");
        auto result = task.execute(std::move(msg)).get();

        if (result.is_ok()) {
            std::cout << "Task completed successfully\n";
            std::cout << "Result: " << result.unwrap().content_as_str() << "\n";
        }
    }

    // Example 4: Task with retries
    std::cout << "\n=== Example 4: Task with Retries ===\n";
    {
        auto unreliable = std::make_shared<UnreliableAgent>(2); // Succeeds on 2nd attempt

        patterns::TaskConfig config;
        config.retries = 3; // Allow up to 3 retries (4 total attempts)
        config.retry_delay = std::chrono::milliseconds(50);

        patterns::Task task(unreliable, config);

        std::cout << "Executing task with retries (agent succeeds on 2nd attempt)...\n";

        auto msg = core::Message::with_text("user", "Test");
        auto result = task.execute(std::move(msg)).get();

        if (result.is_ok()) {
            std::cout << "Final result: " << result.unwrap().content_as_str() << "\n";
        }
    }

    // Example 5: Task with cleanup tracking
    std::cout << "\n=== Example 5: Custom Cleanup ===\n";
    {
        auto agent = std::make_shared<SummarizerAgent>();

        patterns::TaskConfig config;
        TrackedTask task(agent, config);

        std::cout << "Executing task with custom cleanup...\n";

        auto msg = core::Message::with_text("user", "Test");
        task.execute(std::move(msg)).get();

        std::cout << "Cleanup was executed: " << (task.cleanup_executed ? "Yes" : "No") << "\n";
    }

    // Example 6: Get result after execution
    std::cout << "\n=== Example 6: Retrieve Result ===\n";
    {
        auto agent = std::make_shared<SummarizerAgent>();
        patterns::Task task(agent);

        std::cout << "Result before execution: "
                  << (task.get_result().has_value() ? "Available" : "None") << "\n";

        auto msg = core::Message::with_text("user", "Summarize");
        task.execute(std::move(msg)).get();

        if (task.get_result().has_value()) {
            std::cout << "Result after execution: "
                      << task.get_result().value().content_as_str() << "\n";
        }
    }

    std::cout << "\n=== Key Insights ===\n";
    std::cout << "1. One-shot semantics: Task can only be executed once\n";
    std::cout << "2. Timeout support: Tasks can have execution time limits\n";
    std::cout << "3. Retry mechanism: Automatic retries with exponential backoff\n";
    std::cout << "4. Lifecycle management: Automatic cleanup after execution\n";
    std::cout << "5. Result retrieval: Access result after completion\n";
    std::cout << "6. Error handling: Clean error propagation on failure\n";

    std::cout << "\n=== Example Complete ===\n";

    return 0;
}
