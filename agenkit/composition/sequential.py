"""Sequential agent composition pattern."""


from agenkit.interfaces import Agent, Message


class SequentialAgent(Agent):
    """Agent that executes multiple agents in sequence.

    The output of one agent becomes the input to the next agent.
    """

    def __init__(self, name: str, agents: list[Agent]):
        """Initialize sequential agent.

        Args:
            name: Name of this sequential agent
            agents: List of agents to execute in sequence

        Raises:
            ValueError: If agents list is empty
        """
        if not agents:
            raise ValueError("Sequential agent requires at least one agent")

        self._name = name
        self._agents = agents

    @property
    def name(self) -> str:
        """Return the name of the sequential agent."""
        return self._name

    @property
    def capabilities(self) -> list[str]:
        """Return combined capabilities of all agents."""
        caps_set = set()
        for agent in self._agents:
            caps_set.update(agent.capabilities)
        caps = list(caps_set)
        caps.append("sequential")
        return caps

    async def process(self, message: Message) -> Message:
        """Execute all agents in sequence.

        Args:
            message: Input message

        Returns:
            Output message from the last agent in the sequence

        Raises:
            Exception: If any agent in the sequence fails
        """
        current = message

        for i, agent in enumerate(self._agents):
            try:
                result = await agent.process(current)
                current = result
            except Exception as e:
                raise Exception(f"Step {i+1} ({agent.name}) failed: {e}") from e

        return current

    def get_agents(self) -> list[Agent]:
        """Return the list of agents in the sequence."""
        return self._agents
