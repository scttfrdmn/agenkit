"""Authentication middleware for securing agents."""

from ..interfaces import Agent, Message
from .providers import AuthenticationError, AuthorizationError, AuthProvider


class BearerTokenAuth(Agent):
    """Bearer token authentication middleware.

    Validates Bearer tokens from message metadata and enforces role-based access.

    Example:
        >>> from agenkit.auth import BearerTokenAuth, SimpleTokenProvider
        >>>
        >>> provider = SimpleTokenProvider({
        ...     "token-123": {"user_id": "user1", "roles": ["admin"]}
        ... })
        >>>
        >>> auth_agent = BearerTokenAuth(
        ...     agent=base_agent,
        ...     provider=provider,
        ...     required_role="user"
        ... )
        >>>
        >>> # Message must include auth token in metadata
        >>> message = Message(
        ...     role="user",
        ...     content="Hello",
        ...     metadata={"authorization": "Bearer token-123"}
        ... )
        >>> response = await auth_agent.process(message)
    """

    def __init__(
        self,
        agent: Agent,
        provider: AuthProvider,
        required_role: str | None = None,
        required_permission: str | None = None,
    ):
        """Initialize bearer token authentication.

        Args:
            agent: Agent to protect
            provider: Authentication provider
            required_role: Optional role requirement
            required_permission: Optional permission requirement
        """
        self.agent = agent
        self.provider = provider
        self.required_role = required_role
        self.required_permission = required_permission

    @property
    def name(self) -> str:
        return f"auth_{self.agent.name}"

    @property
    def capabilities(self) -> list[str]:
        caps = self.agent.capabilities.copy()
        caps.append("authentication")
        return caps

    async def process(self, message: Message) -> Message:
        """Process message with authentication."""
        # Extract token from metadata
        token = self._extract_token(message)

        if not token:
            raise AuthenticationError("No authentication token provided")

        # Authenticate
        user = await self.provider.authenticate(token)

        # Check role requirement
        if self.required_role and not user.has_role(self.required_role):
            raise AuthorizationError(
                f"User {user.user_id} lacks required role: {self.required_role}"
            )

        # Check permission requirement
        if self.required_permission and not user.has_permission(self.required_permission):
            raise AuthorizationError(
                f"User {user.user_id} lacks required permission: {self.required_permission}"
            )

        # Add user info to metadata for downstream use (Message.metadata is
        # always a dict, never None -- normalized at construction, #919)
        message.metadata["authenticated_user"] = {
            "user_id": user.user_id,
            "roles": user.roles,
            "permissions": list(user.permissions),
        }

        # Process with underlying agent
        return await self.agent.process(message)

    def _extract_token(self, message: Message) -> str | None:
        """Extract bearer token from message metadata.

        Looks for:
        - metadata["authorization"] = "Bearer <token>"
        - metadata["token"] = "<token>"
        """
        if not message.metadata:
            return None

        # Check authorization header
        auth_header = message.metadata.get("authorization", "")
        if isinstance(auth_header, str) and auth_header.startswith("Bearer "):
            return auth_header[7:]  # Remove "Bearer " prefix

        # Check token field
        return message.metadata.get("token")


class APIKeyAuth(Agent):
    """API key authentication middleware.

    Validates API keys from message metadata.

    Example:
        >>> from agenkit.auth import APIKeyAuth, SimpleTokenProvider
        >>>
        >>> provider = SimpleTokenProvider({
        ...     "api-key-xyz": {"user_id": "service1", "roles": ["service"]}
        ... })
        >>>
        >>> auth_agent = APIKeyAuth(agent=base_agent, provider=provider)
        >>>
        >>> # Message must include API key
        >>> message = Message(
        ...     role="user",
        ...     content="Hello",
        ...     metadata={"api_key": "api-key-xyz"}
        ... )
        >>> response = await auth_agent.process(message)
    """

    def __init__(self, agent: Agent, provider: AuthProvider, key_name: str = "api_key"):
        """Initialize API key authentication.

        Args:
            agent: Agent to protect
            provider: Authentication provider
            key_name: Metadata field name for API key
        """
        self.agent = agent
        self.provider = provider
        self.key_name = key_name

    @property
    def name(self) -> str:
        return f"apikey_{self.agent.name}"

    @property
    def capabilities(self) -> list[str]:
        caps = self.agent.capabilities.copy()
        caps.append("api_key_auth")
        return caps

    async def process(self, message: Message) -> Message:
        """Process message with API key authentication."""
        # Extract API key
        if not message.metadata or self.key_name not in message.metadata:
            raise AuthenticationError(f"No API key provided in metadata['{self.key_name}']")

        api_key = message.metadata[self.key_name]

        # Authenticate
        user = await self.provider.authenticate(api_key)

        # Add user info to metadata (Message.metadata is always a dict,
        # never None -- normalized at construction, #919)
        message.metadata["authenticated_user"] = {"user_id": user.user_id, "roles": user.roles}

        # Process with underlying agent
        return await self.agent.process(message)
