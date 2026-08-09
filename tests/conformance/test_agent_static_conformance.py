"""Layer A: static, class-level conformance for every Agent subclass.

Checked with ``inspect.getattr_static``/``inspect.signature`` against the
*class object*, never an instance -- so this layer needs no fixtures and has
no instantiability problem. It alone would have caught #904: ``name`` and
``capabilities`` are ``@property`` on the base ``agenkit.interfaces.Agent``;
a subclass overriding either as a plain method is exactly the bug shape that
survived undetected because no test asserted the *contract*, only that a
mock (which matched the bug) worked with its own pattern.

Includes the 4 Protocol-implementing classes that participated in #904 but
don't subclass ``Agent`` at all (``ClassifierAgent``/``SimpleClassifier``/
``LLMClassifier``, ``PlannerAgent``/``SimplePlanner``) by explicit name.
``typing.Protocol``'s ``runtime_checkable`` would not help discover these
automatically: ``isinstance`` against a ``Protocol`` checks member
*presence*, not property-vs-method shape, so it cannot catch this bug class
either -- there is no substitute for checking the shape explicitly.
"""

from __future__ import annotations

import ast
import inspect
import types

import pytest

from agenkit.interfaces import Agent
from agenkit.patterns.router import LLMClassifier, SimpleClassifier
from agenkit.patterns.supervisor import SimplePlanner

from .registry import ALL_AGENT_CLASSES


def _is_property(cls: type, attr: str) -> bool:
    return isinstance(inspect.getattr_static(cls, attr), property)


def _is_async_generator_function(func: object) -> bool:
    return inspect.isasyncgenfunction(func)


@pytest.mark.parametrize("cls", ALL_AGENT_CLASSES, ids=lambda c: c.__name__)
class TestAgentStaticConformance:
    def test_name_is_a_property(self, cls: type):
        assert _is_property(cls, "name"), (
            f"{cls.__name__}.name is not a @property -- this is the exact "
            f"#904 bug shape (SequentialAgent called agent.capabilities() on "
            f"a base that declares it as a property)"
        )

    def test_capabilities_is_a_property_if_overridden(self, cls: type):
        if "capabilities" not in vars(cls):
            return  # Inherits the base Agent.capabilities property; fine.
        assert _is_property(cls, "capabilities"), (
            f"{cls.__name__}.capabilities is not a @property -- this is the exact #904 bug shape"
        )

    def test_process_is_an_async_method(self, cls: type):
        process = vars(cls).get("process") or inspect.getattr_static(cls, "process")
        assert inspect.iscoroutinefunction(process), (
            f"{cls.__name__}.process must be an async method (async def process)"
        )
        sig = inspect.signature(process)
        params = list(sig.parameters)
        assert params[:2] == ["self", "message"] or params[0] == "self", (
            f"{cls.__name__}.process signature {sig} does not start with (self, message)"
        )

    def test_stream_is_an_async_generator_if_overridden(self, cls: type):
        if "stream" not in vars(cls):
            return  # Inherits the base Agent.stream, which raises NotImplementedError.
        stream = vars(cls)["stream"]
        assert _is_async_generator_function(stream), (
            f"{cls.__name__}.stream is overridden but is not an async "
            f"generator function (missing `yield`) -- callers iterating "
            f"`async for msg in agent.stream(...)` would get a coroutine, "
            f"not an async iterator"
        )

    def test_process_with_signature_if_overridden(self, cls: type):
        if "process_with" not in vars(cls):
            return  # Inherits the base Agent.process_with, which delegates to process.
        process_with = vars(cls)["process_with"]
        assert inspect.iscoroutinefunction(process_with), (
            f"{cls.__name__}.process_with must be async"
        )
        params = list(inspect.signature(process_with).parameters)
        assert params[:3] == ["self", "message", "options"], (
            f"{cls.__name__}.process_with signature does not match "
            f"(self, message, options): {params}"
        )


class TestProtocolParticipantsStaticConformance:
    """The 4 non-Agent-subclass classes that participated in #904.

    ``ClassifierAgent``/``PlannerAgent`` are ``typing.Protocol`` definitions,
    not concrete classes -- checked via AST since a Protocol's ``...`` body
    has no real property object to introspect at runtime. The concrete
    implementers (``SimpleClassifier``, ``LLMClassifier``, ``SimplePlanner``)
    are checked the normal way.
    """

    @pytest.mark.parametrize("cls", [SimpleClassifier, LLMClassifier, SimplePlanner])
    def test_name_is_a_property(self, cls: type):
        assert _is_property(cls, "name"), f"{cls.__name__}.name is not a @property"

    @pytest.mark.parametrize("cls", [SimpleClassifier, LLMClassifier, SimplePlanner])
    def test_capabilities_is_a_property(self, cls: type):
        assert _is_property(cls, "capabilities"), f"{cls.__name__}.capabilities is not a @property"

    @pytest.mark.parametrize(
        ("module_path", "protocol_name"),
        [
            ("agenkit/patterns/router.py", "ClassifierAgent"),
            ("agenkit/patterns/supervisor.py", "PlannerAgent"),
        ],
    )
    def test_protocol_declares_name_and_capabilities_as_properties(
        self, module_path: str, protocol_name: str
    ):
        """AST-check the Protocol body itself: a future edit that turns
        ``name``/``capabilities`` back into plain ``...`` methods (dropping
        ``@property``) would silently widen what satisfies the Protocol to
        include exactly the #904 bug shape, since Protocol conformance is
        structural.
        """
        from pathlib import Path

        root = Path(__file__).resolve().parent.parent.parent
        tree = ast.parse((root / module_path).read_text())

        protocol_node = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef) and node.name == protocol_name
        )
        for member_name in ("name", "capabilities"):
            member = next(
                item
                for item in protocol_node.body
                if isinstance(item, ast.FunctionDef) and item.name == member_name
            )
            decorator_names = {d.id for d in member.decorator_list if isinstance(d, ast.Name)}
            assert "property" in decorator_names, (
                f"{protocol_name}.{member_name} in {module_path} lost its "
                f"@property decorator -- Protocol conformance is structural, "
                f"so this would silently accept the #904 bug shape as valid"
            )


def test_agent_base_class_itself_declares_the_contract_as_properties():
    """A guard on the guard: if agenkit.interfaces.Agent itself ever stopped
    declaring name/capabilities as properties, every test above would become
    vacuous (checking subclasses against a contract that no longer exists).
    """
    assert isinstance(inspect.getattr_static(Agent, "name"), property)
    assert isinstance(inspect.getattr_static(Agent, "capabilities"), property)
    assert not isinstance(Agent.process, types.FunctionType) or inspect.iscoroutinefunction(
        Agent.process
    )
