"""Tripwire, not a placeholder, for Tool conformance.

Tool conformance is deferred pending #762 (the Tool.execute() signature
split) -- and the plan behind this suite established that deferral isn't
merely "not enough time yet": a Tool-subclass conformance suite would not
have caught #762 in the first place, since every divergent execute()
spelling lives on a class that does NOT subclass the real Tool base
(react.py's local Tool Protocol, AgentTool, techniques/protocols/mcp/tools.py,
SimpleApprovalTool). Only 1 class in the entire codebase subclasses the
real Tool -- MCPToolAdapter, which needs a real MCPClient to instantiate.

Rather than ship an empty/placeholder Tool section (the kind of
looks-connected-but-isn't control this repo's own #892/#901/#849
postmortems were written about), this asserts the census is exactly the
one known subclass. It fires the day a second Tool subclass appears --
exactly when Tool conformance becomes both buildable and necessary.
"""

from __future__ import annotations

from .census import tool_subclasses


def test_tool_census_is_exactly_the_one_known_subclass():
    tools = tool_subclasses()
    assert set(tools) == {("MCPToolAdapter", "agenkit/protocols/mcp/tool_adapter.py")}, (
        f"A new Tool subclass appeared: {sorted(tools)}. Tool conformance "
        f"(deferred pending #762) should now be scoped and built -- see "
        f"tests/conformance/registry.py's module docstring."
    )
