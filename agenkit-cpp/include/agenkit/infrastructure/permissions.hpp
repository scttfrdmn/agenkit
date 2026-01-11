/**
 * Permission-based access control and sandboxing.
 *
 * Provides:
 * - Role-Based Access Control (RBAC)
 * - Permission checks before agent actions
 * - Sandboxing (allowed paths, commands, operations)
 * - Resource constraints
 */

#pragma once

#include <filesystem>
#include <future>
#include <memory>
#include <set>
#include <string>
#include <unordered_map>

#include "agenkit/core/agent.hpp"
#include "agenkit/core/errors.hpp"
#include "agenkit/core/message.hpp"
#include "agenkit/core/result.hpp"

namespace agenkit {
namespace infrastructure {

/**
 * System permissions for agents.
 */
enum class Permission {
  // File system
  READ_FILES,
  WRITE_FILES,
  DELETE_FILES,

  // Command execution
  EXECUTE_COMMANDS,
  EXECUTE_SHELL,

  // Database
  QUERY_DATABASE,
  WRITE_DATABASE,

  // Network
  MAKE_HTTP_REQUESTS,
  MAKE_EXTERNAL_API_CALLS,

  // System
  MANAGE_USERS,
  MANAGE_AGENTS,
  ACCESS_SECRETS,

  // Tools
  USE_TOOLS,
  USE_DANGEROUS_TOOLS
};

/**
 * Predefined roles with permission sets.
 */
enum class Role { ADMIN, USER, READONLY, RESTRICTED };

/**
 * Get permissions for a role.
 */
std::set<Permission> get_role_permissions(Role role);

/**
 * Defines sandboxed environment for agent execution.
 *
 * Specifies:
 * - Allowed file paths
 * - Allowed commands
 * - Allowed database operations
 * - Allowed API endpoints
 * - Resource limits
 */
class Sandbox {
 public:
  /**
   * Configuration for sandbox.
   */
  struct Config {
    std::set<std::string> allowed_paths;
    std::set<std::string> denied_paths = {"/etc", "/sys", "/proc"};
    std::set<std::string> allowed_commands = {"ls", "cat", "grep", "git",
                                               "python"};
    std::set<std::string> denied_commands = {"rm", "sudo", "chmod", "chown"};
    std::set<std::string> allowed_sql_operations = {"SELECT", "EXPLAIN"};
    std::set<std::string> allowed_domains;
    std::set<std::string> denied_domains = {"localhost", "127.0.0.1",
                                             "0.0.0.0"};
    size_t max_file_size = 10 * 1024 * 1024;  // 10MB
    int max_execution_time = 30;              // seconds
    size_t max_memory_mb = 512;               // MB
  };

  Sandbox();
  explicit Sandbox(const Config& config);

  /**
   * Check if path is within sandbox.
   *
   * @return pair of (is_allowed, error_message)
   */
  std::pair<bool, std::string> is_path_allowed(
      const std::string& path) const;

  /**
   * Check if command is allowed in sandbox.
   *
   * @return pair of (is_allowed, error_message)
   */
  std::pair<bool, std::string> is_command_allowed(
      const std::string& command) const;

  /**
   * Check if SQL operation is allowed.
   *
   * @return pair of (is_allowed, error_message)
   */
  std::pair<bool, std::string> is_sql_operation_allowed(
      const std::string& sql) const;

  /**
   * Check if domain is allowed for network requests.
   *
   * @return pair of (is_allowed, error_message)
   */
  std::pair<bool, std::string> is_domain_allowed(
      const std::string& domain) const;

  size_t max_file_size() const { return max_file_size_; }
  int max_execution_time() const { return max_execution_time_; }
  size_t max_memory_mb() const { return max_memory_mb_; }

 private:
  std::set<std::string> allowed_paths_;
  std::set<std::string> denied_paths_;
  std::set<std::string> allowed_commands_;
  std::set<std::string> denied_commands_;
  std::set<std::string> allowed_sql_operations_;
  std::set<std::string> allowed_domains_;
  std::set<std::string> denied_domains_;
  size_t max_file_size_;
  int max_execution_time_;
  size_t max_memory_mb_;
};

/**
 * Middleware for permission checks and sandboxing.
 *
 * Enforces:
 * - Role-based permissions
 * - Sandbox constraints
 * - Resource limits
 */
class PermissionMiddleware : public core::Agent {
 public:
  /**
   * Create permission middleware.
   *
   * @param agent Agent to wrap
   * @param role User role
   * @param custom_permissions Custom permission set (optional)
   * @param sandbox Sandbox configuration (optional)
   */
  PermissionMiddleware(
      std::shared_ptr<core::Agent> agent, Role role = Role::USER,
      std::set<Permission> custom_permissions = {},
      std::shared_ptr<Sandbox> sandbox = nullptr);

  std::string name() const override;
  std::future<core::Result<core::Message, core::AgentError>> process(
      core::Message message) override;

  /**
   * Check if agent has permission.
   */
  bool has_permission(Permission permission) const;

 private:
  std::shared_ptr<core::Agent> agent_;
  Role role_;
  std::set<Permission> permissions_;
  std::shared_ptr<Sandbox> sandbox_;

  void check_permission(Permission permission) const;
};

}  // namespace infrastructure
}  // namespace agenkit
