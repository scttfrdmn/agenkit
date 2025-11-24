"""
Bearer Token Authentication Example

Demonstrates how to secure agents with bearer token authentication.

This example shows:
1. Setting up authentication providers
2. Protecting agents with bearer tokens
3. Role-based access control
4. Handling authentication errors
"""

import asyncio
from agenkit.auth import BearerTokenAuth, SimpleTokenProvider, AuthenticationError
from agenkit.interfaces import Message


# Simple echo agent for demonstration
class EchoAgent:
    """Simple agent that echoes messages."""

    @property
    def name(self) -> str:
        return "echo_agent"

    @property
    def capabilities(self) -> list[str]:
        return ["echo"]

    async def process(self, message: Message) -> Message:
        """Echo the message back."""
        user_info = message.metadata.get("authenticated_user", {})
        user_id = user_info.get("user_id", "unknown")

        return Message(
            role="assistant",
            content=f"[Authenticated as {user_id}] Echo: {message.content}"
        )


async def example_1_basic_auth():
    """Example 1: Basic bearer token authentication."""
    print("=" * 60)
    print("Example 1: Basic Bearer Token Authentication")
    print("=" * 60)

    # Create token provider with valid tokens
    provider = SimpleTokenProvider({
        "admin-secret-token": {
            "user_id": "admin",
            "roles": ["admin", "user"],
            "permissions": {"read", "write", "delete"}
        },
        "user-secret-token": {
            "user_id": "user1",
            "roles": ["user"],
            "permissions": {"read"}
        }
    })

    # Wrap agent with authentication
    base_agent = EchoAgent()
    auth_agent = BearerTokenAuth(agent=base_agent, provider=provider)

    print("\n✅ Success: Valid token")
    # Request with valid token
    message = Message(
        role="user",
        content="Hello, secure agent!",
        metadata={"authorization": "Bearer admin-secret-token"}
    )
    response = await auth_agent.process(message)
    print(f"Response: {response.content}")

    print("\n❌ Failure: Invalid token")
    # Request with invalid token
    try:
        invalid_message = Message(
            role="user",
            content="Trying with bad token",
            metadata={"authorization": "Bearer invalid-token"}
        )
        await auth_agent.process(invalid_message)
    except AuthenticationError as e:
        print(f"Authentication failed: {e}")

    print("\n❌ Failure: No token")
    # Request without token
    try:
        no_token_message = Message(
            role="user",
            content="No token provided",
            metadata={}
        )
        await auth_agent.process(no_token_message)
    except AuthenticationError as e:
        print(f"Authentication failed: {e}")


async def example_2_role_based_access():
    """Example 2: Role-based access control."""
    print("\n" + "=" * 60)
    print("Example 2: Role-Based Access Control (RBAC)")
    print("=" * 60)

    provider = SimpleTokenProvider({
        "admin-token": {
            "user_id": "admin",
            "roles": ["admin"],
        },
        "user-token": {
            "user_id": "user1",
            "roles": ["user"],
        }
    })

    base_agent = EchoAgent()

    # Create admin-only agent
    admin_agent = BearerTokenAuth(
        agent=base_agent,
        provider=provider,
        required_role="admin"
    )

    print("\n✅ Admin access with admin token")
    admin_message = Message(
        role="user",
        content="Admin command",
        metadata={"authorization": "Bearer admin-token"}
    )
    response = await admin_agent.process(admin_message)
    print(f"Response: {response.content}")

    print("\n❌ Admin access denied for regular user")
    try:
        user_message = Message(
            role="user",
            content="User trying admin command",
            metadata={"authorization": "Bearer user-token"}
        )
        await admin_agent.process(user_message)
    except Exception as e:
        print(f"Authorization failed: {e}")


async def example_3_production_pattern():
    """Example 3: Production deployment pattern."""
    print("\n" + "=" * 60)
    print("Example 3: Production Pattern")
    print("=" * 60)

    print("""
💡 Production Best Practices:

1. **Use Environment Variables for Tokens**:
   from agenkit.auth import EnvTokenProvider

   # Set environment: AGENKIT_API_KEY=your-secret-key
   provider = EnvTokenProvider("AGENKIT_API_KEY")

2. **Implement Custom Providers**:
   class DatabaseTokenProvider(AuthProvider):
       async def authenticate(self, token):
           # Query database to validate token
           user = await db.get_user_by_token(token)
           if not user:
               raise AuthenticationError("Invalid token")
           return User(user_id=user.id, roles=user.roles)

3. **Combine with TLS**:
   # Always use HTTPS/TLS in production
   transport = GRPCTransport("grpcs://api.example.com:443")

   # AND use authentication
   auth_agent = BearerTokenAuth(agent, provider)

4. **Add Rate Limiting** (recommended):
   from agenkit.middleware import RateLimitMiddleware

   # First rate limit, then authenticate
   protected_agent = RateLimitMiddleware(
       BearerTokenAuth(agent, provider),
       max_requests=100,
       window_seconds=60
   )

5. **Log Authentication Events**:
   import logging

   logger = logging.getLogger("agenkit.auth")
   logger.info(f"User {user.user_id} authenticated")

6. **Rotate Tokens Regularly**:
   - Use short-lived tokens (e.g., JWTs with expiration)
   - Implement token refresh mechanisms
   - Revoke compromised tokens immediately
""")

    print("\n✅ Security checklist for production:")
    print("  ✓ TLS/HTTPS enabled")
    print("  ✓ Authentication required")
    print("  ✓ Tokens stored securely (environment variables)")
    print("  ✓ Role-based access control")
    print("  ✓ Rate limiting enabled")
    print("  ✓ Authentication events logged")
    print("  ✓ Regular token rotation")


async def main():
    """Run all examples."""
    print("\n🔐 Bearer Token Authentication Examples")
    print("=" * 60)

    await example_1_basic_auth()
    await example_2_role_based_access()
    await example_3_production_pattern()

    print("\n" + "=" * 60)
    print("✅ Examples Complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
