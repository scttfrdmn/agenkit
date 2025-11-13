"""Conditional agent composition pattern."""

from collections.abc import Callable
from dataclasses import dataclass

from agenkit.interfaces import Agent, Message

# Type alias for condition functions
Condition = Callable[[Message], bool]


@dataclass
class ConditionalRoute:
    """Represents a condition-agent pair."""

    condition: Condition
    agent: Agent


class ConditionalAgent(Agent):
    """Agent that routes messages to different agents based on conditions."""

    def __init__(self, name: str, default_agent: Agent):
        """Initialize conditional agent.

        Args:
            name: Name of this conditional agent
            default_agent: Agent to use when no condition matches
        """
        self._name = name
        self._routes: list[ConditionalRoute] = []
        self._default_agent = default_agent

    def add_route(self, condition: Condition, agent: Agent) -> None:
        """Add a conditional route.

        Args:
            condition: Function that returns True if this agent should be used
            agent: Agent to use when condition is met
        """
        self._routes.append(ConditionalRoute(condition=condition, agent=agent))

    @property
    def name(self) -> str:
        """Return the name of the conditional agent."""
        return self._name

    @property
    def capabilities(self) -> list[str]:
        """Return combined capabilities of all agents."""
        caps_set = set()

        # Add default agent capabilities
        if self._default_agent:
            caps_set.update(self._default_agent.capabilities)

        # Add route agent capabilities
        for route in self._routes:
            caps_set.update(route.agent.capabilities)

        caps = list(caps_set)
        caps.append("conditional")
        return caps

    async def process(self, message: Message) -> Message:
        """Route the message to the first agent whose condition is met.

        Args:
            message: Input message

        Returns:
            Response from the selected agent

        Raises:
            Exception: If no condition matches and no default agent configured
        """
        # Try each route in order
        for i, route in enumerate(self._routes):
            if route.condition(message):
                try:
                    result = await route.agent.process(message)

                    # Add metadata about routing decision
                    result.metadata["conditional_agent_used"] = route.agent.name
                    result.metadata["conditional_route"] = i + 1
                    return result

                except Exception as e:
                    raise Exception(f"Route {i+1} ({route.agent.name}) failed: {e}") from e

        # No condition matched, use default agent
        if not self._default_agent:
            raise Exception("No condition matched and no default agent configured")

        try:
            result = await self._default_agent.process(message)

            # Add metadata about using default
            result.metadata["conditional_agent_used"] = self._default_agent.name
            result.metadata["conditional_route"] = "default"
            return result

        except Exception as e:
            raise Exception(f"Default agent ({self._default_agent.name}) failed: {e}") from e

    def get_routes(self) -> list[ConditionalRoute]:
        """Return the conditional routes."""
        return self._routes

    def get_default_agent(self) -> Agent:
        """Return the default agent."""
        return self._default_agent


# Common condition helpers


def content_contains(substr: str) -> Condition:
    """Return a condition that checks if message content contains a substring.

    Args:
        substr: Substring to search for

    Returns:
        Condition function
    """

    def condition(message: Message) -> bool:
        return substr in message.content

    return condition


def role_equals(role: str) -> Condition:
    """Return a condition that checks if message role equals the given role.

    Args:
        role: Role to check for

    Returns:
        Condition function
    """

    def condition(message: Message) -> bool:
        return message.role == role

    return condition


def metadata_has_key(key: str) -> Condition:
    """Return a condition that checks if metadata contains a key.

    Args:
        key: Metadata key to check for

    Returns:
        Condition function
    """

    def condition(message: Message) -> bool:
        return key in message.metadata

    return condition


def metadata_equals(key: str, value) -> Condition:
    """Return a condition that checks if metadata key equals value.

    Args:
        key: Metadata key to check
        value: Expected value

    Returns:
        Condition function
    """

    def condition(message: Message) -> bool:
        return message.metadata.get(key) == value

    return condition


def and_conditions(*conditions: Condition) -> Condition:
    """Combine multiple conditions with AND logic.

    Args:
        *conditions: Conditions to combine

    Returns:
        Combined condition function
    """

    def condition(message: Message) -> bool:
        return all(cond(message) for cond in conditions)

    return condition


def or_conditions(*conditions: Condition) -> Condition:
    """Combine multiple conditions with OR logic.

    Args:
        *conditions: Conditions to combine

    Returns:
        Combined condition function
    """

    def condition(message: Message) -> bool:
        return any(cond(message) for cond in conditions)

    return condition


def not_condition(cond: Condition) -> Condition:
    """Negate a condition.

    Args:
        cond: Condition to negate

    Returns:
        Negated condition function
    """

    def condition(message: Message) -> bool:
        return not cond(message)

    return condition
