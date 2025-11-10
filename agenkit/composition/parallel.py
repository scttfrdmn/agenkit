"""Parallel agent composition pattern."""

import asyncio
from dataclasses import dataclass
from typing import List, Optional

from agenkit.interfaces import Agent, Message


@dataclass
class AgentResult:
    """Result from a single agent execution."""

    agent_name: str
    message: Optional[Message]
    error: Optional[Exception]


class ParallelAgent(Agent):
    """Agent that executes multiple agents concurrently and combines their results."""

    def __init__(self, name: str, agents: List[Agent]):
        """Initialize parallel agent.

        Args:
            name: Name of this parallel agent
            agents: List of agents to execute in parallel

        Raises:
            ValueError: If agents list is empty
        """
        if not agents:
            raise ValueError("Parallel agent requires at least one agent")

        self._name = name
        self._agents = agents

    @property
    def name(self) -> str:
        """Return the name of the parallel agent."""
        return self._name

    @property
    def capabilities(self) -> list[str]:
        """Return combined capabilities of all agents."""
        caps_set = set()
        for agent in self._agents:
            caps_set.update(agent.capabilities)
        caps = list(caps_set)
        caps.append("parallel")
        return caps

    async def process(self, message: Message) -> Message:
        """Execute all agents in parallel and combine their results.

        Args:
            message: Input message

        Returns:
            Combined message with results from all agents

        Raises:
            Exception: If any agent fails
        """
        # Create tasks for all agents
        tasks = [self._execute_agent(agent, message) for agent in self._agents]

        # Wait for all agents to complete
        results = await asyncio.gather(*tasks)

        # Check for errors
        errors = []
        for result in results:
            if result.error:
                errors.append(f"{result.agent_name}: {result.error}")

        if errors:
            raise Exception(f"Parallel execution had errors: {'; '.join(errors)}")

        # Combine all responses
        return self._combine_responses(results)

    async def _execute_agent(self, agent: Agent, message: Message) -> AgentResult:
        """Execute a single agent and return the result.

        Args:
            agent: Agent to execute
            message: Input message

        Returns:
            Agent result containing message or error
        """
        try:
            result = await agent.process(message)
            return AgentResult(agent_name=agent.name, message=result, error=None)
        except Exception as e:
            return AgentResult(agent_name=agent.name, message=None, error=e)

    def _combine_responses(self, results: List[AgentResult]) -> Message:
        """Combine multiple agent responses into a single message.

        Args:
            results: List of agent results

        Returns:
            Combined message with all agent outputs
        """
        content_parts = []
        combined_metadata = {}

        for result in results:
            if result.message:
                content_parts.append(f"[{result.agent_name}]: {result.message.content}")

                # Merge metadata with agent name prefix
                for key, value in result.message.metadata.items():
                    prefixed_key = f"{result.agent_name}.{key}"
                    combined_metadata[prefixed_key] = value

        response = Message(role="agent", content="\n".join(content_parts))
        response.metadata = combined_metadata
        return response

    def get_agents(self) -> List[Agent]:
        """Return the list of agents that run in parallel."""
        return self._agents
