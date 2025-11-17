package safety

import (
	"context"
	"strings"
	"testing"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// TestRolePermissions tests for role-based permissions
func TestRoleAdminHasAllPermissions(t *testing.T) {
	perms := RolePermissions[RoleAdmin]

	// Admin should have all permissions
	if !perms[ReadFiles] {
		t.Error("Admin should have ReadFiles permission")
	}
	if !perms[WriteFiles] {
		t.Error("Admin should have WriteFiles permission")
	}
	if !perms[DeleteFiles] {
		t.Error("Admin should have DeleteFiles permission")
	}
	if !perms[ExecuteShell] {
		t.Error("Admin should have ExecuteShell permission")
	}
	if !perms[AccessSecrets] {
		t.Error("Admin should have AccessSecrets permission")
	}
	if !perms[UseDangerousTools] {
		t.Error("Admin should have UseDangerousTools permission")
	}
}

func TestRoleUserRestrictedPermissions(t *testing.T) {
	perms := RolePermissions[RoleUser]

	// User should have some permissions
	if !perms[ReadFiles] {
		t.Error("User should have ReadFiles permission")
	}
	if !perms[WriteFiles] {
		t.Error("User should have WriteFiles permission")
	}

	// User should NOT have dangerous permissions
	if perms[DeleteFiles] {
		t.Error("User should NOT have DeleteFiles permission")
	}
	if perms[ExecuteShell] {
		t.Error("User should NOT have ExecuteShell permission")
	}
	if perms[AccessSecrets] {
		t.Error("User should NOT have AccessSecrets permission")
	}
}

func TestRoleReadOnlyLimitedPermissions(t *testing.T) {
	perms := RolePermissions[RoleReadOnly]

	// ReadOnly should have read permissions
	if !perms[ReadFiles] {
		t.Error("ReadOnly should have ReadFiles permission")
	}
	if !perms[QueryDatabase] {
		t.Error("ReadOnly should have QueryDatabase permission")
	}

	// ReadOnly should NOT have write permissions
	if perms[WriteFiles] {
		t.Error("ReadOnly should NOT have WriteFiles permission")
	}
	if perms[WriteDatabase] {
		t.Error("ReadOnly should NOT have WriteDatabase permission")
	}
	if perms[DeleteFiles] {
		t.Error("ReadOnly should NOT have DeleteFiles permission")
	}
}

func TestRoleRestrictedMinimalPermissions(t *testing.T) {
	perms := RolePermissions[RoleRestricted]

	// Restricted should have minimal permissions
	if !perms[ReadFiles] {
		t.Error("Restricted should have ReadFiles permission")
	}
	if !perms[UseTools] {
		t.Error("Restricted should have UseTools permission")
	}

	// Restricted should NOT have most permissions
	if perms[WriteFiles] {
		t.Error("Restricted should NOT have WriteFiles permission")
	}
	if perms[ExecuteCommands] {
		t.Error("Restricted should NOT have ExecuteCommands permission")
	}
	if perms[QueryDatabase] {
		t.Error("Restricted should NOT have QueryDatabase permission")
	}
}

// TestSandbox tests for Sandbox
func TestSandboxDefaultSettings(t *testing.T) {
	sandbox := NewSandbox()

	if len(sandbox.DeniedPaths) == 0 {
		t.Error("Default sandbox should have denied paths")
	}
	if len(sandbox.AllowedCommands) == 0 {
		t.Error("Default sandbox should have allowed commands")
	}
	if len(sandbox.DeniedCommands) == 0 {
		t.Error("Default sandbox should have denied commands")
	}
	if sandbox.MaxFileSizeMB != 10 {
		t.Errorf("Expected MaxFileSizeMB=10, got %d", sandbox.MaxFileSizeMB)
	}
}

func TestSandboxPathAllowedNoRestrictions(t *testing.T) {
	sandbox := NewSandbox()
	sandbox.AllowedPaths = []string{} // No restrictions
	sandbox.DeniedPaths = []string{}  // No denials

	// Any path should be allowed
	isAllowed, err := sandbox.IsPathAllowed("/tmp/test.txt")

	if !isAllowed {
		t.Errorf("Expected path to be allowed, got error: %v", err)
	}
}

func TestSandboxPathDenied(t *testing.T) {
	sandbox := NewSandbox()
	// Default sandbox denies /etc

	isAllowed, err := sandbox.IsPathAllowed("/etc/passwd")

	if isAllowed {
		t.Error("Expected /etc path to be denied")
	}
	if err == nil || !strings.Contains(*err, "denied") {
		t.Errorf("Expected denied error, got: %v", err)
	}
}

func TestSandboxPathAllowedWithWhitelist(t *testing.T) {
	sandbox := NewSandbox()
	sandbox.AllowedPaths = []string{"/app/data"}
	sandbox.DeniedPaths = []string{}

	// Path within allowed directory should be allowed
	isAllowed, _ := sandbox.IsPathAllowed("/app/data/file.txt")

	if !isAllowed {
		t.Error("Expected path within allowed directory to be allowed")
	}
}

func TestSandboxPathDeniedOutsideWhitelist(t *testing.T) {
	sandbox := NewSandbox()
	sandbox.AllowedPaths = []string{"/app/data"}

	// Path outside allowed directory should be denied
	isAllowed, err := sandbox.IsPathAllowed("/tmp/file.txt")

	if isAllowed {
		t.Error("Expected path outside allowed directory to be denied")
	}
	if err == nil || !strings.Contains(*err, "outside allowed") {
		t.Errorf("Expected 'outside allowed' error, got: %v", err)
	}
}

func TestSandboxCommandAllowed(t *testing.T) {
	sandbox := NewSandbox()

	// "ls" is in default allowed commands
	isAllowed, err := sandbox.IsCommandAllowed("ls")

	if !isAllowed {
		t.Errorf("Expected 'ls' to be allowed, got error: %v", err)
	}
}

func TestSandboxCommandDenied(t *testing.T) {
	sandbox := NewSandbox()

	// "rm" is in default denied commands
	isAllowed, err := sandbox.IsCommandAllowed("rm")

	if isAllowed {
		t.Error("Expected 'rm' to be denied")
	}
	if err == nil || !strings.Contains(*err, "denied") {
		t.Errorf("Expected denied error, got: %v", err)
	}
}

func TestSandboxCommandWithArguments(t *testing.T) {
	sandbox := NewSandbox()

	// Command with arguments should check just the command name
	isAllowed, _ := sandbox.IsCommandAllowed("ls -la /tmp")

	if !isAllowed {
		t.Error("Expected command with arguments to be allowed if command is allowed")
	}
}

func TestSandboxCommandNotInAllowedList(t *testing.T) {
	sandbox := NewSandbox()

	// Command not in allowed list should be denied
	isAllowed, err := sandbox.IsCommandAllowed("unknown_command")

	if isAllowed {
		t.Error("Expected unknown command to be denied")
	}
	if err == nil || !strings.Contains(*err, "not in allowed list") {
		t.Errorf("Expected 'not in allowed list' error, got: %v", err)
	}
}

func TestSandboxSQLOperationAllowed(t *testing.T) {
	sandbox := NewSandbox()

	// SELECT is in default allowed SQL operations
	isAllowed, err := sandbox.IsSQLOperationAllowed("SELECT * FROM users")

	if !isAllowed {
		t.Errorf("Expected SELECT to be allowed, got error: %v", err)
	}
}

func TestSandboxSQLOperationDenied(t *testing.T) {
	sandbox := NewSandbox()

	// DELETE is not in default allowed SQL operations
	isAllowed, err := sandbox.IsSQLOperationAllowed("DELETE FROM users")

	if isAllowed {
		t.Error("Expected DELETE to be denied")
	}
	if err == nil || !strings.Contains(*err, "not allowed") {
		t.Errorf("Expected 'not allowed' error, got: %v", err)
	}
}

func TestSandboxSQLOperationCaseInsensitive(t *testing.T) {
	sandbox := NewSandbox()

	// Should work with lowercase
	isAllowed, _ := sandbox.IsSQLOperationAllowed("select * from users")

	if !isAllowed {
		t.Error("Expected lowercase SELECT to be allowed")
	}
}

func TestSandboxEmptySQL(t *testing.T) {
	sandbox := NewSandbox()

	// Empty SQL should be allowed (no-op)
	isAllowed, err := sandbox.IsSQLOperationAllowed("")

	if !isAllowed {
		t.Errorf("Expected empty SQL to be allowed, got error: %v", err)
	}
}

func TestSandboxDomainAllowed(t *testing.T) {
	sandbox := NewSandbox()
	sandbox.AllowedDomains = []string{"example.com", "api.github.com"}

	isAllowed, _ := sandbox.IsDomainAllowed("example.com")

	if !isAllowed {
		t.Error("Expected example.com to be allowed")
	}
}

func TestSandboxDomainDenied(t *testing.T) {
	sandbox := NewSandbox()

	// localhost is in default denied domains
	isAllowed, err := sandbox.IsDomainAllowed("localhost")

	if isAllowed {
		t.Error("Expected localhost to be denied")
	}
	if err == nil || !strings.Contains(*err, "denied") {
		t.Errorf("Expected denied error, got: %v", err)
	}
}

func TestSandboxDomainNotInAllowedList(t *testing.T) {
	sandbox := NewSandbox()
	sandbox.AllowedDomains = []string{"example.com"}

	isAllowed, err := sandbox.IsDomainAllowed("other.com")

	if isAllowed {
		t.Error("Expected other.com to be denied")
	}
	if err == nil || !strings.Contains(*err, "not in allowed list") {
		t.Errorf("Expected 'not in allowed list' error, got: %v", err)
	}
}

// TestPermissionMiddleware tests for PermissionMiddleware
func TestPermissionMiddlewareDefaultSandbox(t *testing.T) {
	agent := &mockAgent{name: "test-agent"}
	middleware := NewPermissionMiddleware(agent, RoleUser, nil, nil)

	if middleware.sandbox == nil {
		t.Error("Expected default sandbox to be created")
	}
}

func TestPermissionMiddlewareHasPermission(t *testing.T) {
	agent := &mockAgent{name: "test-agent"}
	middleware := NewPermissionMiddleware(agent, RoleAdmin, nil, nil)

	if !middleware.HasPermission(ReadFiles) {
		t.Error("Admin should have ReadFiles permission")
	}
	if !middleware.HasPermission(WriteFiles) {
		t.Error("Admin should have WriteFiles permission")
	}
}

func TestPermissionMiddlewareCheckPermissionAllowed(t *testing.T) {
	agent := &mockAgent{name: "test-agent"}
	middleware := NewPermissionMiddleware(agent, RoleAdmin, nil, nil)

	err := middleware.CheckPermission(ReadFiles)

	if err != nil {
		t.Errorf("Expected no error for allowed permission, got: %v", err)
	}
}

func TestPermissionMiddlewareCheckPermissionDenied(t *testing.T) {
	agent := &mockAgent{name: "test-agent"}
	middleware := NewPermissionMiddleware(agent, RoleReadOnly, nil, nil)

	err := middleware.CheckPermission(WriteFiles)

	if err == nil {
		t.Error("Expected permission denied error")
	}

	permErr, ok := err.(*PermissionDeniedError)
	if !ok {
		t.Errorf("Expected PermissionDeniedError, got %T", err)
	}
	if permErr != nil && !strings.Contains(permErr.Message, "Permission denied") {
		t.Errorf("Expected permission denied message, got: %s", permErr.Message)
	}
}

func TestPermissionMiddlewareProcessAllowed(t *testing.T) {
	agent := &mockAgent{name: "test-agent"}
	middleware := NewPermissionMiddleware(agent, RoleUser, nil, nil)

	message := &agenkit.Message{
		Role:    "user",
		Content: "Hello, how are you?",
	}

	response, err := middleware.Process(context.Background(), message)

	if err != nil {
		t.Errorf("Expected no error for allowed operation, got: %v", err)
	}
	if response == nil {
		t.Error("Expected response, got nil")
	}
}

func TestPermissionMiddlewareBlocksWriteFiles(t *testing.T) {
	agent := &mockAgent{name: "test-agent"}
	middleware := NewPermissionMiddleware(agent, RoleReadOnly, nil, nil)

	message := &agenkit.Message{
		Role:    "user",
		Content: "Write file to /tmp/test.txt",
	}

	_, err := middleware.Process(context.Background(), message)

	if err == nil {
		t.Error("Expected permission denied error for write operation")
	}
}

func TestPermissionMiddlewareBlocksDeleteFiles(t *testing.T) {
	agent := &mockAgent{name: "test-agent"}
	middleware := NewPermissionMiddleware(agent, RoleUser, nil, nil)

	message := &agenkit.Message{
		Role:    "user",
		Content: "Delete file /tmp/test.txt",
	}

	_, err := middleware.Process(context.Background(), message)

	if err == nil {
		t.Error("Expected permission denied error for delete operation")
	}
}

func TestPermissionMiddlewareBlocksShellExecution(t *testing.T) {
	agent := &mockAgent{name: "test-agent"}
	middleware := NewPermissionMiddleware(agent, RoleUser, nil, nil)

	message := &agenkit.Message{
		Role:    "user",
		Content: "Execute shell command: rm -rf /",
	}

	_, err := middleware.Process(context.Background(), message)

	if err == nil {
		t.Error("Expected permission denied error for shell execution")
	}
}

func TestPermissionMiddlewareBlocksDatabaseWrite(t *testing.T) {
	agent := &mockAgent{name: "test-agent"}
	middleware := NewPermissionMiddleware(agent, RoleReadOnly, nil, nil)

	message := &agenkit.Message{
		Role:    "user",
		Content: "INSERT INTO users VALUES (1, 'test')",
	}

	_, err := middleware.Process(context.Background(), message)

	if err == nil {
		t.Error("Expected permission denied error for database write")
	}
}

func TestPermissionMiddlewareAllowsDatabaseRead(t *testing.T) {
	agent := &mockAgent{name: "test-agent"}
	middleware := NewPermissionMiddleware(agent, RoleReadOnly, nil, nil)

	message := &agenkit.Message{
		Role:    "user",
		Content: "SELECT * FROM users",
	}

	response, err := middleware.Process(context.Background(), message)

	if err != nil {
		t.Errorf("Expected no error for database read, got: %v", err)
	}
	if response == nil {
		t.Error("Expected response for database read")
	}
}

func TestPermissionMiddlewarePreservesAgentName(t *testing.T) {
	agent := &mockAgent{name: "my-agent"}
	middleware := NewPermissionMiddleware(agent, RoleUser, nil, nil)

	if middleware.Name() != "my-agent" {
		t.Errorf("Expected name 'my-agent', got '%s'", middleware.Name())
	}
}

func TestPermissionMiddlewarePreservesCapabilities(t *testing.T) {
	agent := &mockAgent{
		name:         "test-agent",
		capabilities: []string{"chat", "search"},
	}
	middleware := NewPermissionMiddleware(agent, RoleUser, nil, nil)

	capabilities := middleware.Capabilities()
	if len(capabilities) != 2 {
		t.Errorf("Expected 2 capabilities, got %d", len(capabilities))
	}
}

func TestPermissionMiddlewareCustomPermissions(t *testing.T) {
	agent := &mockAgent{name: "test-agent"}

	// Custom permissions - only read files
	customPerms := map[Permission]bool{
		ReadFiles: true,
		UseTools:  true,
	}

	middleware := NewPermissionMiddleware(agent, RoleUser, customPerms, nil)

	if !middleware.HasPermission(ReadFiles) {
		t.Error("Expected custom ReadFiles permission")
	}
	if middleware.HasPermission(WriteFiles) {
		t.Error("Expected WriteFiles to be denied with custom permissions")
	}
}

func TestPermissionErrorStruct(t *testing.T) {
	perm := ReadFiles
	err := &PermissionDeniedError{
		Message:            "Test error",
		RequiredPermission: &perm,
	}

	if err.Error() != "Test error" {
		t.Errorf("Expected 'Test error', got '%s'", err.Error())
	}
	if err.RequiredPermission == nil || *err.RequiredPermission != ReadFiles {
		t.Error("Expected RequiredPermission to be preserved")
	}
}
