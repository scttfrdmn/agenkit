"""Authentication providers for validating tokens and users."""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


class AuthenticationError(Exception):
    """Raised when authentication fails."""

    pass


class AuthorizationError(Exception):
    """Raised when user lacks required permissions."""

    pass


@dataclass
class User:
    """Authenticated user information."""

    user_id: str
    roles: list[str] = field(default_factory=list)
    permissions: set[str] = field(default_factory=set)
    metadata: dict[str, any] = field(default_factory=dict)

    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return role in self.roles

    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission."""
        return permission in self.permissions


class AuthProvider(ABC):
    """Abstract base class for authentication providers."""

    @abstractmethod
    async def authenticate(self, token: str) -> User:
        """Authenticate a token and return user information.

        Args:
            token: Authentication token

        Returns:
            User information

        Raises:
            AuthenticationError: If token is invalid
        """
        pass


class SimpleTokenProvider(AuthProvider):
    """Simple in-memory token provider for development/testing.

    Example:
        >>> provider = SimpleTokenProvider({
        ...     "admin-token": {
        ...         "user_id": "admin",
        ...         "roles": ["admin", "user"],
        ...         "permissions": {"read", "write", "delete"}
        ...     },
        ...     "user-token": {
        ...         "user_id": "user1",
        ...         "roles": ["user"],
        ...         "permissions": {"read"}
        ...     }
        ... })
        >>> user = await provider.authenticate("admin-token")
    """

    def __init__(self, tokens: dict[str, dict]):
        """Initialize with token mapping.

        Args:
            tokens: Map of token -> user info
        """
        self.tokens = tokens

    async def authenticate(self, token: str) -> User:
        """Authenticate token."""
        if token not in self.tokens:
            raise AuthenticationError("Invalid token")

        user_data = self.tokens[token]
        return User(
            user_id=user_data["user_id"],
            roles=user_data.get("roles", []),
            permissions=set(user_data.get("permissions", [])),
            metadata=user_data.get("metadata", {}),
        )


class EnvTokenProvider(AuthProvider):
    """Token provider that validates against environment variable.

    Useful for simple deployments with a single API key.

    Example:
        >>> # Set environment variable: AGENKIT_API_KEY=secret-key-123
        >>> provider = EnvTokenProvider("AGENKIT_API_KEY")
        >>> user = await provider.authenticate("secret-key-123")
    """

    def __init__(
        self,
        env_var: str = "AGENKIT_API_KEY",
        user_id: str = "api_user",
        roles: list[str] | None = None,
    ):
        """Initialize with environment variable name.

        Args:
            env_var: Environment variable containing valid API key
            user_id: User ID to assign to authenticated requests
            roles: Roles to assign to authenticated user
        """
        self.env_var = env_var
        self.user_id = user_id
        self.roles = roles or ["user"]
        self.valid_token = os.getenv(env_var)

        if not self.valid_token:
            raise ValueError(f"Environment variable {env_var} not set")

    async def authenticate(self, token: str) -> User:
        """Authenticate token."""
        if token != self.valid_token:
            raise AuthenticationError("Invalid API key")

        return User(
            user_id=self.user_id,
            roles=self.roles,
            permissions=set(),
            metadata={"auth_method": "env_token"},
        )
