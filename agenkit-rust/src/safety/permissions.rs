//! Permission-based access control (RBAC) and sandboxing.

use crate::core::{Agent, AgentError, IntrospectionResult, Message};
use crate::safety::errors::PermissionDeniedError;
use async_trait::async_trait;
use std::collections::HashSet;
use std::path::Path;

/// System permissions.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Permission {
    ReadFiles,
    WriteFiles,
    DeleteFiles,
    ExecuteCommands,
    ExecuteShell,
    QueryDatabase,
    WriteDatabase,
    MakeHttpRequests,
    MakeExternalApiCalls,
    ManageUsers,
    ManageAgents,
    AccessSecrets,
    UseTools,
    UseDangerousTools,
}

/// Predefined roles with permission sets.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Role {
    Admin,
    User,
    ReadOnly,
    Restricted,
}

impl Role {
    /// Get permissions for this role.
    pub fn permissions(&self) -> HashSet<Permission> {
        match self {
            Role::Admin => HashSet::from([
                Permission::ReadFiles,
                Permission::WriteFiles,
                Permission::DeleteFiles,
                Permission::ExecuteCommands,
                Permission::ExecuteShell,
                Permission::QueryDatabase,
                Permission::WriteDatabase,
                Permission::MakeHttpRequests,
                Permission::MakeExternalApiCalls,
                Permission::ManageUsers,
                Permission::ManageAgents,
                Permission::AccessSecrets,
                Permission::UseTools,
                Permission::UseDangerousTools,
            ]),
            Role::User => HashSet::from([
                Permission::ReadFiles,
                Permission::WriteFiles,
                Permission::ExecuteCommands,
                Permission::QueryDatabase,
                Permission::MakeHttpRequests,
                Permission::UseTools,
            ]),
            Role::ReadOnly => HashSet::from([
                Permission::ReadFiles,
                Permission::QueryDatabase,
                Permission::UseTools,
            ]),
            Role::Restricted => HashSet::from([Permission::ReadFiles, Permission::UseTools]),
        }
    }
}

/// Sandbox constraints for execution.
#[derive(Debug, Clone)]
pub struct Sandbox {
    /// Allowed file paths (empty = no restriction)
    pub allowed_paths: HashSet<String>,
    /// Denied file paths
    pub denied_paths: HashSet<String>,
    /// Allowed commands
    pub allowed_commands: HashSet<String>,
    /// Denied commands
    pub denied_commands: HashSet<String>,
    /// Allowed SQL operations
    pub allowed_sql_operations: HashSet<String>,
    /// Allowed domains
    pub allowed_domains: HashSet<String>,
    /// Denied domains
    pub denied_domains: HashSet<String>,
    /// Maximum file size (bytes)
    pub max_file_size: usize,
    /// Maximum execution time (seconds)
    pub max_execution_time: u64,
    /// Maximum memory (bytes)
    pub max_memory: usize,
}

impl Default for Sandbox {
    fn default() -> Self {
        Self {
            allowed_paths: HashSet::new(),
            denied_paths: HashSet::from([
                "/etc".to_string(),
                "/sys".to_string(),
                "/proc".to_string(),
            ]),
            allowed_commands: HashSet::from([
                "ls".to_string(),
                "cat".to_string(),
                "grep".to_string(),
                "git".to_string(),
                "python".to_string(),
            ]),
            denied_commands: HashSet::from([
                "rm".to_string(),
                "sudo".to_string(),
                "chmod".to_string(),
                "chown".to_string(),
            ]),
            allowed_sql_operations: HashSet::from(["SELECT".to_string(), "EXPLAIN".to_string()]),
            allowed_domains: HashSet::new(), // Empty = allow all
            denied_domains: HashSet::from([
                "localhost".to_string(),
                "127.0.0.1".to_string(),
                "0.0.0.0".to_string(),
            ]),
            max_file_size: 10 * 1024 * 1024, // 10MB
            max_execution_time: 30,          // 30 seconds
            max_memory: 512 * 1024 * 1024,   // 512MB
        }
    }
}

impl Sandbox {
    /// Check if a file path is allowed.
    pub fn is_path_allowed(&self, path: &str) -> bool {
        let path_obj = Path::new(path);

        // Check denied paths first
        for denied in &self.denied_paths {
            if path_obj.starts_with(denied) {
                return false;
            }
        }

        // If allowed_paths is empty, allow all (except denied)
        if self.allowed_paths.is_empty() {
            return true;
        }

        // Check allowed paths
        for allowed in &self.allowed_paths {
            if path_obj.starts_with(allowed) {
                return true;
            }
        }

        false
    }

    /// Check if a command is allowed.
    pub fn is_command_allowed(&self, command: &str) -> bool {
        // Check denied first
        if self.denied_commands.contains(command) {
            return false;
        }

        // Check allowed
        self.allowed_commands.contains(command)
    }

    /// Check if a SQL operation is allowed.
    pub fn is_sql_operation_allowed(&self, operation: &str) -> bool {
        self.allowed_sql_operations
            .contains(&operation.to_uppercase())
    }

    /// Check if a domain is allowed.
    pub fn is_domain_allowed(&self, domain: &str) -> bool {
        // Check denied first
        if self.denied_domains.contains(domain) {
            return false;
        }

        // If allowed_domains is empty, allow all (except denied)
        if self.allowed_domains.is_empty() {
            return true;
        }

        // Check allowed
        self.allowed_domains.contains(domain)
    }
}

/// Permission middleware for access control.
pub struct PermissionMiddleware<A: Agent> {
    inner: A,
    role: Role,
    sandbox: Sandbox,
}

impl<A: Agent> PermissionMiddleware<A> {
    /// Create a new permission middleware with the given role.
    pub fn new(agent: A, role: Role) -> Self {
        Self {
            inner: agent,
            role,
            sandbox: Sandbox::default(),
        }
    }

    /// Set custom sandbox constraints.
    pub fn with_sandbox(mut self, sandbox: Sandbox) -> Self {
        self.sandbox = sandbox;
        self
    }

    /// Check if role has permission.
    fn has_permission(&self, permission: Permission) -> bool {
        self.role.permissions().contains(&permission)
    }
}

#[async_trait]
impl<A: Agent> Agent for PermissionMiddleware<A> {
    fn name(&self) -> &str {
        self.inner.name()
    }

    fn capabilities(&self) -> Vec<String> {
        self.inner.capabilities()
    }

    fn introspect(&self) -> IntrospectionResult {
        let mut result = self.inner.introspect();
        result
            .metadata
            .insert("middleware".to_string(), serde_json::json!("permissions"));
        result.metadata.insert(
            "role".to_string(),
            serde_json::json!(format!("{:?}", self.role)),
        );
        result
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        // Basic permission check for tool use
        if !self.has_permission(Permission::UseTools) {
            return Err(AgentError::ProcessingError(
                "Permission denied: cannot use tools".to_string(),
            ));
        }

        // Check message content for dangerous operations
        let content = message.content_as_str().unwrap_or("");
        let content_lower = content.to_lowercase();

        // File operations
        if content_lower.contains("read file") && !self.has_permission(Permission::ReadFiles) {
            return Err(AgentError::ProcessingError(
                "Permission denied: cannot read files".to_string(),
            ));
        }

        if content_lower.contains("write file") && !self.has_permission(Permission::WriteFiles) {
            return Err(AgentError::ProcessingError(
                "Permission denied: cannot write files".to_string(),
            ));
        }

        // Command execution
        if (content_lower.contains("execute") || content_lower.contains("run command"))
            && !self.has_permission(Permission::ExecuteCommands)
        {
            return Err(AgentError::ProcessingError(
                "Permission denied: cannot execute commands".to_string(),
            ));
        }

        // Process message
        self.inner.process(message).await
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_role_permissions() {
        // Admin has all permissions
        assert!(Role::Admin.permissions().contains(&Permission::ManageUsers));

        // User has limited permissions
        assert!(Role::User.permissions().contains(&Permission::ReadFiles));
        assert!(!Role::User.permissions().contains(&Permission::ManageUsers));

        // ReadOnly has minimal permissions
        assert!(Role::ReadOnly
            .permissions()
            .contains(&Permission::ReadFiles));
        assert!(!Role::ReadOnly
            .permissions()
            .contains(&Permission::WriteFiles));
    }

    #[test]
    fn test_sandbox_path_allowed() {
        let sandbox = Sandbox::default();

        // Denied paths
        assert!(!sandbox.is_path_allowed("/etc/passwd"));
        assert!(!sandbox.is_path_allowed("/sys/kernel"));

        // Allowed paths (by default)
        assert!(sandbox.is_path_allowed("/home/user/file.txt"));
        assert!(sandbox.is_path_allowed("/tmp/test.txt"));
    }

    #[test]
    fn test_sandbox_command_allowed() {
        let sandbox = Sandbox::default();

        // Allowed commands
        assert!(sandbox.is_command_allowed("ls"));
        assert!(sandbox.is_command_allowed("cat"));

        // Denied commands
        assert!(!sandbox.is_command_allowed("rm"));
        assert!(!sandbox.is_command_allowed("sudo"));
    }

    #[test]
    fn test_sandbox_domain_allowed() {
        let sandbox = Sandbox::default();

        // Denied domains
        assert!(!sandbox.is_domain_allowed("localhost"));
        assert!(!sandbox.is_domain_allowed("127.0.0.1"));

        // Allowed domains (by default)
        assert!(sandbox.is_domain_allowed("api.example.com"));
        assert!(sandbox.is_domain_allowed("github.com"));
    }

    #[test]
    fn test_role_restricted_permissions() {
        let restricted = Role::Restricted.permissions();

        // Should have minimal permissions
        assert!(restricted.contains(&Permission::ReadFiles));
        assert!(!restricted.contains(&Permission::WriteFiles));
        assert!(!restricted.contains(&Permission::ExecuteCommands));
        assert!(!restricted.contains(&Permission::ManageUsers));
    }

    #[test]
    fn test_permission_hierarchy() {
        // Admin should have more permissions than User
        let admin_perms = Role::Admin.permissions();
        let user_perms = Role::User.permissions();

        assert!(admin_perms.len() > user_perms.len());

        // All user permissions should be in admin permissions
        for perm in user_perms {
            assert!(admin_perms.contains(&perm), "Admin should have all User permissions");
        }
    }

    #[test]
    fn test_sandbox_custom_allowed_paths() {
        let mut sandbox = Sandbox::default();
        sandbox.allowed_paths.insert("/custom/path".to_string());

        assert!(sandbox.is_path_allowed("/custom/path/file.txt"));
    }

    #[test]
    fn test_all_permission_types() {
        // Verify all permission types are defined
        let perms = vec![
            Permission::ReadFiles,
            Permission::WriteFiles,
            Permission::DeleteFiles,
            Permission::ExecuteCommands,
            Permission::QueryDatabase,
            Permission::MakeHttpRequests,
            Permission::UseTools,
            Permission::ManageUsers,
        ];

        for perm in perms {
            // Just checking they exist and can be created
            assert!(format!("{:?}", perm).len() > 0);
        }
    }
}
