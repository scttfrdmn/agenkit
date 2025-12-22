"""
Router Agent Pattern

Router pattern implements conditional agent selection based on message
classification. A classifier determines the intent/category, then routes
the request to an appropriate specialist agent.

Key concepts:
- Intent/category classification
- Conditional routing to specialists
- Single agent execution per request
- Dynamic agent selection based on input

Performance characteristics:
- Time: O(classification + selected agent)
- Memory: O(1) - only one agent executes
- Efficient single-path execution
"""

from dataclasses import dataclass
from typing import Protocol

from agenkit import Agent, Message


class ClassifierAgent(Protocol):
    """
    Protocol for agents responsible for determining routing decisions.

    The classifier analyzes the input message and returns a category/intent
    that determines which specialist agent should handle the request.
    """

    @property
    def name(self) -> str:
        """Return the agent's name."""
        ...

    def capabilities(self) -> list[str]:
        """Return the agent's capabilities."""
        ...

    async def process(self, message: Message) -> Message:
        """Process a message."""
        ...

    async def classify(self, message: Message) -> str:
        """
        Determine the category/intent for routing.

        Args:
            message: Message to classify

        Returns:
            Category string that matches a specialist key
        """
        ...


@dataclass
class RouterConfig:
    """
    Configuration for a RouterAgent.

    Attributes:
        classifier: Determines which agent to route to
        agents: Maps categories to specialist agents
        default_key: Specifies fallback agent when classification doesn't match (optional)
    """

    classifier: ClassifierAgent
    agents: dict[str, Agent]
    default_key: str | None = None


class RouterAgent(Agent):
    """
    Routes messages to appropriate agents based on classification.

    The router uses a classifier to determine message intent/category, then
    delegates to the corresponding specialist agent. This enables efficient
    conditional processing without executing all agents.

    Example use cases:
    - Customer service: route to billing, technical, account agents
    - Content moderation: route to spam, abuse, quality agents
    - Language routing: route to language-specific agents
    - Skill-based routing: route to domain expert agents
    - Intent-based chatbots: route to booking, info, support agents

    The router pattern is ideal when requests have clear categories and
    different agents handle different types of requests.

    Example:
        ```python
        from agenkit.patterns import RouterAgent, RouterConfig, SimpleClassifier

        # Create classifier and specialists
        classifier = SimpleClassifier(
            llm_agent,
            keywords={
                "billing": ["payment", "invoice", "charge"],
                "technical": ["error", "bug", "issue"],
                "account": ["password", "login", "profile"]
            }
        )

        config = RouterConfig(
            classifier=classifier,
            agents={
                "billing": billing_agent,
                "technical": tech_agent,
                "account": account_agent
            },
            default_key="technical"
        )

        router = RouterAgent(config)
        result = await router.process(
            Message(role="user", content="I have a payment question")
        )
        ```
    """

    def __init__(self, config: RouterConfig) -> None:
        """
        Create a new router agent.

        Args:
            config: Router configuration with classifier and agents

        Raises:
            ValueError: If config is None, classifier is None, agents is empty,
                       or default_key is invalid

        The classifier's classify method should return category strings that
        match keys in the agents map. If default_key is specified, requests with
        unmatched categories will be routed to that agent instead of failing.
        """
        if config is None:
            raise ValueError("config is required")
        if config.classifier is None:
            raise ValueError("classifier is required")
        if not config.agents:
            raise ValueError("at least one agent is required")

        # Validate default key if provided
        if config.default_key and config.default_key not in config.agents:
            raise ValueError(f"default key '{config.default_key}' not found in agents map")

        self._classifier = config.classifier
        self._agents = config.agents
        self._default_key = config.default_key

    @property
    def name(self) -> str:
        """Return the agent's identifier."""
        return "RouterAgent"

    def capabilities(self) -> list[str]:
        """Return the combined capabilities of all agents."""
        cap_set = set()

        # Add classifier capabilities
        cap_set.update(self._classifier.capabilities())

        # Add agent capabilities
        for agent in self._agents.values():
            cap_set.update(agent.capabilities())

        capabilities = list(cap_set)
        capabilities.extend(["router", "conditional", "classification"])

        return capabilities

    async def process(self, message: Message) -> Message:
        """
        Classify the message and route to appropriate agent.

        The process follows these steps:
        1. Classification: Determine message category/intent
        2. Route selection: Look up corresponding agent
        3. Execution: Delegate to selected agent

        If classification fails, an error is raised. If the classified category
        doesn't match any agent and no default is configured, an error is raised.

        The final message includes metadata about the routing decision.

        Args:
            message: Input message to classify and route

        Returns:
            Response from the selected specialist agent

        Raises:
            ValueError: If message is None
            RuntimeError: If classification fails or no agent found for category
        """
        if message is None:
            raise ValueError("message cannot be None")

        # Step 1: Classify the message
        try:
            category = await self._classifier.classify(message)
        except Exception as e:
            raise RuntimeError(f"classification failed: {e}") from e

        # Step 2: Select agent based on category
        agent = self._agents.get(category)
        if agent is None:
            # Try default agent if configured
            if self._default_key:
                agent = self._agents[self._default_key]
                category = self._default_key  # Update category to reflect actual routing
            else:
                available_categories = ", ".join(self._agents.keys())
                raise RuntimeError(
                    f"no agent found for category '{category}' (available: {available_categories})"
                )

        # Step 3: Execute selected agent
        try:
            result = await agent.process(message)
        except Exception as e:
            raise RuntimeError(f"agent '{agent.name}' (category: {category}) failed: {e}") from e

        # Add routing metadata
        if result.metadata is None:
            result.metadata = {}
        result.metadata["routed_category"] = category
        result.metadata["routed_agent"] = agent.name
        result.metadata["available_routes"] = len(self._agents)

        return result


class SimpleClassifier:
    """
    Basic classifier using keyword matching.

    This classifier uses simple string matching to determine categories.
    For production use, consider implementing a custom ClassifierAgent with
    ML-based classification or more sophisticated logic.

    Example:
        ```python
        from agenkit.patterns import SimpleClassifier

        classifier = SimpleClassifier(
            agent=llm_agent,
            keywords={
                "billing": ["payment", "invoice", "charge"],
                "technical": ["error", "bug", "issue"]
            }
        )
        ```
    """

    def __init__(self, agent: Agent, keywords: dict[str, list[str]]) -> None:
        """
        Create a keyword-based classifier.

        Args:
            agent: Fallback agent for complex classifications
            keywords: Map of categories to keyword lists
        """
        self._agent = agent
        self._keywords = keywords

    @property
    def name(self) -> str:
        """Return the classifier's identifier."""
        return "SimpleClassifier"

    def capabilities(self) -> list[str]:
        """Return the classifier's capabilities."""
        caps = self._agent.capabilities()
        return [*caps, "classification", "keyword-matching"]

    async def process(self, message: Message) -> Message:
        """Handle direct message processing (delegates to underlying agent)."""
        return await self._agent.process(message)

    async def classify(self, message: Message) -> str:
        """
        Determine category using keyword matching.

        Args:
            message: Message to classify

        Returns:
            Category with the most keyword matches

        Raises:
            ValueError: If message is None
            RuntimeError: If no keyword matches found
        """
        if message is None:
            raise ValueError("message cannot be None")

        content = message.content.lower()

        # Check each category's keywords
        max_matches = 0
        best_category = ""

        for category, keywords in self._keywords.items():
            matches = sum(1 for keyword in keywords if keyword.lower() in content)

            if matches > max_matches:
                max_matches = matches
                best_category = category

        if not best_category:
            raise RuntimeError("unable to classify message - no keyword matches found")

        return best_category


class LLMClassifier:
    """
    LLM-based classifier for intelligent categorization.

    This classifier prompts an LLM to determine the category. The LLM is given
    a list of valid categories and must respond with one of them.

    Example:
        ```python
        from agenkit.patterns import LLMClassifier

        classifier = LLMClassifier(
            agent=llm_agent,
            categories=["billing", "technical", "account"]
        )
        ```
    """

    def __init__(
        self,
        agent: Agent,
        categories: list[str],
        prompt: str | None = None,
    ) -> None:
        """
        Create an LLM-based classifier.

        Args:
            agent: LLM agent for classification
            categories: List of valid category names
            prompt: Optional custom prompt template
        """
        if not categories:
            categories = ["general"]

        self._agent = agent
        self._categories = categories

        if prompt is None:
            categories_str = ", ".join(categories)
            prompt = (
                f"Classify the following message into one of these categories: {categories_str}\n\n"
                "Reply with ONLY the category name, nothing else.\n\n"
                "Message: "
            )

        self._prompt = prompt

    @property
    def name(self) -> str:
        """Return the classifier's identifier."""
        return "LLMClassifier"

    def capabilities(self) -> list[str]:
        """Return the classifier's capabilities."""
        caps = self._agent.capabilities()
        return [*caps, "classification", "llm-classification"]

    async def process(self, message: Message) -> Message:
        """Handle direct message processing (delegates to underlying agent)."""
        return await self._agent.process(message)

    async def classify(self, message: Message) -> str:
        """
        Use LLM to determine category.

        Args:
            message: Message to classify

        Returns:
            Category from the valid categories list

        Raises:
            ValueError: If message is None
            RuntimeError: If LLM classification fails or returns invalid category
        """
        if message is None:
            raise ValueError("message cannot be None")

        # Build classification prompt
        classification_msg = Message(role="user", content=self._prompt + message.content)

        # Get LLM classification
        try:
            result = await self._agent.process(classification_msg)
        except Exception as e:
            raise RuntimeError(f"llm classification failed: {e}") from e

        category = result.content.strip()

        # Validate category is in allowed list
        for valid_cat in self._categories:
            if category.lower() == valid_cat.lower():
                return valid_cat

        categories_str = ", ".join(self._categories)
        raise RuntimeError(f"llm returned invalid category '{category}' (valid: {categories_str})")
