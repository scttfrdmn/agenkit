/**
 * @file errors.cpp
 * @brief Implementation of error types
 */

#include "agenkit/core/errors.hpp"

namespace agenkit {
namespace core {

AgentError::AgentError(AgentErrorType type, std::string message)
    : std::runtime_error(message)
    , type_(type)
    , message_(std::move(message))
{
}

AgentErrorType AgentError::type() const noexcept {
    return type_;
}

const std::string& AgentError::message() const noexcept {
    return message_;
}

std::string to_string(AgentErrorType type) {
    switch (type) {
        case AgentErrorType::ProcessingError:
            return "ProcessingError";
        case AgentErrorType::Timeout:
            return "Timeout";
        case AgentErrorType::NotFound:
            return "NotFound";
        case AgentErrorType::Transport:
            return "Transport";
        case AgentErrorType::Serialization:
            return "Serialization";
        case AgentErrorType::Http:
            return "Http";
        case AgentErrorType::Internal:
            return "Internal";
        case AgentErrorType::InvalidInput:
            return "InvalidInput";
        default:
            return "Unknown";
    }
}

} // namespace core
} // namespace agenkit
