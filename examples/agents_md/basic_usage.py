"""
Basic AGENTS.md usage example.

Demonstrates parsing and validating AGENTS.md files.
"""

import asyncio
from pathlib import Path

from agenkit.agents_md import parse_agents_md, validate_agents_md
from agenkit.agents_md.types import SectionType


async def main():
    """Run basic AGENTS.md example."""
    print("=== AGENTS.md Basic Usage ===\n")

    # Parse AGENTS.md file
    agents_md_path = Path(__file__).parent / "AGENTS.md"
    print(f"Parsing: {agents_md_path}\n")

    doc = parse_agents_md(agents_md_path)
    print(f"Parsed document: {doc}")
    print(f"Found {len(doc.sections)} sections\n")

    # List all sections
    print("Sections:")
    for section in doc.sections:
        print(f"  - {section.heading} ({section.type.value})")
        print(f"    Content length: {len(section.content)} chars")
        print(f"    Level: h{section.level}, Line: {section.line_number}")
    print()

    # Get specific sections
    print("Setup Instructions:")
    setup = doc.get_section(SectionType.SETUP)
    if setup:
        print(f"{setup.content[:200]}...")
        print()

    print("Code Style Guidelines:")
    code_style = doc.get_section(SectionType.CODE_STYLE)
    if code_style:
        print(f"{code_style.content[:200]}...")
        print()

    # Validate document
    print("=== Validation ===\n")
    result = validate_agents_md(doc)
    print(result)
    print()

    if result.issues:
        print("Issues found:")
        for issue in result.issues:
            print(f"  {issue}")
        print()

    if result.recommendations:
        print("Recommendations:")
        for rec in result.recommendations:
            print(f"  - {rec}")
        print()

    # Convert to prompt context
    print("=== Prompt Context ===\n")
    context = doc.to_prompt_context()
    print(f"Context length: {len(context)} chars")
    print(f"Preview:\n{context[:300]}...\n")


if __name__ == "__main__":
    asyncio.run(main())
