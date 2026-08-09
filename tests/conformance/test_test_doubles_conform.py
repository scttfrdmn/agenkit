"""Guard against test doubles re-introducing the #904 method-vs-property bug.

``agenkit.interfaces.Agent`` declares ``name`` and ``capabilities`` as
``@property``. Several first-party pattern classes once overrode them as
plain methods instead (#904), and the bug went undetected for months because
the test doubles used alongside those classes -- most notably the
project's own shared ``tests/helpers/mock_llm.py::MockAgent`` -- matched the
bug's shape rather than the real contract, so no test ever called
``capabilities`` in the way real callers do.

This AST-walks every ``tests/**/*.py`` file (not just the ones fixed so far)
so a *new* test double can't reintroduce the same bug shape by copy-pasting
an old one.
"""

from __future__ import annotations

import ast
from pathlib import Path

_TESTS_ROOT = Path(__file__).resolve().parent.parent

# Method names whose contract is `@property` on agenkit.interfaces.Agent.
_PROPERTY_NAMES = frozenset({"name", "capabilities"})

# Files that intentionally define an unrelated `name`/`capabilities` that is
# not part of the Agent contract (e.g. a dataclass field access helper, or a
# class that is not Agent-shaped at all). Empty today; add an entry with a
# short reason if a legitimate exception ever arises.
_EXCLUDED_FILES: frozenset[str] = frozenset()


def _iter_test_files() -> list[Path]:
    return sorted(p for p in _TESTS_ROOT.rglob("*.py") if p.name != "__init__.py")


def _find_violations(path: Path) -> list[str]:
    """Return violation descriptions for methods that should be properties.

    A "violation" is a zero/one-arg (``self``) method named ``name`` or
    ``capabilities`` defined directly on a class body without an
    ``@property`` decorator. Multi-arg methods (e.g. a helper that happens
    to be named ``name`` but takes extra parameters) are not part of this
    contract and are skipped.
    """
    try:
        tree = ast.parse(path.read_text())
    except SyntaxError:
        return []

    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for item in node.body:
            if not isinstance(item, ast.FunctionDef) or item.name not in _PROPERTY_NAMES:
                continue
            # Only the no-extra-argument shape (self [, ...defaults]) is the
            # Agent contract's shape; skip anything with required extra args.
            if len(item.args.args) > 1 or item.args.vararg or item.args.kwarg:
                continue
            decorator_names = {d.id for d in item.decorator_list if isinstance(d, ast.Name)} | {
                d.attr for d in item.decorator_list if isinstance(d, ast.Attribute)
            }
            if "property" in decorator_names:
                continue
            if {"abstractmethod", "overload"} & decorator_names:
                # Abstract/overload declarations are contract declarations,
                # not the runtime shape under test here.
                continue
            violations.append(
                f"{path.relative_to(_TESTS_ROOT.parent)}:{item.lineno}: "
                f"class {node.name}.{item.name} is a plain method, not a "
                f"@property -- matches the #904 bug shape"
            )
    return violations


def test_no_test_double_reintroduces_name_or_capabilities_as_a_method():
    all_violations: list[str] = []
    for path in _iter_test_files():
        if path.name in _EXCLUDED_FILES:
            continue
        all_violations.extend(_find_violations(path))

    assert not all_violations, (
        "Found test double(s) defining name/capabilities as a plain method "
        "instead of @property -- this is the exact shape of #904, which hid "
        "a real bug in SequentialAgent behind a matching mock for months:\n"
        + "\n".join(all_violations)
    )
