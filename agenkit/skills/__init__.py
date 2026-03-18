"""
Agent Skills module for agenkit.

Provides support for the Agent Skills specification — an open standard for
packaging reusable agent capabilities as discoverable, portable instruction
bundles (a directory with a SKILL.md file containing YAML frontmatter +
Markdown instructions).

Classes:
    AgentSkill: Represents a single loaded skill from a directory.
    SkillRegistry: Discovers and searches skills across filesystem paths.
    SkillEnabledAgent: Agent wrapper that injects relevant skill instructions.

Usage:
    >>> from pathlib import Path
    >>> from agenkit.skills import AgentSkill, SkillRegistry, SkillEnabledAgent
    >>>
    >>> skill = AgentSkill.from_directory(Path("skills/pdf-processing"))
    >>> print(skill.to_prompt())
    >>>
    >>> registry = SkillRegistry([Path("skills/")])
    >>> registry.discover_skills()
    >>> relevant = registry.find_relevant_skills("pdf document")
    >>>
    >>> enabled = SkillEnabledAgent(base_agent, registry)
    >>> response = await enabled.process(message)
"""

from agenkit.skills.agent import SkillEnabledAgent
from agenkit.skills.loader import AgentSkill, SkillRegistry

__all__ = ["AgentSkill", "SkillEnabledAgent", "SkillRegistry"]
