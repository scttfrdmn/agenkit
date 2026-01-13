/**
 * @file timeout.cpp
 * @brief Timeout middleware implementation
 */

#include "agenkit/middleware/timeout.hpp"
#include <future>

namespace agenkit {
namespace middleware {

std::chrono::milliseconds TimeoutMiddleware::get_timeout_for_message(
    const core::Message& /* message */
) const {
    // TODO: Check message metadata for method-specific timeout
    // For now, just use default timeout
    return config_.default_timeout;
}

std::future<core::Result<core::Message, core::AgentError>>
TimeoutMiddleware::process(core::Message message) {
    metrics_.total_requests++;

    auto start = std::chrono::steady_clock::now();
    auto timeout = get_timeout_for_message(message);

    // Start the async operation
    auto future = agent_->process(message);

    // Wait for the result with timeout
    auto status = future.wait_for(timeout);

    auto end = std::chrono::steady_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);
    metrics_.update_duration(duration.count());

    if (status == std::future_status::timeout) {
        // Timed out
        metrics_.timed_out_requests++;
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::err(
                TimeoutError(timeout)
            )
        );
    }

    // Got result within timeout
    auto result = future.get();

    if (result.is_ok()) {
        metrics_.successful_requests++;
    } else {
        metrics_.failed_requests++;
    }

    return core::make_ready_future(std::move(result));
}

std::future<core::Result<bool, core::AgentError>>
TimeoutMiddleware::process_stream(
    core::Message message,
    std::function<void(core::Message)> on_message,
    std::function<void(core::AgentError)> on_error,
    std::function<void()> on_complete
) {
    metrics_.total_requests++;

    auto start_time = std::make_shared<std::chrono::steady_clock::time_point>(
        std::chrono::steady_clock::now()
    );
    auto timeout = get_timeout_for_message(message);
    auto deadline = std::make_shared<std::chrono::steady_clock::time_point>(
        *start_time + timeout
    );

    // Capture metrics pointer for callbacks
    auto metrics_ptr = &metrics_;
    auto timeout_ms = timeout;

    // Wrap callbacks with timeout checking
    auto wrapped_on_message = [on_message, deadline, metrics_ptr, timeout_ms, start_time](core::Message msg) {
        if (std::chrono::steady_clock::now() > *deadline) {
            // Timeout exceeded
            auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(
                std::chrono::steady_clock::now() - *start_time
            );
            metrics_ptr->timed_out_requests++;
            metrics_ptr->update_duration(duration.count());
            throw TimeoutError(timeout_ms);
        }
        on_message(std::move(msg));
    };

    auto wrapped_on_error = [on_error, metrics_ptr, start_time](core::AgentError error) {
        auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::steady_clock::now() - *start_time
        );
        metrics_ptr->failed_requests++;
        metrics_ptr->update_duration(duration.count());
        on_error(std::move(error));
    };

    auto wrapped_on_complete = [on_complete, metrics_ptr, start_time]() {
        auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::steady_clock::now() - *start_time
        );
        metrics_ptr->successful_requests++;
        metrics_ptr->update_duration(duration.count());
        on_complete();
    };

    // Call underlying agent's stream with wrapped callbacks
    try {
        return agent_->process_stream(
            std::move(message),
            wrapped_on_message,
            wrapped_on_error,
            wrapped_on_complete
        );
    } catch (const std::exception& e) {
        // If streaming setup fails immediately
        on_error(core::AgentError(
            core::AgentErrorType::ProcessingError,
            std::string("Failed to start stream: ") + e.what()
        ));
        return core::make_ready_future(core::Result<bool, core::AgentError>::ok(true));
    }
}

} // namespace middleware
} // namespace agenkit
