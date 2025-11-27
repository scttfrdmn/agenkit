/**
 * @file task.hpp
 * @brief Task pattern for one-shot agent execution with lifecycle management
 *
 * This module provides the Task pattern, which wraps an Agent for single-use
 * execution with automatic resource cleanup, timeout, and retry support.
 */

#ifndef AGENKIT_PATTERNS_TASK_HPP
#define AGENKIT_PATTERNS_TASK_HPP

#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include <chrono>
#include <optional>
#include <memory>

namespace agenkit {
namespace patterns {

/**
 * @brief Configuration for task execution
 */
struct TaskConfig {
    /// Optional timeout for task execution (0 = no timeout)
    std::chrono::milliseconds timeout{0};

    /// Number of retry attempts on failure (0 = no retries)
    int retries{0};

    /// Delay between retry attempts in milliseconds
    std::chrono::milliseconds retry_delay{100};
};

/**
 * @brief One-shot agent execution with lifecycle management
 *
 * A Task wraps an Agent for single-use execution, providing:
 * - Explicit one-shot semantics
 * - Automatic resource cleanup
 * - Timeout support
 * - Retry mechanism with exponential backoff
 * - Prevention of reuse after completion
 *
 * The key distinction from Agent:
 * - **Agent**: Multi-turn conversation with state
 * - **Task**: One-shot execution, then cleanup
 *
 * @example
 * @code
 * auto agent = std::make_shared<MyAgent>();
 * TaskConfig config;
 * config.timeout = std::chrono::seconds(30);
 * config.retries = 2;
 *
 * Task task(agent, config);
 * auto msg = Message::with_text("user", "Summarize this document");
 * auto result = task.execute(std::move(msg)).get();
 *
 * // Cannot execute again - task is completed
 * @endcode
 *
 * Pattern comparison:
 * - Use Task when: Single purpose operation that needs cleanup
 * - Use Agent when: Multi-turn conversation with state
 * - Examples: summarize_document, classify_text, extract_entities
 */
class Task {
public:
    /**
     * @brief Construct a Task
     * @param agent The agent to execute
     * @param config Configuration for execution
     * @throws std::invalid_argument if agent is nullptr
     */
    explicit Task(
        std::shared_ptr<core::Agent> agent,
        TaskConfig config = TaskConfig{}
    );

    /**
     * @brief Execute the task once
     *
     * This method can only be called once per Task instance. After execution
     * completes (successfully or with error), the Task is marked as completed
     * and cannot be reused.
     *
     * @param message Input message for the agent
     * @return Future with the result or error
     * @throws std::runtime_error if the task has already been completed
     */
    std::future<core::Result<core::Message, core::AgentError>>
    execute(core::Message message);

    /**
     * @brief Clean up resources after task completion
     *
     * This method is called automatically after execution. Override in
     * subclasses to add custom cleanup logic.
     */
    virtual void cleanup();

    /**
     * @brief Check if the task has been completed
     * @return True if execute() has been called, false otherwise
     */
    bool is_completed() const;

    /**
     * @brief Get the result of the task execution
     * @return Optional result message if execution completed successfully
     */
    std::optional<core::Message> get_result() const;

    /**
     * @brief Get the current configuration
     * @return Current configuration
     */
    TaskConfig get_config() const;

private:
    std::shared_ptr<core::Agent> agent_;
    TaskConfig config_;
    bool completed_;
    std::optional<core::Message> result_;

    /**
     * @brief Execute with retries
     * @param message Input message
     * @return Result or error
     */
    core::Result<core::Message, core::AgentError>
    execute_with_retries(core::Message message);

    /**
     * @brief Execute with timeout
     * @param message Input message
     * @return Result or error
     */
    core::Result<core::Message, core::AgentError>
    execute_with_timeout(core::Message message);
};

} // namespace patterns
} // namespace agenkit

#endif // AGENKIT_PATTERNS_TASK_HPP
