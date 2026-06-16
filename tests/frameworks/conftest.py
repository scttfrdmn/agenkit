"""Shared fixtures and path setup for framework compatibility tests."""

import sys
from pathlib import Path

import pytest

# Inject examples/frameworks/ into the module search path so tests can
# import minichain and minicrew without installing them as packages.
_FRAMEWORKS_DIR = str(Path(__file__).parent.parent.parent / "examples" / "frameworks")
if _FRAMEWORKS_DIR not in sys.path:
    sys.path.insert(0, _FRAMEWORKS_DIR)

# Patch agenkit.adapters.llm to expose OpenAILLM as a stub when openai package
# is not installed.  The minichain/minicrew example files import OpenAILLM at
# module level only to demonstrate the API; tests never actually call it.
import agenkit.adapters.llm as _llm_module

if not hasattr(_llm_module, "OpenAILLM"):
    # Create a minimal stub so the import in minichain.py / minicrew.py succeeds
    class _OpenAILLMStub:
        """Stub for OpenAILLM when the openai package is not installed."""

        def __init__(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
            pass

    _llm_module.OpenAILLM = _OpenAILLMStub  # type: ignore[attr-defined]

from tests.frameworks.fixtures.mock_providers import MockClassifier, MockLLM


@pytest.fixture
def mock_llm() -> MockLLM:
    """Single-response mock LLM."""
    return MockLLM(default_response="mock response")


@pytest.fixture
def mock_llm_multi() -> MockLLM:
    """Multi-response mock LLM cycling through a list of responses."""
    return MockLLM(
        responses=[
            "response one",
            "response two",
            "response three",
            "response four",
            "response five",
        ]
    )


@pytest.fixture
def mock_classifier() -> MockClassifier:
    """Keyword-based mock classifier with billing/tech/account routes."""
    return MockClassifier(
        rules={
            "billing": ["invoice", "payment", "charge"],
            "technical": ["error", "bug", "issue"],
            "account": ["password", "login", "profile"],
        },
        default_category="general",
    )
