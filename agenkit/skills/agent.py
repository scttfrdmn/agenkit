"""
SkillEnabledAgent — wraps an Agent and injects relevant skill instructions.
"""

from __future__ import annotations

import dataclasses
from typing import Any

from agenkit.interfaces import Agent, IntrospectionResult, Message
from agenkit.skills.loader import SkillRegistry


class SkillEnabledAgent(Agent):
    """
    Agent wrapper that automatically injects relevant skill instructions.

    Before delegating to the wrapped agent, this wrapper queries the registry
    for skills relevant to the incoming message and prepends their instructions
    inside an ``<available_skills>`` block.  The response's metadata will
    contain ``active_skills`` listing the skill names that were injected.

    Args:
        agent: Base agent to delegate processing to.
        registry: SkillRegistry used to look up relevant skills.
        max_active_skills: Maximum number of skills to inject (default 3).
        auto_discover: Whether to call ``registry.discover_skills()`` at
            construction time (default True).
    """

    def __init__(
        self,
        agent: Agent,
        registry: SkillRegistry,
        max_active_skills: int = 3,
        auto_discover: bool = True,
    ) -> None:
        self._agent = agent
        self._registry = registry
        self._max_active_skills = max_active_skills
        if auto_discover:
            self._registry.discover_skills()

    @property
    def name(self) -> str:
        return self._agent.name

    @property
    def capabilities(self) -> list[str]:
        base = list(self._agent.capabilities)
        if "skill_injection" not in base:
            base.append("skill_injection")
        return base

    def introspect(self) -> IntrospectionResult:
        return self._agent.introspect()

    async def process(self, message: Message) -> Message:
        """
        Process a message, injecting relevant skill instructions first.

        Finds skills relevant to the message content, builds an
        ``<available_skills>`` block, and prepends it to the message content
        before passing to the wrapped agent.  The returned message's metadata
        will include ``active_skills``.
        """
        query = str(message.content) if message.content is not None else ""
        relevant = self._registry.find_relevant_skills(
            query, max_results=self._max_active_skills
        )

        if relevant:
            skill_blocks = "\n\n".join(skill.to_prompt() for skill in relevant)
            prefix = f"<available_skills>\n{skill_blocks}\n</available_skills>\n\n"
            augmented_content = prefix + query

            new_metadata: dict[str, Any] = dict(message.metadata)
            new_metadata["active_skills"] = [skill.name for skill in relevant]
            enhanced = dataclasses.replace(
                message, content=augmented_content, metadata=new_metadata
            )
        else:
            enhanced = message

        return await self._agent.process(enhanced)
