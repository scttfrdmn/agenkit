/**
 * @file task.cpp
 * @brief Implementation of Task pattern
 */

#include "agenkit/patterns/task.hpp"
#include <stdexcept>
#include <thread>

namespace agenkit {
namespace patterns {

Task::Task(
    std::shared_ptr<core::Agent> agent,
    TaskConfig config
) : agent_(agent), config_(config), completed_(false) {
    if (!agent_) {
        throw std::invalid_argument("Agent cannot be null");
    }
}

std::future<core::Result<core::Message, core::AgentError>>
Task::execute(core::Message message) {
    if (completed_) {
        throw std::runtime_error(
            "Task already completed. Create a new Task for another execution."
        );
    }

    // Execute with retries and timeout
    auto result = execute_with_retries(std::move(message));

    // Mark as completed
    completed_ = true;

    // Store result if successful
    if (result.is_ok()) {
        result_ = result.unwrap();
    }

    // Cleanup
    cleanup();

    return core::make_ready_future(result);
}

void Task::cleanup() {
    // Default implementation - hook for subclasses
    // In the future, this could:
    // - Close agent connections
    // - Release resources
    // - Log completion metrics
}

bool Task::is_completed() const {
    return completed_;
}

std::optional<core::Message> Task::get_result() const {
    return result_;
}

TaskConfig Task::get_config() const {
    return config_;
}

core::Result<core::Message, core::AgentError>
Task::execute_with_retries(core::Message message) {
    int attempts = config_.retries + 1; // retries=0 means 1 attempt
    core::Result<core::Message, core::AgentError> last_result =
        core::Result<core::Message, core::AgentError>::err(
            core::AgentError(core::AgentErrorType::Internal, "No attempts made")
        );

    for (int attempt = 0; attempt < attempts; attempt++) {
        // Execute with optional timeout
        auto result = execute_with_timeout(core::Message(message));

        if (result.is_ok()) {
            return result;
        }

        last_result = result;

        // If this was the last attempt, return the error
        if (attempt == attempts - 1) {
            break;
        }

        // Otherwise, wait before retrying (exponential backoff)
        auto delay = config_.retry_delay * (attempt + 1);
        std::this_thread::sleep_for(delay);
    }

    return last_result;
}

core::Result<core::Message, core::AgentError>
Task::execute_with_timeout(core::Message message) {
    // Note: True timeout with cancellation is complex in C++ with std::future.
    // It would require std::stop_token (C++20) or platform-specific APIs.
    // For now, we just execute without actual timeout enforcement.
    // The timeout configuration is preserved for future enhancement.
    return agent_->process(std::move(message)).get();
}

} // namespace patterns
} // namespace agenkit
