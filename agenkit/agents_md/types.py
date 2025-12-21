"""
Data structures for AGENTS.md documents.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class SectionType(str, Enum):
    """Standard AGENTS.md section types."""

    SETUP = "setup"
    CODE_STYLE = "code_style"
    TESTING = "testing"
    ARCHITECTURE = "architecture"
    PATTERNS = "patterns"
    DEPLOYMENT = "deployment"
    SECURITY = "security"
    CONTRIBUTING = "contributing"
    CUSTOM = "custom"

    @classmethod
    def from_heading(cls, heading: str) -> "SectionType":
        """
        Convert markdown heading to section type.

        Args:
            heading: Markdown heading text (e.g., "Setup", "Code Style")

        Returns:
            Corresponding SectionType, or CUSTOM if not recognized
        """
        normalized = heading.lower().strip()

        # Map common variations
        mappings = {
            "setup": cls.SETUP,
            "installation": cls.SETUP,
            "getting started": cls.SETUP,
            "code style": cls.CODE_STYLE,
            "style": cls.CODE_STYLE,
            "coding conventions": cls.CODE_STYLE,
            "testing": cls.TESTING,
            "tests": cls.TESTING,
            "test": cls.TESTING,
            "architecture": cls.ARCHITECTURE,
            "design": cls.ARCHITECTURE,
            "structure": cls.ARCHITECTURE,
            "patterns": cls.PATTERNS,
            "common patterns": cls.PATTERNS,
            "best practices": cls.PATTERNS,
            "deployment": cls.DEPLOYMENT,
            "deploy": cls.DEPLOYMENT,
            "security": cls.SECURITY,
            "contributing": cls.CONTRIBUTING,
            "contribution": cls.CONTRIBUTING,
        }

        return mappings.get(normalized, cls.CUSTOM)


@dataclass
class AgentsMdSection:
    """
    A section from an AGENTS.md file.

    Attributes:
        type: The type of section
        heading: The original markdown heading text
        content: The section content (markdown)
        level: Heading level (1-6)
        line_number: Line number where section starts
    """

    type: SectionType
    heading: str
    content: str
    level: int = 2
    line_number: int = 0

    def is_empty(self) -> bool:
        """Check if section has no content."""
        return not self.content.strip()

    def __str__(self) -> str:
        """String representation of section."""
        return f"{self.heading} ({len(self.content)} chars)"


@dataclass
class AgentsMdDocument:
    """
    Parsed AGENTS.md document.

    Attributes:
        path: Path to the AGENTS.md file
        sections: List of parsed sections
        raw_content: Original file content
        metadata: Optional metadata (e.g., title, description)
    """

    path: Path
    sections: list[AgentsMdSection] = field(default_factory=list)
    raw_content: str = ""
    metadata: dict[str, str] = field(default_factory=dict)

    def get_section(self, section_type: SectionType) -> AgentsMdSection | None:
        """
        Get first section of given type.

        Args:
            section_type: Type of section to find

        Returns:
            First matching section, or None if not found
        """
        for section in self.sections:
            if section.type == section_type:
                return section
        return None

    def get_sections(self, section_type: SectionType) -> list[AgentsMdSection]:
        """
        Get all sections of given type.

        Args:
            section_type: Type of sections to find

        Returns:
            List of matching sections
        """
        return [s for s in self.sections if s.type == section_type]

    def has_section(self, section_type: SectionType) -> bool:
        """Check if document has section of given type."""
        return any(s.type == section_type for s in self.sections)

    def to_prompt_context(self) -> str:
        """
        Convert document to prompt context string.

        Returns:
            Formatted string suitable for injecting into agent prompts
        """
        if not self.sections:
            return ""

        lines = [f"# Project Instructions (from {self.path.name})\n"]

        for section in self.sections:
            lines.append(f"## {section.heading}\n")
            lines.append(f"{section.content}\n")

        return "\n".join(lines)

    def __str__(self) -> str:
        """String representation of document."""
        return f"AgentsMdDocument({self.path}, {len(self.sections)} sections)"
