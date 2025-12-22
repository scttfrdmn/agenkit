"""
Vertex AI Adapter for A2A.

Integrates Agenkit agents with Google Cloud Vertex AI Agent Builder.
"""

from typing import TYPE_CHECKING, Any

from ..server import A2AServer

if TYPE_CHECKING:
    from agenkit import Agent


class VertexAIAdapter:
    """
    Adapter for Google Cloud Vertex AI Agent Builder.

    Enables Agenkit agents to integrate with Vertex AI's agent ecosystem.

    Note: This is a foundation implementation. Full Vertex AI integration
    requires the google-cloud-aiplatform SDK and proper authentication.

    Example:
        >>> from agenkit.patterns import ReActAgent
        >>> from agenkit.techniques.protocols.a2a import VertexAIAdapter
        >>>
        >>> agent = ReActAgent(llm=my_llm, tools=[...])
        >>>
        >>> adapter = VertexAIAdapter.from_agent(
        ...     agent=agent,
        ...     project_id="my-project",
        ...     location="us-central1"
        ... )
        >>>
        >>> # Deploy to Vertex AI
        >>> await adapter.deploy()
    """

    def __init__(
        self,
        agent_id: str,
        agent: "Agent",
        capabilities: list[str],
        project_id: str,
        location: str = "us-central1",
    ):
        """
        Initialize Vertex AI adapter.

        Args:
            agent_id: Unique agent identifier
            agent: Agenkit agent
            capabilities: Agent capabilities
            project_id: Google Cloud project ID
            location: Google Cloud location
        """
        self.agent_id = agent_id
        self.agent = agent
        self.capabilities = capabilities
        self.project_id = project_id
        self.location = location

        # Create A2A server
        self.server = A2AServer(
            agent_id=agent_id, agent=agent, capabilities=capabilities, name=f"vertex-{agent_id}"
        )

    @staticmethod
    def from_agent(
        agent: "Agent",
        project_id: str,
        location: str = "us-central1",
        agent_id: str | None = None,
        capabilities: list[str] | None = None,
    ) -> "VertexAIAdapter":
        """
        Create adapter from Agenkit agent.

        Args:
            agent: Agenkit agent
            project_id: Google Cloud project ID
            location: Google Cloud location
            agent_id: Optional agent ID (defaults to agent.name)
            capabilities: Optional capabilities (defaults to agent.capabilities)

        Returns:
            VertexAIAdapter instance
        """
        if agent_id is None:
            agent_id = getattr(agent, "name", "agenkit-agent")
            agent_id = agent_id.replace("_", "-").replace(" ", "-").lower()

        if capabilities is None:
            capabilities = getattr(agent, "capabilities", ["general"])

        return VertexAIAdapter(
            agent_id=agent_id,
            agent=agent,
            capabilities=capabilities,
            project_id=project_id,
            location=location,
        )

    async def deploy(
        self,
        host: str = "0.0.0.0",  # noqa: S104 - Server must bind to all interfaces for deployment
        port: int = 8080,
        **kwargs,
    ):
        """
        Deploy agent to Vertex AI.

        This starts an A2A server that Vertex AI can connect to.

        Note: In production, you would also register the agent with
        Vertex AI Agent Builder using the google-cloud-aiplatform SDK.

        Args:
            host: Host to bind to
            port: Port to bind to
            **kwargs: Additional options
        """
        # Start A2A server
        await self.server.start(transport="http", host=host, port=port, **kwargs)

        endpoint = f"http://{host}:{port}/a2a"

        print("Agent deployed for Vertex AI integration")
        print(f"Project: {self.project_id}")
        print(f"Location: {self.location}")
        print(f"Endpoint: {endpoint}")
        print()
        print("To complete integration, register this endpoint with")
        print("Vertex AI Agent Builder using the Cloud Console or SDK.")

    async def register_with_vertex(self):
        """
        Register agent with Vertex AI Agent Builder.

        Note: Requires google-cloud-aiplatform SDK.

        Raises:
            NotImplementedError: SDK integration not yet implemented
        """
        raise NotImplementedError(
            "Full Vertex AI SDK integration requires google-cloud-aiplatform. "
            "For now, manually register the A2A endpoint in Vertex AI Agent Builder. "
            "Visit: https://console.cloud.google.com/vertex-ai/agents"
        )

    def get_vertex_config(self) -> dict[str, Any]:
        """
        Get configuration for Vertex AI Agent Builder.

        Returns:
            Configuration dictionary
        """
        return {
            "agent_id": self.agent_id,
            "project_id": self.project_id,
            "location": self.location,
            "capabilities": self.capabilities,
            "protocol": "a2a",
            "transport": "http",
        }

    async def stop(self):
        """Stop the server."""
        await self.server.stop()


def create_vertex_agent(
    agent: "Agent", project_id: str, location: str = "us-central1", **kwargs
) -> VertexAIAdapter:
    """
    Convenience function to create Vertex AI adapter.

    Args:
        agent: Agenkit agent
        project_id: Google Cloud project ID
        location: Google Cloud location
        **kwargs: Additional options

    Returns:
        VertexAIAdapter instance
    """
    return VertexAIAdapter.from_agent(
        agent=agent, project_id=project_id, location=location, **kwargs
    )
