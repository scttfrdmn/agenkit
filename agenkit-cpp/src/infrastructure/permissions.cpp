/**
 * Implementation of permission-based access control and sandboxing.
 */

#include "agenkit/infrastructure/permissions.hpp"

#include <algorithm>
#include <iostream>
#include <sstream>

namespace agenkit {
namespace infrastructure {

// ============================================================================
// Role Permissions
// ============================================================================

std::set<Permission> get_role_permissions(Role role) {
  switch (role) {
    case Role::ADMIN:
      return {Permission::READ_FILES,
              Permission::WRITE_FILES,
              Permission::DELETE_FILES,
              Permission::EXECUTE_COMMANDS,
              Permission::EXECUTE_SHELL,
              Permission::QUERY_DATABASE,
              Permission::WRITE_DATABASE,
              Permission::MAKE_HTTP_REQUESTS,
              Permission::MAKE_EXTERNAL_API_CALLS,
              Permission::MANAGE_USERS,
              Permission::MANAGE_AGENTS,
              Permission::ACCESS_SECRETS,
              Permission::USE_TOOLS,
              Permission::USE_DANGEROUS_TOOLS};

    case Role::USER:
      return {Permission::READ_FILES,     Permission::WRITE_FILES,
              Permission::EXECUTE_COMMANDS, Permission::QUERY_DATABASE,
              Permission::MAKE_HTTP_REQUESTS, Permission::USE_TOOLS};

    case Role::READONLY:
      return {Permission::READ_FILES, Permission::QUERY_DATABASE,
              Permission::USE_TOOLS};

    case Role::RESTRICTED:
      return {Permission::READ_FILES, Permission::USE_TOOLS};
  }

  return {};
}

// ============================================================================
// Sandbox
// ============================================================================

Sandbox::Sandbox()
    : Sandbox(Config{}) {}

Sandbox::Sandbox(const Config& config)
    : allowed_paths_(config.allowed_paths),
      denied_paths_(config.denied_paths),
      allowed_commands_(config.allowed_commands),
      denied_commands_(config.denied_commands),
      allowed_sql_operations_(config.allowed_sql_operations),
      allowed_domains_(config.allowed_domains),
      denied_domains_(config.denied_domains),
      max_file_size_(config.max_file_size),
      max_execution_time_(config.max_execution_time),
      max_memory_mb_(config.max_memory_mb) {}

std::pair<bool, std::string> Sandbox::is_path_allowed(
    const std::string& path) const {
  try {
    std::filesystem::path resolved = std::filesystem::absolute(path);

    // Check denied paths first
    for (const auto& denied : denied_paths_) {
      std::filesystem::path denied_resolved = std::filesystem::absolute(denied);
      // Check if resolved path starts with denied path
      auto [resolved_it, denied_it] =
          std::mismatch(resolved.begin(), resolved.end(), denied_resolved.begin(),
                        denied_resolved.end());
      if (denied_it == denied_resolved.end()) {
        return {false, "Path is in denied directory: " + denied};
      }
    }

    // If allowed_paths specified, must be under one of them
    if (!allowed_paths_.empty()) {
      for (const auto& allowed : allowed_paths_) {
        std::filesystem::path allowed_resolved =
            std::filesystem::absolute(allowed);
        auto [resolved_it, allowed_it] = std::mismatch(
            resolved.begin(), resolved.end(), allowed_resolved.begin(),
            allowed_resolved.end());
        if (allowed_it == allowed_resolved.end()) {
          return {true, ""};
        }
      }

      return {false, "Path is outside allowed directories"};
    }

    // No allowed_paths specified, just check denied
    return {true, ""};
  } catch (const std::exception& e) {
    return {false, std::string("Path validation error: ") + e.what()};
  }
}

std::pair<bool, std::string> Sandbox::is_command_allowed(
    const std::string& command) const {
  // Extract command name (first word)
  std::istringstream iss(command);
  std::string cmd_name;
  iss >> cmd_name;

  if (cmd_name.empty()) {
    return {false, "Empty command"};
  }

  // Check denied commands first
  if (denied_commands_.find(cmd_name) != denied_commands_.end()) {
    return {false, "Command is denied: " + cmd_name};
  }

  // Check allowed commands
  if (!allowed_commands_.empty() &&
      allowed_commands_.find(cmd_name) == allowed_commands_.end()) {
    return {false, "Command not in allowed list: " + cmd_name};
  }

  return {true, ""};
}

std::pair<bool, std::string> Sandbox::is_sql_operation_allowed(
    const std::string& sql) const {
  // Extract SQL operation (first word, uppercase)
  std::istringstream iss(sql);
  std::string operation;
  iss >> operation;

  if (operation.empty()) {
    return {false, "Empty SQL query"};
  }

  // Convert to uppercase
  std::transform(operation.begin(), operation.end(), operation.begin(),
                 [](unsigned char c) { return std::toupper(c); });

  if (allowed_sql_operations_.find(operation) ==
      allowed_sql_operations_.end()) {
    return {false, "SQL operation not allowed: " + operation};
  }

  return {true, ""};
}

std::pair<bool, std::string> Sandbox::is_domain_allowed(
    const std::string& domain) const {
  // Check denied domains first
  if (denied_domains_.find(domain) != denied_domains_.end()) {
    return {false, "Domain is denied: " + domain};
  }

  // If allowed_domains specified, must be in list
  if (!allowed_domains_.empty() &&
      allowed_domains_.find(domain) == allowed_domains_.end()) {
    return {false, "Domain not in allowed list: " + domain};
  }

  return {true, ""};
}

// ============================================================================
// PermissionMiddleware
// ============================================================================

PermissionMiddleware::PermissionMiddleware(
    std::shared_ptr<core::Agent> agent, Role role,
    std::set<Permission> custom_permissions,
    std::shared_ptr<Sandbox> sandbox)
    : agent_(agent),
      role_(role),
      permissions_(custom_permissions.empty() ? get_role_permissions(role)
                                              : custom_permissions),
      sandbox_(sandbox ? sandbox : std::make_shared<Sandbox>()) {}

std::string PermissionMiddleware::name() const { return agent_->name(); }

bool PermissionMiddleware::has_permission(Permission permission) const {
  return permissions_.find(permission) != permissions_.end();
}

void PermissionMiddleware::check_permission(Permission permission) const {
  if (!has_permission(permission)) {
    std::string role_str;
    switch (role_) {
      case Role::ADMIN:
        role_str = "admin";
        break;
      case Role::USER:
        role_str = "user";
        break;
      case Role::READONLY:
        role_str = "readonly";
        break;
      case Role::RESTRICTED:
        role_str = "restricted";
        break;
    }

    throw core::AgentError(core::AgentErrorType::InvalidInput,
                           "Permission denied (role: " + role_str + ")");
  }
}

std::future<core::Result<core::Message, core::AgentError>>
PermissionMiddleware::process(core::Message message) {
  return std::async(std::launch::async, [this, message]() mutable {
    try {
      // Basic permission check
      check_permission(Permission::USE_TOOLS);

      // Check for dangerous operations in message content
      std::string content_str = message.content();
      std::string content_lower = content_str;
      std::transform(content_lower.begin(), content_lower.end(),
                     content_lower.begin(),
                     [](unsigned char c) { return std::tolower(c); });

      // Detect file operations
      if (content_lower.find("read file") != std::string::npos ||
          content_lower.find("write file") != std::string::npos ||
          content_lower.find("delete file") != std::string::npos) {
        if (content_lower.find("delete") != std::string::npos) {
          check_permission(Permission::DELETE_FILES);
        } else if (content_lower.find("write") != std::string::npos) {
          check_permission(Permission::WRITE_FILES);
        } else {
          check_permission(Permission::READ_FILES);
        }
      }

      // Detect command execution
      if (content_lower.find("execute") != std::string::npos ||
          content_lower.find("run command") != std::string::npos ||
          content_lower.find("shell") != std::string::npos) {
        if (content_lower.find("shell") != std::string::npos) {
          check_permission(Permission::EXECUTE_SHELL);
        } else {
          check_permission(Permission::EXECUTE_COMMANDS);
        }
      }

      // Detect database operations
      std::vector<std::string> db_write_keywords = {
          "insert", "update", "delete", "drop", "alter", "create table"};
      bool is_db_write = false;
      for (const auto& kw : db_write_keywords) {
        if (content_lower.find(kw) != std::string::npos) {
          is_db_write = true;
          break;
        }
      }

      if (is_db_write) {
        check_permission(Permission::WRITE_DATABASE);
      } else if (content_lower.find("query") != std::string::npos ||
                 content_lower.find("database") != std::string::npos ||
                 content_lower.find("sql") != std::string::npos ||
                 content_lower.find("select") != std::string::npos ||
                 content_lower.find("from") != std::string::npos) {
        check_permission(Permission::QUERY_DATABASE);
      }

      // Process with wrapped agent
      return agent_->process(std::move(message)).get();

    } catch (const core::AgentError& e) {
      return core::Result<core::Message, core::AgentError>::err(e);
    } catch (const std::exception& e) {
      return core::Result<core::Message, core::AgentError>::err(
          core::AgentError(core::AgentErrorType::Internal, e.what()));
    }
  });
}

}  // namespace infrastructure
}  // namespace agenkit
