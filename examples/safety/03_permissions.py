"""
Example: Permission-Based Access Control and Sandboxing

This example demonstrates how to use PermissionMiddleware to implement
role-based access control (RBAC) and sandboxing for your agents.
"""

import asyncio

from agenkit.interfaces import Agent, Message
from agenkit.safety.permissions import (Permission, PermissionDeniedError,
                                        PermissionMiddleware, Role, Sandbox)


# Simple echo agent for testing
class EchoAgent(Agent):
    """Agent that echoes back user commands."""

    @property
    def name(self) -> str:
        return "echo"

    @property
    def capabilities(self) -> list[str]:
        return []

    async def process(self, message: Message) -> Message:
        return Message(role="assistant", content=f"Executing: {message.content}")


async def main():
    """Demonstrate permissions and sandboxing."""
    print("=" * 60)
    print("Permissions and Sandboxing Example")
    print("=" * 60)

    echo_agent = EchoAgent()

    # 1. Role-Based Access Control
    print("\n1. Role-Based Access Control")
    print("-" * 60)

    # Admin role - full access
    print("\nAdmin Role (full access):")
    admin_agent = PermissionMiddleware(echo_agent, role=Role.ADMIN)
    try:
        response = await admin_agent.process(
            Message(role="user", content="delete file /important/data.txt")
        )
        print(f"  ✓ {response.content}")
    except PermissionDeniedError as e:
        print(f"  ✗ {e}")

    # User role - standard access
    print("\nUser Role (standard access):")
    user_agent = PermissionMiddleware(echo_agent, role=Role.USER)
    try:
        response = await user_agent.process(Message(role="user", content="read file config.json"))
        print(f"  ✓ {response.content}")
    except PermissionDeniedError as e:
        print(f"  ✗ {e}")

    # Readonly role - limited access
    print("\nReadonly Role (read-only access):")
    readonly_agent = PermissionMiddleware(echo_agent, role=Role.READONLY)
    try:
        response = await readonly_agent.process(
            Message(role="user", content="write file output.txt")
        )
        print(f"  ✓ {response.content}")
    except PermissionDeniedError as e:
        print(f"  ✗ Blocked: {e}")

    # 2. Permission Checks
    print("\n2. Specific Permission Checks")
    print("-" * 60)

    # Check what permissions a role has
    readonly = PermissionMiddleware(echo_agent, role=Role.READONLY)
    print(f"Readonly can read files: {readonly.has_permission(Permission.READ_FILES)}")
    print(f"Readonly can write files: {readonly.has_permission(Permission.WRITE_FILES)}")
    print(f"Readonly can execute shell: {readonly.has_permission(Permission.EXECUTE_SHELL)}")

    # 3. Custom permissions
    print("\n3. Custom Permissions")
    print("-" * 60)

    custom_perms = {Permission.READ_FILES, Permission.QUERY_DATABASE}
    custom_agent = PermissionMiddleware(echo_agent, custom_permissions=custom_perms)

    print(f"Custom agent can read files: {custom_agent.has_permission(Permission.READ_FILES)}")
    print(f"Custom agent can write files: {custom_agent.has_permission(Permission.WRITE_FILES)}")
    print(f"Custom agent can query DB: {custom_agent.has_permission(Permission.QUERY_DATABASE)}")

    # 4. Sandboxing - File paths
    print("\n4. Sandboxing - File Path Restrictions")
    print("-" * 60)

    sandbox = Sandbox(allowed_paths={"/app/data", "/tmp"}, denied_paths={"/etc", "/sys", "/proc"})

    # Check path permissions
    allowed, error = sandbox.is_path_allowed("/app/data/file.txt")
    print(f"✓ /app/data/file.txt allowed: {allowed}")

    allowed, error = sandbox.is_path_allowed("/etc/passwd")
    print(f"✗ /etc/passwd allowed: {allowed} ({error})")

    # 5. Sandboxing - Command restrictions
    print("\n5. Sandboxing - Command Restrictions")
    print("-" * 60)

    command_sandbox = Sandbox(
        allowed_commands={"ls", "cat", "grep", "git"}, denied_commands={"rm", "sudo", "chmod"}
    )

    allowed, error = command_sandbox.is_command_allowed("ls -la")
    print(f"✓ 'ls -la' allowed: {allowed}")

    allowed, error = command_sandbox.is_command_allowed("rm -rf /")
    print(f"✗ 'rm -rf /' allowed: {allowed} ({error})")

    # 6. Sandboxing - SQL operations
    print("\n6. Sandboxing - SQL Operation Restrictions")
    print("-" * 60)

    sql_sandbox = Sandbox(allowed_sql_operations={"SELECT", "EXPLAIN"})

    allowed, error = sql_sandbox.is_sql_operation_allowed("SELECT * FROM users")
    print(f"✓ SELECT query allowed: {allowed}")

    allowed, error = sql_sandbox.is_sql_operation_allowed("DROP TABLE users")
    print(f"✗ DROP TABLE allowed: {allowed} ({error})")

    # 7. Sandboxing - Network restrictions
    print("\n7. Sandboxing - Network Domain Restrictions")
    print("-" * 60)

    network_sandbox = Sandbox(
        allowed_domains={"api.example.com", "cdn.example.com"},
        denied_domains={"localhost", "127.0.0.1"},
    )

    allowed, error = network_sandbox.is_domain_allowed("api.example.com")
    print(f"✓ api.example.com allowed: {allowed}")

    allowed, error = network_sandbox.is_domain_allowed("evil.com")
    print(f"✗ evil.com allowed: {allowed} ({error})")

    # 8. Combined: Permissions + Sandbox
    print("\n8. Combined: Role + Sandbox")
    print("-" * 60)

    combined_sandbox = Sandbox(
        allowed_paths={"/app/data"},
        allowed_commands={"ls", "cat"},
        allowed_sql_operations={"SELECT"},
    )

    PermissionMiddleware(echo_agent, role=Role.USER, sandbox=combined_sandbox)

    print("Secure agent configuration:")
    print("  Role: USER")
    print(f"  Allowed paths: {combined_sandbox.allowed_paths}")
    print(f"  Allowed commands: {combined_sandbox.allowed_commands}")
    print(f"  Allowed SQL: {combined_sandbox.allowed_sql_operations}")

    print("\n" + "=" * 60)
    print("Permissions and Sandboxing Example Complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
