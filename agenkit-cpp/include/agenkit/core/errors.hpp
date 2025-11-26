/**
 * @file errors.hpp
 * @brief Error types for agent operations
 */

#ifndef AGENKIT_CORE_ERRORS_HPP
#define AGENKIT_CORE_ERRORS_HPP

#include <string>
#include <exception>
#include <stdexcept>

namespace agenkit {
namespace core {

/**
 * @brief Error type categories for agent operations
 */
enum class AgentErrorType {
    ProcessingError,  ///< Error during agent processing
    Timeout,          ///< Operation timed out
    NotFound,         ///< Agent or resource not found
    Transport,        ///< Network/transport error
    Serialization,    ///< JSON serialization/deserialization error
    Http,             ///< HTTP-specific error
    Internal,         ///< Internal error
    InvalidInput      ///< Invalid input provided
};

/**
 * @brief Exception class for agent errors
 *
 * Provides detailed error information including type and message.
 *
 * @example
 * @code
 * try {
 *     agent.process(message);
 * } catch (const AgentError& e) {
 *     if (e.type() == AgentErrorType::Timeout) {
 *         // Handle timeout
 *     }
 * }
 * @endcode
 */
class AgentError : public std::runtime_error {
public:
    /**
     * @brief Construct an agent error
     * @param type Error type
     * @param message Error message
     */
    AgentError(AgentErrorType type, std::string message);

    /**
     * @brief Get error type
     * @return Error type enum value
     */
    AgentErrorType type() const noexcept;

    /**
     * @brief Get error message
     * @return Error message
     */
    const std::string& message() const noexcept;

private:
    AgentErrorType type_;
    std::string message_;
};

/**
 * @brief Convert error type to string
 * @param type Error type
 * @return String representation of error type
 */
std::string to_string(AgentErrorType type);

} // namespace core
} // namespace agenkit

#endif // AGENKIT_CORE_ERRORS_HPP
