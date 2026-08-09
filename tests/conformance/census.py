"""AST census of concrete Agent/Tool subclasses in agenkit/.

This is the guard half of the conformance suite's discovery model: an
explicit factory-lambda list in registry.py is the *executor* (the house
style already established by
tests/techniques/reasoning/test_temperature_plumbing.py), and this census is
what proves that list is complete. Import-based discovery
(``pkgutil.walk_packages``) was rejected -- it throws on 6 optional LLM
provider deps that may not be installed, pulls in ~20 out-of-scope
middleware/auth/routing decorators, and would still miss the 4
Protocol-implementing classes (``ClassifierAgent``/``PlannerAgent`` and
friends) that participated in the original #904 bug despite not subclassing
``Agent`` at all.

AST-walking needs no imports, so it can't fail on a missing optional
dependency, and it finds every subclass whether or not agenkit/__init__.py
or any package's ``__all__`` re-exports it.
"""

from __future__ import annotations

import ast
from pathlib import Path

_AGENKIT_ROOT = Path(__file__).resolve().parent.parent.parent / "agenkit"


def _direct_bases(node: ast.ClassDef) -> set[str]:
    names = set()
    for base in node.bases:
        if isinstance(base, ast.Name):
            names.add(base.id)
        elif isinstance(base, ast.Attribute):
            names.add(base.attr)
    return names


def _find_subclasses(root: Path, target_bases: set[str]) -> dict[tuple[str, str], set[str]]:
    """Return {(class_name, relative_file_path): direct_bases} for every
    class in the tree, keyed by (name, file) rather than name alone --
    SequentialAgent/ParallelAgent/FallbackAgent each exist as two distinct
    classes, one in patterns/ and one in composition/, and keying by name
    alone would silently collapse them into one entry.
    """
    all_bases: dict[str, set[str]] = {}
    declarations: dict[tuple[str, str], set[str]] = {}

    for path in sorted(root.rglob("*.py")):
        if path.name.startswith("_") or "test" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:
            continue
        rel_path = str(path.relative_to(root.parent))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                bases = _direct_bases(node)
                # Name-keyed lookup table for base-class resolution: two
                # same-named classes in this codebase never subclass each
                # other, so a name collision here doesn't create a false
                # inheritance edge in the walk below.
                all_bases.setdefault(node.name, set()).update(bases)
                declarations[(node.name, rel_path)] = bases

    resolved: dict[tuple[str, str], set[str]] = {}
    for (name, path), bases in declarations.items():
        seen = {name}
        frontier = set(bases)
        while frontier:
            base = frontier.pop()
            if base in target_bases:
                resolved[(name, path)] = bases
                break
            if base in seen:
                continue
            seen.add(base)
            frontier |= all_bases.get(base, set())

    return resolved


def agent_subclasses() -> dict[tuple[str, str], set[str]]:
    """{(class_name, relative_file_path): direct_bases} for every concrete
    Agent subclass.
    """
    return _find_subclasses(_AGENKIT_ROOT, {"Agent"})


def tool_subclasses() -> dict[tuple[str, str], set[str]]:
    """{(class_name, relative_file_path): direct_bases} for every concrete
    Tool subclass.
    """
    return _find_subclasses(_AGENKIT_ROOT, {"Tool"})
