/**
 * Safety framework for agent operations.
 *
 * Provides comprehensive security features:
 * - Input validation and prompt injection defense
 * - Output validation and sensitive data redaction
 * - Permission-based access control (RBAC)
 * - Anomaly detection and monitoring
 * - Security audit logging
 *
 * Example:
 *   auto detector = std::make_shared<PromptInjectionDetector>();
 *   auto filter = std::make_shared<ContentFilter>();
 *   auto safe_agent = std::make_shared<InputValidationMiddleware>(
 *       base_agent, detector, filter, true);
 */

#pragma once

#include "agenkit/infrastructure/anomaly.hpp"
#include "agenkit/infrastructure/audit.hpp"
#include "agenkit/infrastructure/permissions.hpp"
#include "agenkit/infrastructure/validation.hpp"

// Main safety module export
namespace agenkit {
namespace infrastructure {

/**
 * Safety framework version.
 */
constexpr const char* SAFETY_VERSION = "0.47.0";

}  // namespace infrastructure
}  // namespace agenkit
