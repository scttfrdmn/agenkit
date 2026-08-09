/**
 * @file agent.hpp
 * @brief Core Agent interface and abstractions
 *
 * This module defines the core Agent interface that all agents must implement,
 * following the same design as Python, Go, TypeScript, and Rust implementations.
 */

#ifndef AGENKIT_CORE_AGENT_HPP
#define AGENKIT_CORE_AGENT_HPP

#include "agenkit/core/message.hpp"
#include "agenkit/core/errors.hpp"
#include "agenkit/core/result.hpp"
#include <nlohmann/json.hpp>
#include <string>
#include <vector>
#include <future>
#include <memory>
#include <functional>
#include <atomic>
#include <thread>
#include <chrono>
#include <ctime>
#include <iomanip>
#include <sstream>

namespace agenkit {
namespace core {

/**
 * @brief Core Agent interface - minimal contract for agent communication
 *
 * Design decisions:
 * - Only 2 required methods (name, process)
 * - Async process using std::future for portability
 * - No state in interface (agents manage their own state)
 * - Virtual interface for polymorphism
 *
 * @example
 * @code
 * class SimpleAgent : public Agent {
 * public:
 *     std::string name() const override {
 *         return "simple";
 *     }
 *
 *     std::future<Result<Message, AgentError>>
 *     process(Message message) override {
 *         auto response = Message::with_text(
 *             "assistant",
 *             "Processed: " + message.content_as_str()
 *         );
 *         return make_ready_future(Result<Message, AgentError>::ok(response));
 *     }
 * };
 * @endcode
 */
class Agent {
public:
    virtual ~Agent() = default;

    /**
     * @brief Agent identifier
     * @return Agent name as string
     */
    virtual std::string name() const = 0;

    /**
     * @brief Process a message and return a response
     *
     * This is the primary method for synchronous request-response interactions.
     * The method returns a future to support async operations.
     *
     * @param message Input message
     * @return Future containing Result<Message, AgentError>
     */
    virtual std::future<Result<Message, AgentError>>
    process(Message message) = 0;

    /**
     * @brief What this agent can do (optional)
     *
     * Returns a list of capabilities this agent supports.
     * Override to provide specific capabilities.
     *
     * @return Vector of capability strings
     */
    virtual std::vector<std::string> capabilities() const {
        return {};
    }

    /**
     * @brief Examine agent's internal state, memory, and capabilities (optional)
     *
     * This is introspection (examining "what I know"), not reflection
     * (analyzing "how I did"). Returns a snapshot of current internal state.
     *
     * Introspection is useful for:
     * - Debugging: Examine agent state during development
     * - Monitoring: Track agent state in production
     * - Coordination: Agents can inspect each other's capabilities
     * - Testing: Verify agent state in tests
     * - Explainability: Understand what an agent "knows"
     *
     * @return JSON object mirroring the other cores' IntrospectionResult shape:
     *         `agent_name`, `capabilities`, `timestamp` (ISO 8601 UTC),
     *         `memory_state` (null unless overridden), `internal_state`
     *         (empty object unless overridden), and `metadata` (empty object).
     *
     * @note Default implementation returns `name()` and `capabilities()` with
     *       `memory_state: null` and empty `internal_state`/`metadata` objects.
     *       Override to report agent-specific memory or internal state, e.g.:
     * @code
     * nlohmann::json introspect() const override {
     *     auto result = Agent::introspect();
     *     result["internal_state"]["messages_processed"] = message_count_;
     *     return result;
     * }
     * @endcode
     */
    virtual nlohmann::json introspect() const {
        nlohmann::json result;
        result["agent_name"] = name();
        result["capabilities"] = capabilities();
        result["timestamp"] = current_timestamp_iso8601();
        result["memory_state"] = nullptr;
        result["internal_state"] = nlohmann::json::object();
        result["metadata"] = nlohmann::json::object();
        return result;
    }

    /**
     * @brief Process a message with streaming response (optional)
     *
     * This method enables streaming responses where the agent can return
     * multiple message chunks over time. The implementation uses callbacks
     * to deliver messages and errors asynchronously.
     *
     * @param message Input message
     * @param on_message Callback invoked for each message chunk
     * @param on_error Callback invoked on error (terminates stream)
     * @param on_complete Callback invoked when stream completes successfully
     *
     * @return Future that completes when streaming starts (true = started, false/error = not supported)
     *
     * @note Default implementation calls on_error indicating no streaming support
     * @note Callbacks may be invoked from background threads
     *
     * @example
     * @code
     * agent->process_stream(
     *     message,
     *     [](Message chunk) { std::cout << "Chunk: " << chunk.content_as_str() << "\n"; },
     *     [](AgentError error) { std::cerr << "Error: " << error.message() << "\n"; },
     *     []() { std::cout << "Stream complete\n"; }
     * );
     * @endcode
     */
    virtual std::future<Result<bool, AgentError>>
    process_stream(
        Message message,
        std::function<void(Message)> on_message,
        std::function<void(AgentError)> on_error,
        std::function<void()> on_complete
    ) {
        (void)message;
        (void)on_message;
        (void)on_complete;

        // Default: streaming not supported
        on_error(AgentError(
            AgentErrorType::ProcessingError,
            "streaming not supported by this agent"
        ));

        std::promise<Result<bool, AgentError>> promise;
        promise.set_value(Result<bool, AgentError>::ok(true));
        return promise.get_future();
    }

private:
    /**
     * @brief Current UTC time formatted as ISO 8601 (used by the default introspect())
     * @return Timestamp string, e.g. "2026-08-08T12:34:56Z"
     */
    static std::string current_timestamp_iso8601() {
        auto now = std::chrono::system_clock::now();
        auto time_t_now = std::chrono::system_clock::to_time_t(now);
        std::stringstream ss;
        ss << std::put_time(std::gmtime(&time_t_now), "%Y-%m-%dT%H:%M:%SZ");
        return ss.str();
    }
};

/**
 * @brief Helper to create a ready future (immediate result)
 * @tparam T Type of the value in the future
 * @param value Value to wrap in future
 * @return Future containing the value
 */
template<typename T>
std::future<T> make_ready_future(T value) {
    std::promise<T> promise;
    promise.set_value(std::move(value));
    return promise.get_future();
}

} // namespace core
} // namespace agenkit

#endif // AGENKIT_CORE_AGENT_HPP
