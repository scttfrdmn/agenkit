"""
Multi-Agent Collaboration Pattern

Enables multiple agents to work together on complex tasks through:
- Coordination: Agents working on different parts simultaneously
- Delegation: Agents delegating subtasks to specialists
- Consensus: Agents reaching agreement through discussion

This pattern is useful for:
- Complex tasks requiring diverse expertise
- Parallelizable workflows
- Problems benefiting from multiple perspectives
"""

from dataclasses import dataclass
from typing import Any

from agenkit import Agent, Message


@dataclass
class AgentTask:
    """A task assigned to an agent."""

    agent_name: str
    description: str
    result: Any = None
    status: str = "pending"  # pending, in_progress, completed, failed
    error: str | None = None


class MultiAgentOrchestrator(Agent):
    """
    Orchestrates multiple agents working together.

    Example:
        ```python
        from agenkit.patterns import MultiAgentOrchestrator

        orchestrator = MultiAgentOrchestrator()
        orchestrator.register_agent("researcher", research_agent)
        orchestrator.register_agent("writer", writing_agent)

        result = await orchestrator.process(
            Message(role="user", content="Write a research report")
        )
        ```
    """

    def __init__(self, strategy: str = "sequential"):
        self.agents: dict[str, Agent] = {}
        self.strategy = strategy  # sequential, parallel, or delegate
        self.tasks: list[AgentTask] = []

    @property
    def name(self) -> str:
        return "MultiAgentOrchestrator"

    def register_agent(self, name: str, agent: Agent) -> None:
        """Register an agent that can be used."""
        self.agents[name] = agent

    def unregister_agent(self, name: str) -> None:
        """Remove an agent."""
        self.agents.pop(name, None)

    def list_agents(self) -> list[str]:
        """Get list of registered agents."""
        return list(self.agents.keys())

    async def process(self, message: Message) -> Message:
        """Process message by coordinating multiple agents."""
        # Simple implementation: delegate to all agents sequentially
        results = []

        for agent_name, agent in self.agents.items():
            task = AgentTask(agent_name=agent_name, description=message.content)
            task.status = "in_progress"
            self.tasks.append(task)

            try:
                response = await agent.process(message)
                task.result = response.content
                task.status = "completed"
                results.append(f"{agent_name}: {response.content}")
            except Exception as e:
                task.error = str(e)
                task.status = "failed"
                results.append(f"{agent_name}: Failed - {e}")

        combined_result = "\n\n".join(results)
        return Message(role="assistant", content=combined_result)

    def get_tasks(self) -> list[AgentTask]:
        """Get all tasks executed."""
        return self.tasks.copy()


class ConsensusAgent(Agent):
    """
    Reaches consensus among multiple agents.

    Example:
        ```python
        consensus = ConsensusAgent()
        consensus.add_agent(agent1)
        consensus.add_agent(agent2)
        consensus.add_agent(agent3)

        result = await consensus.process(
            Message(role="user", content="What's the best approach?")
        )
        # Result combines perspectives from all agents
        ```
    """

    def __init__(self, voting_strategy: str = "majority"):
        self.agents: list[Agent] = []
        self.voting_strategy = voting_strategy

    @property
    def name(self) -> str:
        return "ConsensusAgent"

    def add_agent(self, agent: Agent) -> None:
        """Add an agent to the consensus group."""
        self.agents.append(agent)

    async def process(self, message: Message) -> Message:
        """Get responses from all agents and form consensus."""
        responses = []

        for agent in self.agents:
            response = await agent.process(message)
            responses.append(response.content)

        # Simple consensus: combine all responses
        consensus = f"Consensus from {len(responses)} agents:\n\n"
        consensus += "\n\n".join([f"Agent {i + 1}: {r}" for i, r in enumerate(responses)])

        return Message(role="assistant", content=consensus)
