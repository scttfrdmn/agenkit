package safety

import (
	"context"
	"fmt"
	"path/filepath"
	"strings"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// Permission represents system permissions for agents.
type Permission string

const (
	// File system permissions
	ReadFiles   Permission = "read:files"
	WriteFiles  Permission = "write:files"
	DeleteFiles Permission = "delete:files"

	// Command execution permissions
	ExecuteCommands Permission = "execute:commands"
	ExecuteShell    Permission = "execute:shell"

	// Database permissions
	QueryDatabase Permission = "query:database"
	WriteDatabase Permission = "write:database"

	// Network permissions
	MakeHTTPRequests     Permission = "network:http"
	MakeExternalAPICalls Permission = "network:api"

	// System permissions
	ManageUsers   Permission = "manage:users"
	ManageAgents  Permission = "manage:agents"
	AccessSecrets Permission = "access:secrets"

	// Tool permissions
	UseTools          Permission = "use:tools"
	UseDangerousTools Permission = "use:dangerous_tools"
)

// Role represents predefined roles with permission sets.
type Role string

const (
	// Admin: Full access
	RoleAdmin Role = "admin"

	// User: Standard access
	RoleUser Role = "user"

	// ReadOnly: View access only
	RoleReadOnly Role = "readonly"

	// Restricted: Minimal access
	RoleRestricted Role = "restricted"
)

// RolePermissions maps roles to their permission sets.
var RolePermissions = map[Role]map[Permission]bool{
	RoleAdmin: {
		ReadFiles:            true,
		WriteFiles:           true,
		DeleteFiles:          true,
		ExecuteCommands:      true,
		ExecuteShell:         true,
		QueryDatabase:        true,
		WriteDatabase:        true,
		MakeHTTPRequests:     true,
		MakeExternalAPICalls: true,
		ManageUsers:          true,
		ManageAgents:         true,
		AccessSecrets:        true,
		UseTools:             true,
		UseDangerousTools:    true,
	},
	RoleUser: {
		ReadFiles:        true,
		WriteFiles:       true,
		ExecuteCommands:  true,
		QueryDatabase:    true,
		MakeHTTPRequests: true,
		UseTools:         true,
	},
	RoleReadOnly: {
		ReadFiles:     true,
		QueryDatabase: true,
		UseTools:      true,
	},
	RoleRestricted: {
		ReadFiles: true,
		UseTools:  true,
	},
}

// PermissionDeniedError is raised when permission check fails.
type PermissionDeniedError struct {
	Message            string
	RequiredPermission *Permission
}

// Error returns the error message.
func (e *PermissionDeniedError) Error() string {
	return e.Message
}

// Sandbox defines sandboxed environment for agent execution.
//
// Specifies:
//   - Allowed file paths
//   - Allowed commands
//   - Allowed database operations
//   - Allowed API endpoints
//   - Resource limits
//
// Example:
//
//	sandbox := NewSandbox()
//	sandbox.AllowedPaths = []string{"/app/data"}
//	sandbox.AllowedCommands = []string{"git", "ls", "cat"}
type Sandbox struct {
	// File system sandbox
	AllowedPaths []string
	DeniedPaths  []string

	// Command sandbox
	AllowedCommands []string
	DeniedCommands  []string

	// Database sandbox
	AllowedSQLOperations []string

	// Network sandbox
	AllowedDomains []string
	DeniedDomains  []string

	// Resource limits
	MaxFileSizeMB    int // MB
	MaxExecutionTime int // seconds
	MaxMemoryMB      int // MB
}

// NewSandbox creates a new sandbox with default settings.
//
// Example:
//
//	sandbox := NewSandbox()
func NewSandbox() *Sandbox {
	return &Sandbox{
		AllowedPaths:         []string{},
		DeniedPaths:          []string{"/etc", "/sys", "/proc"},
		AllowedCommands:      []string{"ls", "cat", "grep", "git", "python"},
		DeniedCommands:       []string{"rm", "sudo", "chmod", "chown"},
		AllowedSQLOperations: []string{"SELECT", "EXPLAIN"},
		AllowedDomains:       []string{},
		DeniedDomains:        []string{"localhost", "127.0.0.1", "0.0.0.0"},
		MaxFileSizeMB:        10,
		MaxExecutionTime:     30,
		MaxMemoryMB:          512,
	}
}

// IsPathAllowed checks if path is within sandbox.
//
// Args:
//
//	path: File path to check
//
// Returns:
//
//	isAllowed: true if path is allowed
//	errorMessage: Error message if denied (nil if allowed)
func (s *Sandbox) IsPathAllowed(path string) (bool, *string) {
	// Resolve path
	resolved, err := filepath.Abs(path)
	if err != nil {
		msg := fmt.Sprintf("Path validation error: %v", err)
		return false, &msg
	}

	// Check denied paths first
	for _, denied := range s.DeniedPaths {
		deniedResolved, err := filepath.Abs(denied)
		if err != nil {
			continue
		}

		rel, err := filepath.Rel(deniedResolved, resolved)
		if err == nil && !strings.HasPrefix(rel, "..") {
			msg := fmt.Sprintf("Path is in denied directory: %s", denied)
			return false, &msg
		}
	}

	// If allowed_paths specified, must be under one of them
	if len(s.AllowedPaths) > 0 {
		for _, allowed := range s.AllowedPaths {
			allowedResolved, err := filepath.Abs(allowed)
			if err != nil {
				continue
			}

			rel, err := filepath.Rel(allowedResolved, resolved)
			if err == nil && !strings.HasPrefix(rel, "..") {
				return true, nil
			}
		}

		msg := "Path is outside allowed directories"
		return false, &msg
	}

	// No allowed_paths specified, just check denied
	return true, nil
}

// IsCommandAllowed checks if command is allowed in sandbox.
//
// Args:
//
//	command: Command to check (just the command name, not args)
//
// Returns:
//
//	isAllowed: true if command is allowed
//	errorMessage: Error message if denied (nil if allowed)
func (s *Sandbox) IsCommandAllowed(command string) (bool, *string) {
	cmdName := command
	if idx := strings.Index(command, " "); idx != -1 {
		cmdName = command[:idx]
	}

	// Check denied commands first
	for _, denied := range s.DeniedCommands {
		if cmdName == denied {
			msg := fmt.Sprintf("Command is denied: %s", cmdName)
			return false, &msg
		}
	}

	// Check allowed commands
	if len(s.AllowedCommands) > 0 {
		allowed := false
		for _, allowedCmd := range s.AllowedCommands {
			if cmdName == allowedCmd {
				allowed = true
				break
			}
		}
		if !allowed {
			msg := fmt.Sprintf("Command not in allowed list: %s", cmdName)
			return false, &msg
		}
	}

	return true, nil
}

// IsSQLOperationAllowed checks if SQL operation is allowed.
//
// Args:
//
//	sql: SQL statement
//
// Returns:
//
//	isAllowed: true if operation is allowed
//	errorMessage: Error message if denied (nil if allowed)
func (s *Sandbox) IsSQLOperationAllowed(sql string) (bool, *string) {
	if sql == "" {
		return true, nil
	}

	operation := strings.ToUpper(strings.TrimSpace(sql))
	if idx := strings.Index(operation, " "); idx != -1 {
		operation = operation[:idx]
	}

	allowed := false
	for _, allowedOp := range s.AllowedSQLOperations {
		if operation == allowedOp {
			allowed = true
			break
		}
	}

	if !allowed {
		msg := fmt.Sprintf("SQL operation not allowed: %s", operation)
		return false, &msg
	}

	return true, nil
}

// IsDomainAllowed checks if domain is allowed for network requests.
//
// Args:
//
//	domain: Domain to check
//
// Returns:
//
//	isAllowed: true if domain is allowed
//	errorMessage: Error message if denied (nil if allowed)
func (s *Sandbox) IsDomainAllowed(domain string) (bool, *string) {
	// Check denied domains first
	for _, denied := range s.DeniedDomains {
		if domain == denied {
			msg := fmt.Sprintf("Domain is denied: %s", domain)
			return false, &msg
		}
	}

	// If allowed_domains specified, must be in list
	if len(s.AllowedDomains) > 0 {
		allowed := false
		for _, allowedDomain := range s.AllowedDomains {
			if domain == allowedDomain {
				allowed = true
				break
			}
		}
		if !allowed {
			msg := fmt.Sprintf("Domain not in allowed list: %s", domain)
			return false, &msg
		}
	}

	return true, nil
}

// PermissionMiddleware provides middleware for permission checks and sandboxing.
//
// Enforces:
//   - Role-based permissions
//   - Sandbox constraints
//   - Resource limits
//
// Example:
//
//	sandbox := NewSandbox()
//	sandbox.AllowedPaths = []string{"/app/data"}
//
//	middleware := NewPermissionMiddleware(
//	    baseAgent,
//	    RoleUser,
//	    nil,
//	    sandbox,
//	)
type PermissionMiddleware struct {
	agent       agenkit.Agent
	role        Role
	permissions map[Permission]bool
	sandbox     *Sandbox
}

// NewPermissionMiddleware creates a new permission middleware.
//
// Args:
//
//	agent: Agent to wrap
//	role: User role (determines permissions)
//	customPermissions: Custom permission set (nil = use role permissions)
//	sandbox: Sandbox constraints (nil = default sandbox)
//
// Example:
//
//	middleware := NewPermissionMiddleware(
//	    agent,
//	    RoleUser,
//	    nil,
//	    NewSandbox(),
//	)
func NewPermissionMiddleware(
	agent agenkit.Agent,
	role Role,
	customPermissions map[Permission]bool,
	sandbox *Sandbox,
) *PermissionMiddleware {
	permissions := customPermissions
	if permissions == nil {
		if rolePerms, ok := RolePermissions[role]; ok {
			permissions = rolePerms
		} else {
			permissions = make(map[Permission]bool)
		}
	}

	if sandbox == nil {
		sandbox = NewSandbox()
	}

	return &PermissionMiddleware{
		agent:       agent,
		role:        role,
		permissions: permissions,
		sandbox:     sandbox,
	}
}

// Name returns the name of the underlying agent.
func (m *PermissionMiddleware) Name() string {
	return m.agent.Name()
}

// Capabilities returns capabilities of the underlying agent.
func (m *PermissionMiddleware) Capabilities() []string {
	return m.agent.Capabilities()
}

// HasPermission checks if agent has permission.
func (m *PermissionMiddleware) HasPermission(permission Permission) bool {
	return m.permissions[permission]
}

// CheckPermission checks permission and raises error if denied.
//
// Args:
//
//	permission: Required permission
//
// Returns:
//
//	error: PermissionDeniedError if permission not granted
func (m *PermissionMiddleware) CheckPermission(permission Permission) error {
	if !m.HasPermission(permission) {
		return &PermissionDeniedError{
			Message: fmt.Sprintf("Permission denied: %s required (role: %s)",
				permission, m.role),
			RequiredPermission: &permission,
		}
	}
	return nil
}

// Process processes message with permission checks.
//
// Note: This middleware checks for general USE_TOOLS permission.
// Specific permission checks should be done by tools themselves
// or by extending this middleware.
func (m *PermissionMiddleware) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	// Basic permission check
	if err := m.CheckPermission(UseTools); err != nil {
		return nil, err
	}

	// Check for dangerous operations in message content
	contentStr := strings.ToLower(message.Content)

	// Detect file operations
	if strings.Contains(contentStr, "read file") || strings.Contains(contentStr, "write file") || strings.Contains(contentStr, "delete file") {
		if strings.Contains(contentStr, "delete") {
			if err := m.CheckPermission(DeleteFiles); err != nil {
				return nil, err
			}
		} else if strings.Contains(contentStr, "write") {
			if err := m.CheckPermission(WriteFiles); err != nil {
				return nil, err
			}
		} else {
			if err := m.CheckPermission(ReadFiles); err != nil {
				return nil, err
			}
		}
	}

	// Detect command execution
	if strings.Contains(contentStr, "execute") || strings.Contains(contentStr, "run command") || strings.Contains(contentStr, "shell") {
		if strings.Contains(contentStr, "shell") {
			if err := m.CheckPermission(ExecuteShell); err != nil {
				return nil, err
			}
		} else {
			if err := m.CheckPermission(ExecuteCommands); err != nil {
				return nil, err
			}
		}
	}

	// Detect database operations
	// Check for write operations first (more specific)
	if strings.Contains(contentStr, "insert") || strings.Contains(contentStr, "update") ||
		strings.Contains(contentStr, "delete") || strings.Contains(contentStr, "drop") ||
		strings.Contains(contentStr, "alter") || strings.Contains(contentStr, "create table") {
		// Likely a SQL write operation
		if err := m.CheckPermission(WriteDatabase); err != nil {
			return nil, err
		}
	} else if strings.Contains(contentStr, "query") || strings.Contains(contentStr, "database") ||
		strings.Contains(contentStr, "sql") || strings.Contains(contentStr, "select") ||
		strings.Contains(contentStr, "from") {
		// Database read operation
		if err := m.CheckPermission(QueryDatabase); err != nil {
			return nil, err
		}
	}

	// Process with wrapped agent
	return m.agent.Process(ctx, message)
}
