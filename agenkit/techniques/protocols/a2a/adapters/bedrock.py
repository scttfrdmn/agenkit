"""
AWS Bedrock Adapter for A2A.

Integrates Agenkit agents with AWS Bedrock Agents.
"""

from typing import TYPE_CHECKING, Any

from ..server import A2AServer

if TYPE_CHECKING:
    from agenkit import Agent


class BedrockAdapter:
    """
    Adapter for AWS Bedrock Agents.

    Enables Agenkit agents to integrate with AWS Bedrock's agent ecosystem.

    Note: This is a foundation implementation. Full Bedrock integration
    requires the boto3 SDK and proper AWS authentication.

    Example:
        >>> from agenkit.patterns import ReActAgent
        >>> from agenkit.techniques.protocols.a2a import BedrockAdapter
        >>>
        >>> agent = ReActAgent(llm=my_llm, tools=[...])
        >>>
        >>> adapter = BedrockAdapter.from_agent(
        ...     agent=agent,
        ...     agent_id="my-bedrock-agent",
        ...     region="us-east-1"
        ... )
        >>>
        >>> # Deploy for Bedrock
        >>> await adapter.deploy()
    """

    def __init__(
        self,
        agent_id: str,
        agent: "Agent",
        capabilities: list[str],
        region: str = "us-east-1",
        account_id: str | None = None
    ):
        """
        Initialize Bedrock adapter.

        Args:
            agent_id: Unique agent identifier
            agent: Agenkit agent
            capabilities: Agent capabilities
            region: AWS region
            account_id: Optional AWS account ID
        """
        self.agent_id = agent_id
        self.agent = agent
        self.capabilities = capabilities
        self.region = region
        self.account_id = account_id

        # Create A2A server
        self.server = A2AServer(
            agent_id=agent_id,
            agent=agent,
            capabilities=capabilities,
            name=f"bedrock-{agent_id}"
        )

    @staticmethod
    def from_agent(
        agent: "Agent",
        agent_id: str | None = None,
        region: str = "us-east-1",
        capabilities: list[str] | None = None,
        account_id: str | None = None
    ) -> "BedrockAdapter":
        """
        Create adapter from Agenkit agent.

        Args:
            agent: Agenkit agent
            agent_id: Optional agent ID (defaults to agent.name)
            region: AWS region
            capabilities: Optional capabilities (defaults to agent.capabilities)
            account_id: Optional AWS account ID

        Returns:
            BedrockAdapter instance
        """
        if agent_id is None:
            agent_id = getattr(agent, 'name', 'agenkit-agent')
            agent_id = agent_id.replace('_', '-').replace(' ', '-').lower()

        if capabilities is None:
            capabilities = getattr(agent, 'capabilities', ['general'])

        return BedrockAdapter(
            agent_id=agent_id,
            agent=agent,
            capabilities=capabilities,
            region=region,
            account_id=account_id
        )

    async def deploy(
        self,
        host: str = "0.0.0.0",  # noqa: S104 - Server must bind to all interfaces for deployment
        port: int = 8080,
        **kwargs
    ):
        """
        Deploy agent for Bedrock integration.

        This starts an A2A server that Bedrock can connect to.

        Note: In production, you would also register the agent with
        AWS Bedrock using the boto3 SDK.

        Args:
            host: Host to bind to
            port: Port to bind to
            **kwargs: Additional options
        """
        # Start A2A server
        await self.server.start(
            transport="http",
            host=host,
            port=port,
            **kwargs
        )

        endpoint = f"http://{host}:{port}/a2a"

        print("Agent deployed for AWS Bedrock integration")
        print(f"Region: {self.region}")
        if self.account_id:
            print(f"Account: {self.account_id}")
        print(f"Endpoint: {endpoint}")
        print()
        print("To complete integration, register this endpoint with")
        print("AWS Bedrock Agents using the AWS Console or boto3 SDK.")

    async def register_with_bedrock(self):
        """
        Register agent with AWS Bedrock.

        Note: Requires boto3 SDK.

        Raises:
            NotImplementedError: SDK integration not yet implemented
        """
        raise NotImplementedError(
            "Full AWS Bedrock SDK integration requires boto3. "
            "For now, manually register the A2A endpoint in AWS Bedrock. "
            "Visit: https://console.aws.amazon.com/bedrock/home#/agents"
        )

    def get_bedrock_config(self) -> dict[str, Any]:
        """
        Get configuration for AWS Bedrock.

        Returns:
            Configuration dictionary
        """
        config = {
            "agent_id": self.agent_id,
            "region": self.region,
            "capabilities": self.capabilities,
            "protocol": "a2a",
            "transport": "http"
        }

        if self.account_id:
            config["account_id"] = self.account_id

        return config

    async def stop(self):
        """Stop the server."""
        await self.server.stop()


def create_bedrock_agent(
    agent: "Agent",
    region: str = "us-east-1",
    **kwargs
) -> BedrockAdapter:
    """
    Convenience function to create Bedrock adapter.

    Args:
        agent: Agenkit agent
        region: AWS region
        **kwargs: Additional options

    Returns:
        BedrockAdapter instance
    """
    return BedrockAdapter.from_agent(
        agent=agent,
        region=region,
        **kwargs
    )
