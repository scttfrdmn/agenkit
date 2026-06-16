"""
Agent Skill loader and registry.

Implements the Agent Skills specification: each skill is a directory containing
a SKILL.md file with YAML frontmatter (name, description, optional license and
metadata) followed by Markdown instructions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class AgentSkill:
    """
    Represents a single agent skill loaded from a directory.

    A skill directory must contain a SKILL.md file structured as:
        ---
        name: skill-name
        description: What this skill does.
        license: Apache-2.0  # optional
        metadata:            # optional
          key: value
        ---
        # Skill Title
        Markdown instructions here.
    """

    name: str
    description: str
    instructions: str
    license: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    skill_dir: Path | None = None

    @classmethod
    def from_directory(cls, skill_dir: Path) -> AgentSkill:
        """
        Load a skill from a directory containing a SKILL.md file.

        Args:
            skill_dir: Path to the skill directory.

        Returns:
            AgentSkill instance.

        Raises:
            ValueError: If the directory lacks SKILL.md, has invalid frontmatter,
                        or is missing required fields (name, description).
        """
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            raise ValueError(f"No SKILL.md found in {skill_dir}")

        raw = skill_file.read_text(encoding="utf-8")

        # Split on "---" delimiters. File must start with "---".
        parts = raw.split("---", 2)
        if len(parts) < 3:
            raise ValueError(f"Invalid SKILL.md in {skill_dir}: missing frontmatter delimiters")

        frontmatter_text = parts[1].strip()
        instructions = parts[2].strip()

        try:
            fm = yaml.safe_load(frontmatter_text)
        except yaml.YAMLError as exc:
            raise ValueError(f"Invalid YAML frontmatter in {skill_dir}/SKILL.md: {exc}") from exc

        if not isinstance(fm, dict):
            raise ValueError(f"Invalid frontmatter in {skill_dir}/SKILL.md: expected YAML mapping")

        name = fm.get("name")
        if not name:
            raise ValueError(f"Missing required field 'name' in {skill_dir}/SKILL.md")

        description = fm.get("description")
        if not description:
            raise ValueError(f"Missing required field 'description' in {skill_dir}/SKILL.md")

        return cls(
            name=str(name),
            description=str(description),
            instructions=instructions,
            license=fm.get("license"),
            metadata=fm.get("metadata") or {},
            skill_dir=skill_dir,
        )

    def to_prompt(self) -> str:
        """
        Render the skill as a prompt block for injection into agent messages.

        Returns:
            Formatted string with skill name, description, and instructions.
        """
        return (
            f"# Skill: {self.name}\n\n"
            f"## Description\n{self.description}\n\n"
            f"## Instructions\n{self.instructions}\n"
        )


class SkillRegistry:
    """
    Discovers and searches agent skills across filesystem paths.

    Skills are discovered by walking search paths and loading any subdirectory
    that contains a SKILL.md file. Invalid skill directories are skipped with
    a warning.
    """

    def __init__(self, search_paths: list[Path]) -> None:
        self._search_paths = search_paths
        self._skills: dict[str, AgentSkill] = {}

    def discover_skills(self) -> None:
        """
        Walk each search path and load all valid skill directories.

        Skill directories without a SKILL.md or with invalid format are
        skipped and logged as warnings.
        """
        for search_path in self._search_paths:
            if not search_path.is_dir():
                continue
            for entry in search_path.iterdir():
                if not entry.is_dir():
                    continue
                if not (entry / "SKILL.md").exists():
                    continue
                try:
                    skill = AgentSkill.from_directory(entry)
                    self._skills[skill.name] = skill
                except ValueError as exc:
                    logger.warning("skipping skill directory %s: %s", entry, exc)

    def find_relevant_skills(self, query: str, max_results: int = 5) -> list[AgentSkill]:
        """
        Return skills most relevant to the given query string.

        Scoring:
          +10 if query (lowercased) appears in skill name (lowercased)
          +5  if query (lowercased) appears in skill description (lowercased)
          +N  for each word in query that also appears in description

        Only skills with score > 0 are returned, sorted descending.

        Args:
            query: Natural-language query to match against skills.
            max_results: Maximum number of skills to return.

        Returns:
            Ordered list of matching AgentSkill instances (best match first).
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())

        scored: list[tuple[int, AgentSkill]] = []
        for skill in self._skills.values():
            score = 0
            name_lower = skill.name.lower()
            desc_lower = skill.description.lower()

            if query_lower in name_lower:
                score += 10
            if query_lower in desc_lower:
                score += 5

            word_overlap = len(query_words & set(desc_lower.split()))
            score += word_overlap

            if score > 0:
                scored.append((score, skill))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [skill for _, skill in scored[:max_results]]

    def get_skill(self, name: str) -> AgentSkill | None:
        """Return the skill with the given name, or None if not found."""
        return self._skills.get(name)

    @property
    def skills(self) -> dict[str, AgentSkill]:
        """Read-only view of loaded skills keyed by name."""
        return dict(self._skills)
