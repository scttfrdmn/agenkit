"""
Authentication and Authorization for Agenkit

Provides authentication middleware for securing HTTP and gRPC servers.

Key Features:
- Bearer token authentication
- API key authentication
- Configurable auth providers
- Role-based access control (RBAC)
- Rate limiting per user

Example:
    >>> from agenkit.auth import BearerTokenAuth, SimpleTokenProvider
    >>>
    >>> # Create token provider
    >>> provider = SimpleTokenProvider({
    ...     "secret-token-123": {"user_id": "user1", "roles": ["admin"]},
    ...     "another-token-456": {"user_id": "user2", "roles": ["user"]},
    ... })
    >>>
    >>> # Wrap agent with authentication
    >>> auth = BearerTokenAuth(agent, provider, required_role="user")
    >>>
    >>> # Requests without valid token will be rejected
    >>> response = await auth.process(message)  # Checks metadata for token
"""

from .middleware import APIKeyAuth, BearerTokenAuth
from .providers import (AuthenticationError, AuthorizationError, AuthProvider,
                        EnvTokenProvider, SimpleTokenProvider, User)

__all__ = [
    "APIKeyAuth",
    "AuthProvider",
    "AuthenticationError",
    "AuthorizationError",
    "BearerTokenAuth",
    "EnvTokenProvider",
    "SimpleTokenProvider",
    "User",
]
