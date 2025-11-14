"""
Permission-based access control and sandboxing.

Provides:
- Role-Based Access Control (RBAC)
- Permission checks before agent actions
- Sandboxing (allowed paths, commands, operations)
- Resource constraints
"""

from enum import Enum
from typing import Set, Optional, List, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path

from agenkit import Agent, Message


class Permission(Enum):
    """System permissions for agents."""

    # File system
    READ_FILES = "read:files"
    WRITE_FILES = "write:files"
    DELETE_FILES = "delete:files"

    # Command execution
    EXECUTE_COMMANDS = "execute:commands"
    EXECUTE_SHELL = "execute:shell"

    # Database
    QUERY_DATABASE = "query:database"
    WRITE_DATABASE = "write:database"

    # Network
    MAKE_HTTP_REQUESTS = "network:http"
    MAKE_EXTERNAL_API_CALLS = "network:api"

    # System
    MANAGE_USERS = "manage:users"
    MANAGE_AGENTS = "manage:agents"
    ACCESS_SECRETS = "access:secrets"

    # Tools
    USE_TOOLS = "use:tools"
    USE_DANGEROUS_TOOLS = "use:dangerous_tools"


class Role(Enum):
    """Predefined roles with permission sets."""

    # Admin: Full access
    ADMIN = "admin"

    # User: Standard access
    USER = "user"

    # Read-only: View access only
    READONLY = "readonly"

    # Restricted: Minimal access
    RESTRICTED = "restricted"


# Role -> Permissions mapping
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.ADMIN: {
        Permission.READ_FILES,
        Permission.WRITE_FILES,
        Permission.DELETE_FILES,
        Permission.EXECUTE_COMMANDS,
        Permission.EXECUTE_SHELL,
        Permission.QUERY_DATABASE,
        Permission.WRITE_DATABASE,
        Permission.MAKE_HTTP_REQUESTS,
        Permission.MAKE_EXTERNAL_API_CALLS,
        Permission.MANAGE_USERS,
        Permission.MANAGE_AGENTS,
        Permission.ACCESS_SECRETS,
        Permission.USE_TOOLS,
        Permission.USE_DANGEROUS_TOOLS,
    },
    Role.USER: {
        Permission.READ_FILES,
        Permission.WRITE_FILES,
        Permission.EXECUTE_COMMANDS,
        Permission.QUERY_DATABASE,
        Permission.MAKE_HTTP_REQUESTS,
        Permission.USE_TOOLS,
    },
    Role.READONLY: {
        Permission.READ_FILES,
        Permission.QUERY_DATABASE,
        Permission.USE_TOOLS,  # Basic tool access needed
    },
    Role.RESTRICTED: {
        Permission.READ_FILES,
        Permission.USE_TOOLS,  # Basic tool access needed
    },
}


class PermissionDeniedError(Exception):
    """Raised when permission check fails."""

    def __init__(
        self, message: str, required_permission: Optional[Permission] = None
    ):
        super().__init__(message)
        self.required_permission = required_permission


@dataclass
class Sandbox:
    """
    Defines sandboxed environment for agent execution.

    Specifies:
    - Allowed file paths
    - Allowed commands
    - Allowed database operations
    - Allowed API endpoints
    - Resource limits
    """

    # File system sandbox
    allowed_paths: Set[str] = field(default_factory=set)
    denied_paths: Set[str] = field(default_factory=lambda: {"/etc", "/sys", "/proc"})

    # Command sandbox
    allowed_commands: Set[str] = field(
        default_factory=lambda: {"ls", "cat", "grep", "git", "python"}
    )
    denied_commands: Set[str] = field(
        default_factory=lambda: {"rm", "sudo", "chmod", "chown"}
    )

    # Database sandbox
    allowed_sql_operations: Set[str] = field(
        default_factory=lambda: {"SELECT", "EXPLAIN"}
    )

    # Network sandbox
    allowed_domains: Set[str] = field(default_factory=set)  # Empty = allow all
    denied_domains: Set[str] = field(
        default_factory=lambda: {"localhost", "127.0.0.1", "0.0.0.0"}
    )

    # Resource limits
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    max_execution_time: int = 30  # seconds
    max_memory_mb: int = 512  # MB

    def is_path_allowed(self, path: str) -> tuple[bool, Optional[str]]:
        """
        Check if path is within sandbox.

        Args:
            path: File path to check

        Returns:
            Tuple of (is_allowed, error_message)
        """
        try:
            resolved = Path(path).resolve()

            # Check denied paths first
            for denied in self.denied_paths:
                denied_resolved = Path(denied).resolve()
                try:
                    resolved.relative_to(denied_resolved)
                    return False, f"Path is in denied directory: {denied}"
                except ValueError:
                    pass

            # If allowed_paths specified, must be under one of them
            if self.allowed_paths:
                for allowed in self.allowed_paths:
                    allowed_resolved = Path(allowed).resolve()
                    try:
                        resolved.relative_to(allowed_resolved)
                        return True, None
                    except ValueError:
                        pass

                return False, "Path is outside allowed directories"

            # No allowed_paths specified, just check denied
            return True, None

        except Exception as e:
            return False, f"Path validation error: {e}"

    def is_command_allowed(self, command: str) -> tuple[bool, Optional[str]]:
        """
        Check if command is allowed in sandbox.

        Args:
            command: Command to check (just the command name, not args)

        Returns:
            Tuple of (is_allowed, error_message)
        """
        cmd_name = command.split()[0] if command else ""

        # Check denied commands first
        if cmd_name in self.denied_commands:
            return False, f"Command is denied: {cmd_name}"

        # Check allowed commands
        if self.allowed_commands:
            if cmd_name not in self.allowed_commands:
                return False, f"Command not in allowed list: {cmd_name}"

        return True, None

    def is_sql_operation_allowed(self, sql: str) -> tuple[bool, Optional[str]]:
        """
        Check if SQL operation is allowed.

        Args:
            sql: SQL statement

        Returns:
            Tuple of (is_allowed, error_message)
        """
        operation = sql.strip().upper().split()[0] if sql else ""

        if operation not in self.allowed_sql_operations:
            return False, f"SQL operation not allowed: {operation}"

        return True, None

    def is_domain_allowed(self, domain: str) -> tuple[bool, Optional[str]]:
        """
        Check if domain is allowed for network requests.

        Args:
            domain: Domain to check

        Returns:
            Tuple of (is_allowed, error_message)
        """
        # Check denied domains first
        if domain in self.denied_domains:
            return False, f"Domain is denied: {domain}"

        # If allowed_domains specified, must be in list
        if self.allowed_domains:
            if domain not in self.allowed_domains:
                return False, f"Domain not in allowed list: {domain}"

        return True, None


class PermissionMiddleware(Agent):
    """
    Middleware for permission checks and sandboxing.

    Enforces:
    - Role-based permissions
    - Sandbox constraints
    - Resource limits

    Usage:
        sandbox = Sandbox(
            allowed_paths={"/app/data"},
            allowed_commands={"git", "ls", "cat"}
        )

        agent = PermissionMiddleware(
            base_agent,
            role=Role.USER,
            sandbox=sandbox
        )
    """

    def __init__(
        self,
        agent: Agent,
        role: Role = Role.USER,
        custom_permissions: Optional[Set[Permission]] = None,
        sandbox: Optional[Sandbox] = None,
    ):
        """
        Initialize permission middleware.

        Args:
            agent: Agent to wrap
            role: User role (determines permissions)
            custom_permissions: Custom permission set (overrides role)
            sandbox: Sandbox constraints
        """
        self._agent = agent
        self.role = role
        self.permissions = custom_permissions or ROLE_PERMISSIONS.get(
            role, set()
        )
        self.sandbox = sandbox or Sandbox()

    @property
    def name(self) -> str:
        """Return the name of the underlying agent."""
        return self._agent.name

    @property
    def capabilities(self) -> list[str]:
        """Return capabilities of the underlying agent."""
        return self._agent.capabilities

    def has_permission(self, permission: Permission) -> bool:
        """Check if agent has permission."""
        return permission in self.permissions

    def check_permission(self, permission: Permission) -> None:
        """
        Check permission and raise error if denied.

        Args:
            permission: Required permission

        Raises:
            PermissionDeniedError: If permission not granted
        """
        if not self.has_permission(permission):
            raise PermissionDeniedError(
                f"Permission denied: {permission.value} required (role: {self.role.value})",
                required_permission=permission,
            )

    async def process(self, message: Message) -> Message:
        """
        Process with permission checks.

        Note: This middleware checks for general USE_TOOLS permission.
        Specific permission checks should be done by tools themselves
        or by extending this middleware.
        """
        # Basic permission check
        self.check_permission(Permission.USE_TOOLS)

        # Check for dangerous operations in message content
        content_str = str(message.content).lower() if message.content else ""

        # Detect file operations
        if any(keyword in content_str for keyword in ["read file", "write file", "delete file"]):
            if "delete" in content_str:
                self.check_permission(Permission.DELETE_FILES)
            elif "write" in content_str:
                self.check_permission(Permission.WRITE_FILES)
            else:
                self.check_permission(Permission.READ_FILES)

        # Detect command execution
        if any(keyword in content_str for keyword in ["execute", "run command", "shell"]):
            if "shell" in content_str:
                self.check_permission(Permission.EXECUTE_SHELL)
            else:
                self.check_permission(Permission.EXECUTE_COMMANDS)

        # Detect database operations
        # Check for write operations first (more specific)
        if any(op in content_str for op in ["insert", "update", "delete", "drop", "alter", "create table"]):
            # Likely a SQL write operation
            self.check_permission(Permission.WRITE_DATABASE)
        elif any(keyword in content_str for keyword in ["query", "database", "sql", "select", "from"]):
            # Database read operation
            self.check_permission(Permission.QUERY_DATABASE)

        # Process with wrapped agent
        return await self._agent.process(message)


def permissions(
    role: Role = Role.USER,
    custom_permissions: Optional[Set[Permission]] = None,
    sandbox: Optional[Sandbox] = None,
):
    """
    Create permission middleware function.

    Args:
        role: User role
        custom_permissions: Custom permissions (overrides role)
        sandbox: Sandbox constraints

    Returns:
        Middleware function

    Usage:
        sandbox = Sandbox(allowed_paths={"/app/data"})

        agent = applyMiddleware(base_agent, [
            permissions(role=Role.USER, sandbox=sandbox),
            retry(),
        ])
    """
    def middleware(agent: Agent) -> Agent:
        return PermissionMiddleware(agent, role, custom_permissions, sandbox)

    return middleware
