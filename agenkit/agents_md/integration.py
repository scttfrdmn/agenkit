"""
Integration middleware for AGENTS.md support.

This module provides middleware that automatically injects AGENTS.md context
into agent prompts.
"""

from pathlib import Path
from typing import Optional

from agenkit.interfaces import Agent, Message

from .parser import find_agents_md_hierarchy, parse_agents_md
from .types import AgentsMdDocument


class AgentsMdMiddleware(Agent):
    """
    Middleware that injects AGENTS.md context into agent prompts.

    This middleware automatically discovers AGENTS.md files in the project
    hierarchy and injects their content into the system prompt, giving the
    agent context about project conventions, setup, testing, etc.

    Example:
        ```python
        from agenkit import Agent, Message
        from agenkit.agents_md import AgentsMdMiddleware

        # Base agent
        base_agent = MyLLMAgent()

        # Wrap with AGENTS.md middleware
        agent = AgentsMdMiddleware(base_agent, project_root=".")

        # Agent now has context from ./AGENTS.md
        response = await agent.process(Message(
            role="user",
            content="Write a new function following our code style"
        ))
        ```

    Attributes:
        agent: The underlying agent to wrap
        project_root: Root directory to search for AGENTS.md files
        instructions: Cached parsed AGENTS.md documents
        cache_enabled: Whether to cache parsed documents (default: True)
    """

    def __init__(
        self,
        agent: Agent,
        project_root: str | Path = ".",
        cache_enabled: bool = True,
    ):
        """
        Initialize AGENTS.md middleware.

        Args:
            agent: Agent to wrap
            project_root: Root directory for AGENTS.md discovery
            cache_enabled: Whether to cache parsed documents
        """
        self.agent = agent
        self.project_root = Path(project_root).resolve()
        self.cache_enabled = cache_enabled
        self._instructions: Optional[dict[Path, AgentsMdDocument]] = None

    @property
    def name(self) -> str:
        """Agent name."""
        return f"{self.agent.name}-with-agents-md"

    @property
    def capabilities(self) -> list[str]:
        """Agent capabilities."""
        caps = list(self.agent.capabilities) if self.agent.capabilities else []
        caps.append("agents-md-context")
        return caps

    async def process(self, message: Message) -> Message:
        """
        Process message with AGENTS.md context injected.

        Args:
            message: Input message

        Returns:
            Response from underlying agent with context
        """
        # Load AGENTS.md instructions if not cached
        if self._instructions is None or not self.cache_enabled:
            self._instructions = self._load_instructions()

        # Inject context into message
        enhanced_message = self._inject_context(message)

        # Process with underlying agent
        return await self.agent.process(enhanced_message)

    def _load_instructions(self) -> dict[Path, AgentsMdDocument]:
        """
        Load AGENTS.md files from project hierarchy.

        Returns:
            Dictionary mapping directory paths to parsed documents
        """
        try:
            hierarchy = find_agents_md_hierarchy(self.project_root)
            return hierarchy
        except Exception as e:
            # If loading fails, return empty dict and continue without context
            print(f"Warning: Could not load AGENTS.md files: {e}")
            return {}

    def _inject_context(self, message: Message) -> Message:
        """
        Inject AGENTS.md context into message.

        Args:
            message: Original message

        Returns:
            Message with context injected
        """
        if not self._instructions:
            return message

        # Build context string from all AGENTS.md files
        context_parts = []

        for dir_path, doc in sorted(self._instructions.items()):
            # Format context from each AGENTS.md
            context = doc.to_prompt_context()
            if context:
                context_parts.append(context)

        if not context_parts:
            return message

        # Combine all context
        full_context = "\n\n".join(context_parts)

        # Inject into message based on role
        if message.role == "system":
            # Append to existing system message
            enhanced_content = f"{message.content}\n\n{full_context}"
        else:
            # Prepend to user message as context
            enhanced_content = f"{full_context}\n\n---\n\n{message.content}"

        # Create new message with enhanced content
        return Message(
            role=message.role,
            content=enhanced_content,
            metadata={
                **(message.metadata or {}),
                "agents_md_context": True,
                "agents_md_files": [str(p) for p in self._instructions.keys()],
            },
        )

    def clear_cache(self) -> None:
        """Clear cached AGENTS.md instructions."""
        self._instructions = None

    def reload(self) -> None:
        """Reload AGENTS.md files from disk."""
        self._instructions = self._load_instructions()


def load_agents_md_context(project_root: str | Path = ".") -> str:
    """
    Load AGENTS.md context as string for manual injection.

    Utility function to load AGENTS.md content without using middleware.

    Args:
        project_root: Root directory to search for AGENTS.md files

    Returns:
        Formatted context string

    Example:
        ```python
        context = load_agents_md_context(".")
        prompt = f"{context}\n\nUser: {user_message}"
        ```
    """
    hierarchy = find_agents_md_hierarchy(project_root)

    if not hierarchy:
        return ""

    context_parts = []
    for dir_path, doc in sorted(hierarchy.items()):
        context = doc.to_prompt_context()
        if context:
            context_parts.append(context)

    return "\n\n".join(context_parts)
