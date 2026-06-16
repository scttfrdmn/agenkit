"""Tests for AgentSkill and SkillRegistry."""

from pathlib import Path

import pytest

from agenkit.skills.loader import AgentSkill, SkillRegistry

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def make_skill_dir(
    tmp_path: Path, name: str, description: str, body: str = "Instructions here."
) -> Path:
    """Create a minimal valid skill directory inside tmp_path."""
    skill_dir = tmp_path / name
    skill_dir.mkdir()
    content = f"---\nname: {name}\ndescription: {description}\n---\n{body}"
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
    return skill_dir


# ---------------------------------------------------------------------------
# AgentSkill.from_directory
# ---------------------------------------------------------------------------


def test_load_skill_valid(tmp_path: Path) -> None:
    skill_dir = make_skill_dir(
        tmp_path, "pdf-processing", "Extract text from PDFs.", "# PDF\nDo stuff."
    )
    skill = AgentSkill.from_directory(skill_dir)

    assert skill.name == "pdf-processing"
    assert skill.description == "Extract text from PDFs."
    assert "Do stuff." in skill.instructions
    assert skill.skill_dir == skill_dir


def test_load_skill_with_license_and_metadata(tmp_path: Path) -> None:
    skill_dir = tmp_path / "advanced"
    skill_dir.mkdir()
    content = (
        "---\n"
        "name: advanced\n"
        "description: Advanced skill.\n"
        "license: Apache-2.0\n"
        "metadata:\n"
        "  version: '1.0'\n"
        "---\n"
        "Advanced instructions."
    )
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
    skill = AgentSkill.from_directory(skill_dir)

    assert skill.license == "Apache-2.0"
    assert skill.metadata == {"version": "1.0"}


def test_load_skill_missing_skill_md(tmp_path: Path) -> None:
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    with pytest.raises(ValueError, match=r"No SKILL\.md found"):
        AgentSkill.from_directory(empty_dir)


def test_load_skill_invalid_frontmatter(tmp_path: Path) -> None:
    skill_dir = tmp_path / "bad"
    skill_dir.mkdir()
    # Missing second "---" delimiter.
    (skill_dir / "SKILL.md").write_text("name: foo\ndescription: bar\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing frontmatter delimiters"):
        AgentSkill.from_directory(skill_dir)


def test_load_skill_missing_name(tmp_path: Path) -> None:
    skill_dir = tmp_path / "noname"
    skill_dir.mkdir()
    content = "---\ndescription: A skill without a name.\n---\nInstructions."
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
    with pytest.raises(ValueError, match="Missing required field 'name'"):
        AgentSkill.from_directory(skill_dir)


def test_load_skill_missing_description(tmp_path: Path) -> None:
    skill_dir = tmp_path / "nodesc"
    skill_dir.mkdir()
    content = "---\nname: nodesc\n---\nInstructions."
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
    with pytest.raises(ValueError, match="Missing required field 'description'"):
        AgentSkill.from_directory(skill_dir)


def test_skill_to_prompt(tmp_path: Path) -> None:
    skill_dir = make_skill_dir(tmp_path, "csv-tools", "Handle CSV files.", "Parse and write CSV.")
    skill = AgentSkill.from_directory(skill_dir)
    prompt = skill.to_prompt()

    assert "# Skill: csv-tools" in prompt
    assert "## Description" in prompt
    assert "Handle CSV files." in prompt
    assert "## Instructions" in prompt
    assert "Parse and write CSV." in prompt


# ---------------------------------------------------------------------------
# SkillRegistry
# ---------------------------------------------------------------------------


def test_registry_discover_skips_non_dirs(tmp_path: Path) -> None:
    # A file (not directory) at the search path level must be ignored.
    (tmp_path / "not_a_dir.md").write_text("ignored", encoding="utf-8")
    registry = SkillRegistry([tmp_path])
    registry.discover_skills()
    assert len(registry.skills) == 0


def test_registry_discovers_valid_skills(tmp_path: Path) -> None:
    make_skill_dir(tmp_path, "skill-a", "Skill A description.")
    make_skill_dir(tmp_path, "skill-b", "Skill B description.")
    registry = SkillRegistry([tmp_path])
    registry.discover_skills()

    assert "skill-a" in registry.skills
    assert "skill-b" in registry.skills


def test_registry_find_relevant_name_match(tmp_path: Path) -> None:
    make_skill_dir(tmp_path, "pdf-processing", "Work with PDF documents.")
    make_skill_dir(tmp_path, "csv-tools", "Handle CSV spreadsheets.")
    registry = SkillRegistry([tmp_path])
    registry.discover_skills()

    results = registry.find_relevant_skills("pdf")
    assert len(results) >= 1
    assert results[0].name == "pdf-processing"


def test_registry_find_relevant_max_results(tmp_path: Path) -> None:
    for i in range(6):
        make_skill_dir(tmp_path, f"skill-{i}", f"A skill about document processing number {i}.")
    registry = SkillRegistry([tmp_path])
    registry.discover_skills()

    results = registry.find_relevant_skills("document", max_results=3)
    assert len(results) <= 3


def test_registry_get_skill(tmp_path: Path) -> None:
    make_skill_dir(tmp_path, "email-compose", "Compose professional emails.")
    registry = SkillRegistry([tmp_path])
    registry.discover_skills()

    skill = registry.get_skill("email-compose")
    assert skill is not None
    assert skill.name == "email-compose"

    missing = registry.get_skill("nonexistent")
    assert missing is None
