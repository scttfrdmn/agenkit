"""
AGENTS.md support for Agenkit.

This module provides parsing, validation, and integration of AGENTS.md files,
a standard format for providing instructions to AI coding agents.

AGENTS.md is a hierarchical markdown format that allows you to document:
- Project setup and configuration
- Code style and conventions
- Testing procedures
- Architecture decisions
- Common patterns

Example:
    ```python
    from agenkit.agents_md import parse_agents_md, AgentsMdMiddleware

    # Parse AGENTS.md file
    doc = parse_agents_md("./AGENTS.md")
    print(doc.sections)

    # Use as middleware to inject instructions into agent prompts
    agent = MyAgent()
    agent_with_context = AgentsMdMiddleware(agent, project_root=".")
    ```

Components:
    - parser: Parse AGENTS.md files into structured data
    - validator: Validate AGENTS.md format and completeness
    - integration: Inject AGENTS.md context into agent prompts
    - types: Data structures for AGENTS.md documents
"""

from .integration import AgentsMdMiddleware
from .parser import find_agents_md, find_agents_md_hierarchy, parse_agents_md
from .types import AgentsMdDocument, AgentsMdSection, SectionType
from .validator import ValidationIssue, ValidationResult, validate_agents_md

__all__ = [
    # Types
    "AgentsMdDocument",
    # Integration
    "AgentsMdMiddleware",
    "AgentsMdSection",
    "SectionType",
    "ValidationIssue",
    "ValidationResult",
    "find_agents_md",
    "find_agents_md_hierarchy",
    # Parser
    "parse_agents_md",
    # Validator
    "validate_agents_md",
]
