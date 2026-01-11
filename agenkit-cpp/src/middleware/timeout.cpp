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

} // namespace middleware
} // namespace agenkit
