"""Tests for permission-based access control and sandboxing."""

import pytest
from agenkit.interfaces import Agent, Message
from agenkit.safety.permissions import (
    PermissionMiddleware,
    Permission,
    Role,
    PermissionDeniedError,
    Sandbox,
    ROLE_PERMISSIONS,
)


class EchoAgent(Agent):
    """Simple echo agent for testing."""

    @property
    def name(self) -> str:
        return "echo"

    @property
    def capabilities(self) -> list[str]:
        return []

    async def process(self, message: Message) -> Message:
        return Message(role="assistant", content=message.content)


@pytest.fixture
def echo_agent():
    """Create a simple echo agent for testing."""
    return EchoAgent()


class TestPermission:
    """Tests for Permission enum."""

    def test_permission_values(self):
        """Test that permission values are correctly defined."""
        assert Permission.READ_FILES.value == "read:files"
        assert Permission.WRITE_FILES.value == "write:files"
        assert Permission.EXECUTE_COMMANDS.value == "execute:commands"
        assert Permission.ACCESS_SECRETS.value == "access:secrets"


class TestRole:
    """Tests for Role enum and role permissions."""

    def test_role_values(self):
        """Test that role values are correctly defined."""
        assert Role.ADMIN.value == "admin"
        assert Role.USER.value == "user"
        assert Role.READONLY.value == "readonly"
        assert Role.RESTRICTED.value == "restricted"

    def test_admin_has_all_permissions(self):
        """Test that admin role has comprehensive permissions."""
        admin_perms = ROLE_PERMISSIONS[Role.ADMIN]

        assert Permission.READ_FILES in admin_perms
        assert Permission.WRITE_FILES in admin_perms
        assert Permission.DELETE_FILES in admin_perms
        assert Permission.EXECUTE_COMMANDS in admin_perms
        assert Permission.EXECUTE_SHELL in admin_perms
        assert Permission.ACCESS_SECRETS in admin_perms

    def test_user_has_standard_permissions(self):
        """Test that user role has standard permissions."""
        user_perms = ROLE_PERMISSIONS[Role.USER]

        assert Permission.READ_FILES in user_perms
        assert Permission.WRITE_FILES in user_perms
        assert Permission.EXECUTE_COMMANDS in user_perms

        # Should not have dangerous permissions
        assert Permission.DELETE_FILES not in user_perms
        assert Permission.EXECUTE_SHELL not in user_perms
        assert Permission.ACCESS_SECRETS not in user_perms

    def test_readonly_limited_permissions(self):
        """Test that readonly role has minimal permissions."""
        readonly_perms = ROLE_PERMISSIONS[Role.READONLY]

        assert Permission.READ_FILES in readonly_perms
        assert Permission.QUERY_DATABASE in readonly_perms

        # Should not have write permissions
        assert Permission.WRITE_FILES not in readonly_perms
        assert Permission.EXECUTE_COMMANDS not in readonly_perms

    def test_restricted_minimal_permissions(self):
        """Test that restricted role has very minimal permissions."""
        restricted_perms = ROLE_PERMISSIONS[Role.RESTRICTED]

        assert Permission.READ_FILES in restricted_perms

        # Should not have other permissions
        assert Permission.WRITE_FILES not in restricted_perms
        assert Permission.EXECUTE_COMMANDS not in restricted_perms


class TestSandbox:
    """Tests for Sandbox."""

    def test_path_allowed_by_default(self):
        """Test that paths are allowed when no restrictions set."""
        sandbox = Sandbox(allowed_paths=set())

        is_allowed, error = sandbox.is_path_allowed("/tmp/test.txt")
        assert is_allowed is True
        assert error is None

    def test_path_denied_in_system_directories(self):
        """Test that system directories are denied by default."""
        sandbox = Sandbox()

        # Should deny /etc
        is_allowed, error = sandbox.is_path_allowed("/etc/passwd")
        assert is_allowed is False
        assert "denied directory" in error

        # Should deny /sys
        is_allowed, error = sandbox.is_path_allowed("/sys/kernel/test")
        assert is_allowed is False

    def test_path_allowed_in_specified_directories(self):
        """Test that paths in allowed_paths are permitted."""
        sandbox = Sandbox(allowed_paths={"/app/data", "/tmp"})

        is_allowed, error = sandbox.is_path_allowed("/app/data/file.txt")
        assert is_allowed is True
        assert error is None

        is_allowed, error = sandbox.is_path_allowed("/tmp/test.txt")
        assert is_allowed is True

    def test_path_denied_outside_allowed_directories(self):
        """Test that paths outside allowed_paths are denied."""
        sandbox = Sandbox(allowed_paths={"/app/data"})

        is_allowed, error = sandbox.is_path_allowed("/home/user/file.txt")
        assert is_allowed is False
        assert "outside allowed directories" in error

    def test_command_allowed_by_default(self):
        """Test that commands in allowed_commands are permitted."""
        sandbox = Sandbox()

        is_allowed, error = sandbox.is_command_allowed("ls -la")
        assert is_allowed is True
        assert error is None

        is_allowed, error = sandbox.is_command_allowed("git status")
        assert is_allowed is True

    def test_command_denied_in_denied_list(self):
        """Test that denied commands are blocked."""
        sandbox = Sandbox()

        is_allowed, error = sandbox.is_command_allowed("rm -rf /")
        assert is_allowed is False
        assert "denied" in error

        is_allowed, error = sandbox.is_command_allowed("sudo apt-get install")
        assert is_allowed is False

    def test_command_denied_outside_allowed_list(self):
        """Test that commands not in allowed list are denied."""
        sandbox = Sandbox(allowed_commands={"ls", "cat"})

        is_allowed, error = sandbox.is_command_allowed("python script.py")
        assert is_allowed is False
        assert "not in allowed list" in error

    def test_sql_operation_allowed(self):
        """Test that allowed SQL operations are permitted."""
        sandbox = Sandbox()

        is_allowed, error = sandbox.is_sql_operation_allowed("SELECT * FROM users")
        assert is_allowed is True
        assert error is None

        is_allowed, error = sandbox.is_sql_operation_allowed("EXPLAIN SELECT * FROM users")
        assert is_allowed is True

    def test_sql_operation_denied(self):
        """Test that write SQL operations are denied by default."""
        sandbox = Sandbox()

        is_allowed, error = sandbox.is_sql_operation_allowed("DELETE FROM users")
        assert is_allowed is False
        assert "not allowed" in error

        is_allowed, error = sandbox.is_sql_operation_allowed("DROP TABLE users")
        assert is_allowed is False

    def test_domain_allowed_by_default(self):
        """Test that domains are allowed when no restrictions set."""
        sandbox = Sandbox(allowed_domains=set())

        is_allowed, error = sandbox.is_domain_allowed("example.com")
        assert is_allowed is True
        assert error is None

    def test_domain_denied_in_denied_list(self):
        """Test that denied domains are blocked."""
        sandbox = Sandbox()

        is_allowed, error = sandbox.is_domain_allowed("localhost")
        assert is_allowed is False
        assert "denied" in error

        is_allowed, error = sandbox.is_domain_allowed("127.0.0.1")
        assert is_allowed is False

    def test_domain_allowed_in_allowed_list(self):
        """Test that domains in allowed list are permitted."""
        sandbox = Sandbox(allowed_domains={"api.example.com", "cdn.example.com"})

        is_allowed, error = sandbox.is_domain_allowed("api.example.com")
        assert is_allowed is True
        assert error is None

    def test_domain_denied_outside_allowed_list(self):
        """Test that domains not in allowed list are denied."""
        sandbox = Sandbox(allowed_domains={"api.example.com"})

        is_allowed, error = sandbox.is_domain_allowed("evil.com")
        assert is_allowed is False
        assert "not in allowed list" in error


class TestPermissionMiddleware:
    """Tests for PermissionMiddleware."""

    @pytest.mark.asyncio
    async def test_admin_role_allows_all_operations(self, echo_agent):
        """Test that admin role allows all operations."""
        agent = PermissionMiddleware(echo_agent, role=Role.ADMIN)

        # Should allow any message
        message = Message(role="user", content="delete file /tmp/test.txt")
        response = await agent.process(message)
        assert response.content == message.content

    @pytest.mark.asyncio
    async def test_user_role_blocks_dangerous_operations(self, echo_agent):
        """Test that user role blocks dangerous operations."""
        agent = PermissionMiddleware(echo_agent, role=Role.USER)

        # Should block shell execution
        message = Message(role="user", content="execute shell command rm -rf")

        with pytest.raises(PermissionDeniedError) as exc_info:
            await agent.process(message)

        assert "execute:shell" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_readonly_blocks_write_operations(self, echo_agent):
        """Test that readonly role blocks write operations."""
        agent = PermissionMiddleware(echo_agent, role=Role.READONLY)

        # Should block write operations
        message = Message(role="user", content="write file config.json")

        with pytest.raises(PermissionDeniedError) as exc_info:
            await agent.process(message)

        assert "write:files" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_restricted_blocks_most_operations(self, echo_agent):
        """Test that restricted role blocks most operations."""
        agent = PermissionMiddleware(echo_agent, role=Role.RESTRICTED)

        # Should block execute
        message = Message(role="user", content="execute command ls")

        with pytest.raises(PermissionDeniedError) as exc_info:
            await agent.process(message)

        assert "execute:commands" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_custom_permissions_override_role(self, echo_agent):
        """Test that custom permissions override role defaults."""
        custom_perms = {Permission.READ_FILES, Permission.WRITE_FILES}
        agent = PermissionMiddleware(
            echo_agent,
            role=Role.ADMIN,  # Would normally have all permissions
            custom_permissions=custom_perms
        )

        # Should block execute (not in custom perms)
        message = Message(role="user", content="execute command ls")

        with pytest.raises(PermissionDeniedError):
            await agent.process(message)

    @pytest.mark.asyncio
    async def test_has_permission_check(self, echo_agent):
        """Test the has_permission method."""
        agent = PermissionMiddleware(echo_agent, role=Role.USER)

        assert agent.has_permission(Permission.READ_FILES) is True
        assert agent.has_permission(Permission.WRITE_FILES) is True
        assert agent.has_permission(Permission.DELETE_FILES) is False
        assert agent.has_permission(Permission.ACCESS_SECRETS) is False

    @pytest.mark.asyncio
    async def test_name_property_delegates(self, echo_agent):
        """Test that name property delegates to wrapped agent."""
        agent = PermissionMiddleware(echo_agent, role=Role.USER)
        assert agent.name == echo_agent.name

    @pytest.mark.asyncio
    async def test_capabilities_property_delegates(self, echo_agent):
        """Test that capabilities property delegates to wrapped agent."""
        agent = PermissionMiddleware(echo_agent, role=Role.USER)
        assert agent.capabilities == echo_agent.capabilities

    @pytest.mark.asyncio
    async def test_detects_database_write_operations(self, echo_agent):
        """Test detection of database write operations."""
        agent = PermissionMiddleware(echo_agent, role=Role.READONLY)

        # Should block database writes
        message = Message(role="user", content="delete from users where id = 1")

        with pytest.raises(PermissionDeniedError) as exc_info:
            await agent.process(message)

        assert "write:database" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_allows_safe_content(self, echo_agent):
        """Test that safe content is allowed through."""
        agent = PermissionMiddleware(echo_agent, role=Role.USER)

        message = Message(role="user", content="What is the weather today?")
        response = await agent.process(message)

        assert response.content == message.content

    @pytest.mark.asyncio
    async def test_detects_delete_file_operations(self, echo_agent):
        """Test detection of file delete operations."""
        agent = PermissionMiddleware(echo_agent, role=Role.USER)

        message = Message(role="user", content="delete file /tmp/test.txt")

        with pytest.raises(PermissionDeniedError) as exc_info:
            await agent.process(message)

        assert "delete:files" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_detects_database_insert_operations(self, echo_agent):
        """Test detection of database insert operations."""
        agent = PermissionMiddleware(echo_agent, role=Role.READONLY)

        message = Message(role="user", content="insert into users (name) values ('Bob')")

        with pytest.raises(PermissionDeniedError) as exc_info:
            await agent.process(message)

        assert "write:database" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_detects_database_update_operations(self, echo_agent):
        """Test detection of database update operations."""
        agent = PermissionMiddleware(echo_agent, role=Role.READONLY)

        message = Message(role="user", content="update users set active = true")

        with pytest.raises(PermissionDeniedError) as exc_info:
            await agent.process(message)

        assert "write:database" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_detects_drop_table_operations(self, echo_agent):
        """Test detection of drop table operations."""
        agent = PermissionMiddleware(echo_agent, role=Role.READONLY)

        message = Message(role="user", content="drop table old_data")

        with pytest.raises(PermissionDeniedError) as exc_info:
            await agent.process(message)

        assert "write:database" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_allows_database_queries(self, echo_agent):
        """Test that database queries are allowed for READONLY."""
        agent = PermissionMiddleware(echo_agent, role=Role.READONLY)

        message = Message(role="user", content="select * from users")
        response = await agent.process(message)

        assert response.content == message.content

    @pytest.mark.asyncio
    async def test_permission_denied_error_includes_permission(self, echo_agent):
        """Test that PermissionDeniedError includes the required permission."""
        agent = PermissionMiddleware(echo_agent, role=Role.RESTRICTED)

        message = Message(role="user", content="write file test.txt")

        with pytest.raises(PermissionDeniedError) as exc_info:
            await agent.process(message)

        assert exc_info.value.required_permission == Permission.WRITE_FILES


class TestSandboxExtended:
    """Extended tests for Sandbox edge cases."""

    def test_sandbox_resource_limits(self):
        """Test sandbox resource limit configuration."""
        sandbox = Sandbox(
            max_file_size=5 * 1024 * 1024,  # 5MB
            max_execution_time=60,
            max_memory_mb=1024
        )

        assert sandbox.max_file_size == 5 * 1024 * 1024
        assert sandbox.max_execution_time == 60
        assert sandbox.max_memory_mb == 1024

    def test_sandbox_custom_denied_paths(self):
        """Test custom denied paths configuration."""
        sandbox = Sandbox(
            denied_paths={"/etc", "/var", "/usr/local/sensitive"}
        )

        is_allowed, error = sandbox.is_path_allowed("/var/log/test.log")
        assert is_allowed is False
        assert "denied directory" in error

    def test_sandbox_custom_allowed_commands(self):
        """Test custom allowed commands configuration."""
        sandbox = Sandbox(
            allowed_commands={"echo", "date", "whoami"}
        )

        is_allowed, _ = sandbox.is_command_allowed("echo hello")
        assert is_allowed is True

        is_allowed, error = sandbox.is_command_allowed("curl example.com")
        assert is_allowed is False
        assert "not in allowed list" in error

    def test_sandbox_sql_with_custom_operations(self):
        """Test SQL sandbox with custom allowed operations."""
        sandbox = Sandbox(
            allowed_sql_operations={"SELECT", "EXPLAIN", "DESCRIBE"}
        )

        is_allowed, _ = sandbox.is_sql_operation_allowed("DESCRIBE users")
        assert is_allowed is True

        is_allowed, error = sandbox.is_sql_operation_allowed("INSERT INTO users VALUES (1)")
        assert is_allowed is False
        assert "not allowed" in error

    def test_command_with_empty_string(self):
        """Test command validation with empty string."""
        sandbox = Sandbox()

        is_allowed, error = sandbox.is_command_allowed("")
        assert is_allowed is False  # Empty command is not in allowed list
        assert "not in allowed list" in error

    def test_sql_with_empty_string(self):
        """Test SQL validation with empty string."""
        sandbox = Sandbox()

        is_allowed, error = sandbox.is_sql_operation_allowed("")
        assert is_allowed is False
        assert "not allowed" in error

    def test_domain_with_subdomain(self):
        """Test domain validation with subdomains."""
        sandbox = Sandbox(
            allowed_domains={"example.com", "api.example.com"}
        )

        is_allowed, _ = sandbox.is_domain_allowed("api.example.com")
        assert is_allowed is True

        # Subdomain not explicitly allowed
        is_allowed, error = sandbox.is_domain_allowed("staging.example.com")
        assert is_allowed is False
        assert "not in allowed list" in error


def test_permissions_decorator():
    """Test permissions decorator function."""
    from agenkit.safety.permissions import permissions

    class TestAgent(Agent):
        @property
        def name(self) -> str:
            return "test"

        @property
        def capabilities(self) -> list[str]:
            return []

        async def process(self, message: Message) -> Message:
            return Message(role="assistant", content="test")

    base_agent = TestAgent()
    middleware_fn = permissions(role=Role.USER)

    agent = middleware_fn(base_agent)

    assert isinstance(agent, PermissionMiddleware)
    assert agent.role == Role.USER


def test_permissions_decorator_with_sandbox():
    """Test permissions decorator with custom sandbox."""
    from agenkit.safety.permissions import permissions

    class TestAgent(Agent):
        @property
        def name(self) -> str:
            return "test"

        @property
        def capabilities(self) -> list[str]:
            return []

        async def process(self, message: Message) -> Message:
            return Message(role="assistant", content="test")

    sandbox = Sandbox(allowed_paths={"/app/data"})
    base_agent = TestAgent()
    middleware_fn = permissions(role=Role.READONLY, sandbox=sandbox)

    agent = middleware_fn(base_agent)

    assert isinstance(agent, PermissionMiddleware)
    assert agent.role == Role.READONLY
    assert agent.sandbox == sandbox


def test_permissions_decorator_with_custom_permissions():
    """Test permissions decorator with custom permissions."""
    from agenkit.safety.permissions import permissions

    class TestAgent(Agent):
        @property
        def name(self) -> str:
            return "test"

        @property
        def capabilities(self) -> list[str]:
            return []

        async def process(self, message: Message) -> Message:
            return Message(role="assistant", content="test")

    custom_perms = {Permission.READ_FILES, Permission.QUERY_DATABASE}
    base_agent = TestAgent()
    middleware_fn = permissions(custom_permissions=custom_perms)

    agent = middleware_fn(base_agent)

    assert isinstance(agent, PermissionMiddleware)
    assert agent.permissions == custom_perms
