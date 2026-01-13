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
#include <string>
#include <vector>
#include <future>
#include <memory>
#include <functional>
#include <atomic>
#include <thread>

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
