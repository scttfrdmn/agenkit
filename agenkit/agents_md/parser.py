"""
Parser for AGENTS.md files.

This module provides functions to parse AGENTS.md files from disk and extract
structured sections for use by AI agents.
"""

import re
from pathlib import Path

from .types import AgentsMdDocument, AgentsMdSection, SectionType


def parse_agents_md(path: str | Path) -> AgentsMdDocument:
    """
    Parse an AGENTS.md file into structured sections.

    Args:
        path: Path to AGENTS.md file

    Returns:
        Parsed document with sections

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file is empty or invalid

    Example:
        ```python
        doc = parse_agents_md("./AGENTS.md")
        setup = doc.get_section(SectionType.SETUP)
        print(setup.content)
        ```
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"AGENTS.md not found: {path}")

    content = path.read_text(encoding="utf-8")

    if not content.strip():
        raise ValueError(f"AGENTS.md is empty: {path}")

    sections = _parse_sections(content)

    # Extract metadata from first lines if present
    metadata = _extract_metadata(content)

    return AgentsMdDocument(
        path=path,
        sections=sections,
        raw_content=content,
        metadata=metadata,
    )


def find_agents_md(start_dir: str | Path) -> list[Path]:
    """
    Find all AGENTS.md files in directory hierarchy.

    Searches upward from start_dir to find AGENTS.md files.

    Args:
        start_dir: Directory to start search from

    Returns:
        List of AGENTS.md file paths (closest first)

    Example:
        ```python
        # Find AGENTS.md in current dir and parents
        files = find_agents_md(".")
        for f in files:
            doc = parse_agents_md(f)
        ```
    """
    start_dir = Path(start_dir).resolve()
    found = []

    current = start_dir
    while True:
        agents_md = current / "AGENTS.md"
        if agents_md.exists():
            found.append(agents_md)

        # Stop at filesystem root
        if current.parent == current:
            break

        current = current.parent

    return found


def find_agents_md_hierarchy(start_dir: str | Path) -> dict[Path, AgentsMdDocument]:
    """
    Find and parse all AGENTS.md files in hierarchy.

    Searches upward from start_dir and parses all found files.

    Args:
        start_dir: Directory to start search from

    Returns:
        Dictionary mapping directory paths to parsed documents

    Example:
        ```python
        hierarchy = find_agents_md_hierarchy("./src")
        # Returns: {
        #     Path("."): doc1,           # Root AGENTS.md
        #     Path("./src"): doc2,       # src/AGENTS.md
        # }
        ```
    """
    files = find_agents_md(start_dir)
    hierarchy = {}

    for path in files:
        try:
            doc = parse_agents_md(path)
            hierarchy[path.parent] = doc
        except (FileNotFoundError, ValueError) as e:
            # Skip files that can't be parsed
            print(f"Warning: Could not parse {path}: {e}")
            continue

    return hierarchy


def _parse_sections(content: str) -> list[AgentsMdSection]:
    """
    Parse markdown content into sections.

    Sections are delimited by markdown headings (##, ###, etc.).

    Args:
        content: Markdown content

    Returns:
        List of parsed sections
    """
    sections = []
    lines = content.split("\n")

    current_section: dict | None = None
    current_lines: list[str] = []

    for line_num, line in enumerate(lines, start=1):
        # Check if line is a heading
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)

        if heading_match:
            # Save previous section if exists
            if current_section is not None:
                sections.append(
                    AgentsMdSection(
                        type=SectionType.from_heading(current_section["heading"]),
                        heading=current_section["heading"],
                        content="\n".join(current_lines).strip(),
                        level=current_section["level"],
                        line_number=current_section["line_number"],
                    )
                )

            # Start new section
            level = len(heading_match.group(1))
            heading = heading_match.group(2).strip()

            current_section = {
                "heading": heading,
                "level": level,
                "line_number": line_num,
            }
            current_lines = []
        # Accumulate content for current section
        elif current_section is not None:
            current_lines.append(line)

    # Save final section
    if current_section is not None:
        sections.append(
            AgentsMdSection(
                type=SectionType.from_heading(current_section["heading"]),
                heading=current_section["heading"],
                content="\n".join(current_lines).strip(),
                level=current_section["level"],
                line_number=current_section["line_number"],
            )
        )

    return sections


def _extract_metadata(content: str) -> dict[str, str]:
    """
    Extract metadata from document.

    Looks for metadata in first lines (YAML front matter or title).

    Args:
        content: Document content

    Returns:
        Dictionary of metadata
    """
    metadata = {}
    lines = content.split("\n")

    # Check for YAML front matter
    if lines and lines[0].strip() == "---":
        for line in lines[1:]:
            if line.strip() == "---":
                break
            if ":" in line:
                key, value = line.split(":", 1)
                metadata[key.strip()] = value.strip()

    # Extract title from first heading
    for line in lines:
        if line.startswith("#"):
            title_match = re.match(r"^#+\s+(.+)$", line)
            if title_match:
                metadata.setdefault("title", title_match.group(1).strip())
                break

    return metadata
