"""Fallback agent composition pattern."""

from typing import List

from agenkit.interfaces import Agent, Message


class FallbackAgent(Agent):
    """Agent that tries agents in order until one succeeds.

    This implements the Fallback/Retry pattern for reliability.
    """

    def __init__(self, name: str, agents: List[Agent]):
        """Initialize fallback agent.

        Args:
            name: Name of this fallback agent
            agents: List of agents to try in order

        Raises:
            ValueError: If agents list is empty
        """
        if not agents:
            raise ValueError("Fallback agent requires at least one agent")

        self._name = name
        self._agents = agents

    @property
    def name(self) -> str:
        """Return the name of the fallback agent."""
        return self._name

    @property
    def capabilities(self) -> list[str]:
        """Return combined capabilities of all agents."""
        caps_set = set()
        for agent in self._agents:
            caps_set.update(agent.capabilities)
        caps = list(caps_set)
        caps.append("fallback")
        return caps

    async def process(self, message: Message) -> Message:
        """Try each agent in order until one succeeds.

        Args:
            message: Input message

        Returns:
            Response from the first successful agent

        Raises:
            Exception: If all agents fail
        """
        errors = []

        for i, agent in enumerate(self._agents):
            try:
                result = await agent.process(message)

                # Success! Add metadata about which agent was used
                result.metadata["fallback_agent_used"] = agent.name
                result.metadata["fallback_attempt"] = i + 1
                return result

            except Exception as e:
                errors.append(f"agent {i+1} ({agent.name}): {e}")

        # All agents failed
        raise Exception(f"All {len(self._agents)} agents failed: {'; '.join(errors)}")

    def get_agents(self) -> List[Agent]:
        """Return the list of fallback agents."""
        return self._agents
