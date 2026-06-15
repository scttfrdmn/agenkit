"""Tests for SkillEnabledAgent."""

from pathlib import Path

import pytest

from agenkit.interfaces import Agent, Message
from agenkit.skills.agent import SkillEnabledAgent
from agenkit.skills.loader import SkillRegistry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_skill_dir(
    tmp_path: Path, name: str, description: str, body: str = "Instructions here."
) -> Path:
    skill_dir = tmp_path / name
    skill_dir.mkdir()
    content = "---\n" f"name: {name}\n" f"description: {description}\n" "---\n" f"{body}"
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
    return skill_dir


class EchoAgent(Agent):
    """Agent that echoes its input content back."""

    @property
    def name(self) -> str:
        return "echo"

    async def process(self, message: Message) -> Message:
        return Message(role="agent", content=message.content, metadata=dict(message.metadata))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_skill_agent_augments_message(tmp_path: Path) -> None:
    make_skill_dir(tmp_path, "pdf-processing", "Extract text from PDF documents.")
    registry = SkillRegistry([tmp_path])
    agent = SkillEnabledAgent(EchoAgent(), registry, auto_discover=True)

    msg = Message(role="user", content="How do I parse pdf files?")
    response = await agent.process(msg)

    assert "<available_skills>" in str(response.content)
    assert "pdf-processing" in str(response.content)


@pytest.mark.asyncio
async def test_skill_agent_no_skills_passthrough(tmp_path: Path) -> None:
    make_skill_dir(tmp_path, "email-compose", "Compose professional emails.")
    registry = SkillRegistry([tmp_path])
    agent = SkillEnabledAgent(EchoAgent(), registry, auto_discover=True)

    msg = Message(role="user", content="tell me a joke")
    response = await agent.process(msg)

    assert "<available_skills>" not in str(response.content)
    assert str(response.content) == "tell me a joke"


@pytest.mark.asyncio
async def test_skill_agent_active_skills_metadata(tmp_path: Path) -> None:
    make_skill_dir(tmp_path, "csv-tools", "Handle and transform CSV spreadsheets.")
    registry = SkillRegistry([tmp_path])
    agent = SkillEnabledAgent(EchoAgent(), registry, auto_discover=True)

    msg = Message(role="user", content="parse this csv spreadsheet data")
    response = await agent.process(msg)

    assert "active_skills" in response.metadata
    assert "csv-tools" in response.metadata["active_skills"]


def test_skill_agent_capabilities(tmp_path: Path) -> None:
    registry = SkillRegistry([tmp_path])
    agent = SkillEnabledAgent(EchoAgent(), registry, auto_discover=False)

    caps = agent.capabilities
    assert "skill_injection" in caps


def test_skill_agent_name_delegates(tmp_path: Path) -> None:
    registry = SkillRegistry([tmp_path])
    agent = SkillEnabledAgent(EchoAgent(), registry, auto_discover=False)
    assert agent.name == "echo"
