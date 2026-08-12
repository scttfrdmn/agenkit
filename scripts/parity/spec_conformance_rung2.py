#!/usr/bin/env python3
"""Rung 2 of #909/#924's spec-conformance work: constructor-parameter
conformance against ``specs/patterns/*.yaml``.

Rung 1 (``spec_conformance.py``) answers "does a source file implementing
pattern X exist per language?" This module goes one level deeper, for the
subset of (pattern, language) pairs where rung 1 says "yes": does that
language's actual constructor (or its config object, for the languages
that use the config-object convention) take the same parameters that
``interface.constructor.parameters`` in the spec declares?

Design decisions (see #924):

* **Report-only, non-gating.** This deliberately does not fail a build.
  #924's own design doc calls out that even a careful spec-fixing pass
  (done immediately before this script was written) is expected to leave
  real mismatches in *some* non-Python languages, and a full
  language-by-language audit is future work, not this change. Nothing in
  ``main()`` returns non-zero because of what the comparison finds.

* **Python is the audited baseline; the other 8 languages are
  best-effort.** #924 explicitly scoped the spec-fixing pass to "Python
  vs spec", not "all 9 languages' constructors agree with each other".
  The extraction for Go/TypeScript/Rust/C++/Zig/C#/Java/Scala below is
  regex-based (this repo has no multi-language AST tooling), so absence
  of a reported mismatch in those languages is weaker evidence than
  Python's -- it may also mean the regex didn't find the construct, which
  is surfaced explicitly as ``"extraction": "not_found"`` rather than
  silently treated as a pass.

* **Naming-convention normalization.** Python's ``max_iterations``, Go's
  ``MaxIterations``, and TypeScript's ``maxIterations`` are the same
  parameter under different per-language casing conventions. Comparison
  strips underscores/hyphens and lowercases before comparing, so casing
  differences alone never produce a reported mismatch.

* **Config-object aware.** Most languages here converged on a
  config-object constructor convention (``ReActConfig``, ``TaskConfig``,
  ...) rather than long positional parameter lists. Extraction prefers a
  matching ``*Config`` struct/interface/dataclass's fields over a bare
  constructor's parameter list, per language, since the config object is
  what ``specs/patterns/*.yaml`` is describing.

Usage::

    scripts/parity/spec_conformance_rung2.py            # write spec-conformance-rung2.json
    scripts/parity/spec_conformance_rung2.py --check    # exit 1 if stale (still not a CI gate;
                                                          # nothing wires this flag into CI today)
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import yaml

# Reuse rung 1's language/path/spec-presence conventions rather than
# re-deriving them, so the two rungs never quietly drift apart on "where
# does language X's pattern code live."
sys.path.insert(0, str(Path(__file__).resolve().parent))
from spec_conformance import (  # noqa: E402
    LANGUAGES,
    SPECS_DIR,
    build_conformance,
)

ROOT = Path(__file__).resolve().parent.parent.parent

# spec filename stem -> ordered list of candidate PascalCase base names to
# search for in each language's source. For each base, the extractor
# tries several suffix variants (base, base+"Agent", base+"Config", ...)
# since the *Agent/*Config/no-suffix convention differs by language and,
# in a few cases (Task, AgentTool), by design within a single language.
PATTERN_CLASS_BASES: dict[str, list[str]] = {
    "agents_as_tools": ["AgentTool"],
    "autonomous": ["Autonomous"],
    "collaborative": ["Collaborative"],
    "conversational": ["Conversational", "ConversationalAgent"],
    "fallback": ["Fallback"],
    "human_in_loop": ["HumanInLoop"],
    "memory_hierarchy": ["MemoryHierarchy", "MemoryAugmented"],
    "multiagent": ["MultiAgent", "MultiAgentOrchestrator"],
    "orchestration": ["Orchestration"],
    "parallel": ["Parallel"],
    "planning": ["Planning"],
    "react": ["ReAct", "React"],
    "reasoning_with_tools": ["ReasoningWithTools"],
    "reflection": ["Reflection"],
    "router": ["Router"],
    "sequential": ["Sequential"],
    "supervisor": ["Supervisor"],
    "task": ["Task"],
}

_SUFFIXES = ("", "Agent", "Pattern")
_CONFIG_SUFFIXES = ("Config", "AgentConfig", "PatternConfig")


def _candidate_names(bases: list[str]) -> tuple[list[str], list[str]]:
    """Return (class_name_candidates, config_name_candidates) for a pattern."""
    classes = [f"{b}{s}" for b in bases for s in _SUFFIXES]
    configs = [f"{b}{s}" for b in bases for s in _CONFIG_SUFFIXES]
    return classes, configs


def normalize_param(name: str) -> str:
    """Fold snake_case/camelCase/PascalCase into a comparable canonical form.

    ``max_iterations``, ``maxIterations``, and ``MaxIterations`` all become
    ``maxiterations`` -- casing-convention differences across languages are
    not conformance bugs.
    """
    return re.sub(r"[_\-\s]", "", name).lower()


def _read_all(directory: Path, extension: str) -> str:
    if not directory.exists():
        return ""
    parts = []
    for p in sorted(directory.glob(f"*{extension}")):
        try:
            parts.append(p.read_text())
        except OSError:
            continue
    return "\n".join(parts)


def _source_text(lang_name: str, spec_stem: str) -> str:
    """Combined source text to search: a language's patterns_dir plus its
    composition_dir (some patterns, e.g. sequential/parallel/fallback,
    live in composition/ rather than patterns/ in several languages)."""
    lang = LANGUAGES[lang_name]
    text = _read_all(lang.patterns_dir, lang.extension)
    if lang.composition_dir is not None:
        text += "\n" + _read_all(lang.composition_dir, lang.extension)
    if lang_name == "zig":
        zig_composition = ROOT / "agenkit-zig" / "src" / "composition.zig"
        if zig_composition.exists():
            text += "\n" + zig_composition.read_text()
    return text


# --- Python extraction ------------------------------------------------------


def _extract_python_dataclass_fields(text: str, class_name: str) -> list[str] | None:
    m = re.search(
        rf"@dataclass\s*\nclass {re.escape(class_name)}\b[^:\n]*:\n", text
    )
    if not m:
        return None
    start = m.end()
    # crude end-of-class heuristic: next top-level class/def declaration
    nextm = re.search(r"\n(?:@\w+\n)?class \w|\ndef \w", text[start:])
    end = start + nextm.start() if nextm else len(text)
    body = text[start:end]
    body = re.sub(r'"""(?:.|\n)*?"""', "", body, count=1)
    fields = re.findall(r"^\s{4}(\w+)\s*:\s*[^\n=]+(?:=.*)?$", body, re.MULTILINE)
    # drop dunder/private-looking false positives and method-like lines
    return [f for f in fields if not f.startswith("_")] or None


def _extract_python_init_params(text: str, class_name: str) -> list[str] | None:
    m = re.search(rf"class {re.escape(class_name)}\b[^:\n]*:\n", text)
    if not m:
        return None
    start = m.end()
    nextm = re.search(r"\nclass \w", text[start:])
    end = start + nextm.start() if nextm else len(text)
    body = text[start:end]
    initm = re.search(r"def __init__\(\s*self\s*,?(.*?)\)\s*(?:->.*?)?:", body, re.DOTALL)
    if not initm:
        return None
    params_blob = initm.group(1)
    names = []
    for line in params_blob.split(","):
        line = line.strip()
        if not line or line.startswith("*"):
            continue
        pm = re.match(r"(\w+)\s*:", line)
        if pm:
            names.append(pm.group(1))
    return names or None


def extract_python(spec_stem: str) -> tuple[list[str] | None, str]:
    text = _source_text("python", spec_stem)
    classes, configs = _candidate_names(PATTERN_CLASS_BASES[spec_stem])
    # Prefer the Config dataclass (the "recommended" cross-language shape);
    # fall back to a bare __init__ signature for the classes that never
    # grew a config object (e.g. FallbackAgent, SequentialAgent).
    for cfg in configs:
        fields = _extract_python_dataclass_fields(text, cfg)
        if fields:
            return fields, f"dataclass:{cfg}"
    for cls in classes:
        params = _extract_python_init_params(text, cls)
        if params:
            return params, f"__init__:{cls}"
    return None, "not_found"


# --- Go extraction -----------------------------------------------------------


def _extract_go_struct_fields(text: str, struct_name: str) -> list[str] | None:
    m = re.search(rf"type {re.escape(struct_name)} struct \{{\n((?:.*\n)*?)\}}", text)
    if not m:
        return None
    body = m.group(1)
    fields = []
    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        fm = re.match(r"(\w+)\s+", line)
        if fm:
            fields.append(fm.group(1))
    return fields or None


def _extract_go_func_params(text: str, func_names: list[str]) -> list[str] | None:
    for fn in func_names:
        m = re.search(rf"func {re.escape(fn)}\(([^)]*)\)", text)
        if not m:
            continue
        params_blob = m.group(1)
        names = []
        for part in params_blob.split(","):
            part = part.strip()
            if not part:
                continue
            pm = re.match(r"(\w+)\s+", part)
            if pm and pm.group(1) not in ("ctx", "config"):
                names.append(pm.group(1))
        if names:
            return names
    return None


def extract_go(spec_stem: str) -> tuple[list[str] | None, str]:
    text = _source_text("go", spec_stem)
    classes, configs = _candidate_names(PATTERN_CLASS_BASES[spec_stem])
    for cfg in configs:
        fields = _extract_go_struct_fields(text, cfg)
        if fields:
            return fields, f"struct:{cfg}"
    ctor_names = [f"New{c}" for c in classes]
    params = _extract_go_func_params(text, ctor_names)
    if params:
        return params, "func:New*"
    return None, "not_found"


# --- TypeScript extraction ---------------------------------------------------


def _extract_ts_interface_fields(text: str, iface_name: str) -> list[str] | None:
    m = re.search(rf"export interface {re.escape(iface_name)} \{{\n((?:.*\n)*?)\}}", text)
    if not m:
        return None
    body = m.group(1)
    fields = re.findall(r"^\s*(\w+)\??\s*:", body, re.MULTILINE)
    return fields or None


def _extract_ts_constructor_params(text: str, class_names: list[str]) -> list[str] | None:
    for cls in class_names:
        m = re.search(rf"class {re.escape(cls)}\b", text)
        if not m:
            continue
        ctorm = re.search(r"constructor\(([^)]*)\)", text[m.end() :])
        if not ctorm:
            continue
        names = []
        for part in ctorm.group(1).split(","):
            part = part.strip()
            pm = re.match(r"(?:private |public |readonly )*(\w+)\??\s*:", part)
            if pm:
                names.append(pm.group(1))
        if names:
            return names
    return None


def extract_typescript(spec_stem: str) -> tuple[list[str] | None, str]:
    text = _source_text("typescript", spec_stem)
    classes, configs = _candidate_names(PATTERN_CLASS_BASES[spec_stem])
    for cfg in configs:
        fields = _extract_ts_interface_fields(text, cfg)
        if fields:
            return fields, f"interface:{cfg}"
    params = _extract_ts_constructor_params(text, classes)
    if params:
        return params, "constructor"
    return None, "not_found"


# --- Rust extraction ----------------------------------------------------------


def _extract_rust_struct_fields(text: str, struct_name: str) -> list[str] | None:
    m = re.search(rf"pub struct {re.escape(struct_name)} \{{\n((?:.*\n)*?)\}}", text)
    if not m:
        return None
    body = m.group(1)
    fields = re.findall(r"pub (\w+)\s*:", body)
    return fields or None


def _extract_rust_new_params(text: str, struct_names: list[str]) -> list[str] | None:
    for st in struct_names:
        m = re.search(rf"impl {re.escape(st)} \{{", text)
        if not m:
            continue
        newm = re.search(r"pub fn new\(([^)]*)\)", text[m.end() :])
        if not newm:
            continue
        names = []
        for part in newm.group(1).split(","):
            part = part.strip()
            if part in ("", "&self", "self"):
                continue
            pm = re.match(r"(\w+)\s*:", part)
            if pm:
                names.append(pm.group(1))
        if names:
            return names
    return None


def extract_rust(spec_stem: str) -> tuple[list[str] | None, str]:
    text = _source_text("rust", spec_stem)
    classes, configs = _candidate_names(PATTERN_CLASS_BASES[spec_stem])
    for cfg in configs:
        fields = _extract_rust_struct_fields(text, cfg)
        if fields:
            return fields, f"struct:{cfg}"
    params = _extract_rust_new_params(text, classes)
    if params:
        return params, "fn:new"
    return None, "not_found"


# --- Generic constructor-parameter-list extraction (C++, Java, Scala, C#) ---


def _extract_paren_ctor_params(
    text: str, class_names: list[str], ctor_pattern: str
) -> list[str] | None:
    """Shared helper for languages whose constructor is a parenthesized
    parameter list directly after the class name (C++, Java, Scala, C#)."""
    for cls in class_names:
        for m in re.finditer(ctor_pattern.format(cls=re.escape(cls)), text):
            blob = m.group(1)
            names = []
            for part in blob.split(","):
                part = part.strip()
                if not part:
                    continue
                # last identifier before optional default value is the param name
                part = part.split("=")[0].strip()
                tokens = re.findall(r"\w+", part)
                if tokens:
                    names.append(tokens[-1])
            if names:
                return names
    return None


def extract_cpp(spec_stem: str) -> tuple[list[str] | None, str]:
    text = _source_text("cpp", spec_stem)
    classes, _ = _candidate_names(PATTERN_CLASS_BASES[spec_stem])
    params = _extract_paren_ctor_params(text, classes, r"\b{cls}\(([^)]*)\)\s*[;{{]")
    if params:
        return params, "ctor"
    return None, "not_found"


def extract_java(spec_stem: str) -> tuple[list[str] | None, str]:
    text = _source_text("java", spec_stem)
    classes, _ = _candidate_names(PATTERN_CLASS_BASES[spec_stem])
    params = _extract_paren_ctor_params(
        text, classes, r"public {cls}\(([^)]*)\)\s*\{{"
    )
    if params:
        return params, "ctor"
    return None, "not_found"


def extract_scala(spec_stem: str) -> tuple[list[str] | None, str]:
    text = _source_text("scala", spec_stem)
    classes, _ = _candidate_names(PATTERN_CLASS_BASES[spec_stem])
    params = _extract_paren_ctor_params(text, classes, r"class {cls}\(\s*\n?((?:.|\n)*?)\)\s*(?:extends|:)")
    if params:
        return params, "primary-ctor"
    return None, "not_found"


def extract_csharp(spec_stem: str) -> tuple[list[str] | None, str]:
    text = _source_text("csharp", spec_stem)
    classes, configs = _candidate_names(PATTERN_CLASS_BASES[spec_stem])
    for cfg in configs:
        params = _extract_paren_ctor_params(text, [cfg], r"record {cls}\(((?:.|\n)*?)\)\s*;")
        if params:
            return params, f"record:{cfg}"
    params = _extract_paren_ctor_params(text, classes, r"public {cls}\(([^)]*)\)\s*\n?\s*\{{")
    if params:
        return params, "ctor"
    return None, "not_found"


def extract_zig(spec_stem: str) -> tuple[list[str] | None, str]:
    text = _source_text("zig", spec_stem)
    classes, configs = _candidate_names(PATTERN_CLASS_BASES[spec_stem])
    for cfg in configs:
        m = re.search(rf"pub const {re.escape(cfg)} = struct \{{\n((?:.*\n)*?)\}}", text)
        if m:
            fields = re.findall(r"^\s*(\w+)\s*:", m.group(1), re.MULTILINE)
            if fields:
                return fields, f"struct:{cfg}"
    for cls in classes:
        m = re.search(rf"pub const {re.escape(cls)} = struct \{{", text)
        if not m:
            continue
        initm = re.search(r"pub fn init\(([^)]*)\)", text[m.end() :])
        if not initm:
            continue
        names = []
        for part in initm.group(1).split(","):
            part = part.strip()
            pm = re.match(r"(\w+)\s*:", part)
            if pm and pm.group(1) != "allocator":
                names.append(pm.group(1))
        if names:
            return names, "fn:init"
    return None, "not_found"


EXTRACTORS = {
    "python": extract_python,
    "go": extract_go,
    "typescript": extract_typescript,
    "rust": extract_rust,
    "cpp": extract_cpp,
    "zig": extract_zig,
    "csharp": extract_csharp,
    "java": extract_java,
    "scala": extract_scala,
}


# --- Spec loading -------------------------------------------------------------


def _spec_declared_params(spec_stem: str) -> list[str] | None:
    spec_path = SPECS_DIR / f"{spec_stem}.yaml"
    data = yaml.safe_load(spec_path.read_text())
    iface = data.get("interface")
    if not iface:
        return None
    params = iface.get("constructor", {}).get("parameters", [])
    return [p["name"] for p in params] if params else None


@dataclass(frozen=True)
class ComparisonResult:
    declared: list[str]
    actual: list[str] | None
    extraction_method: str
    missing_in_code: list[str]
    extra_in_code: list[str]

    @property
    def status(self) -> str:
        if self.actual is None:
            return "not_found"
        if not self.missing_in_code and not self.extra_in_code:
            return "match"
        return "mismatch"


def compare_one(spec_stem: str, lang_name: str, declared: list[str]) -> ComparisonResult:
    actual, method = EXTRACTORS[lang_name](spec_stem)
    if actual is None:
        return ComparisonResult(declared, None, method, [], [])

    declared_norm = {normalize_param(p): p for p in declared}
    actual_norm = {normalize_param(p): p for p in actual}

    missing = [orig for norm, orig in declared_norm.items() if norm not in actual_norm]
    extra = [orig for norm, orig in actual_norm.items() if norm not in declared_norm]
    return ComparisonResult(declared, actual, method, missing, extra)


def build_rung2_report() -> dict:
    rung1 = build_conformance()
    presence = rung1["patterns"]

    results: dict[str, dict] = {}
    totals = {
        "match": 0,
        "mismatch": 0,
        "not_found": 0,
        "no_interface": 0,
        "not_present": 0,
    }

    for spec_path in sorted(SPECS_DIR.glob("*.yaml")):
        stem = spec_path.stem
        declared = _spec_declared_params(stem)
        results[stem] = {}

        if declared is None:
            # Stub spec with no interface section -- nothing to check here.
            for lang_name in LANGUAGES:
                results[stem][lang_name] = {"status": "no_interface"}
                totals["no_interface"] += 1
            continue

        for lang_name in LANGUAGES:
            if not presence.get(stem, {}).get(lang_name, False):
                # Rung 1 says this language doesn't implement the pattern
                # at all -- checking constructor params would be
                # meaningless (there's nothing to check against).
                results[stem][lang_name] = {"status": "not_present"}
                totals["not_present"] += 1
                continue

            cmp_result = compare_one(stem, lang_name, declared)
            entry = {
                "status": cmp_result.status,
                "extraction_method": cmp_result.extraction_method,
                "declared_params": cmp_result.declared,
                "actual_params": cmp_result.actual,
                "missing_in_code": cmp_result.missing_in_code,
                "extra_in_code": cmp_result.extra_in_code,
            }
            results[stem][lang_name] = entry
            totals[cmp_result.status] += 1

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "version": "1.0",
        "description": (
            "Rung 2 (#924): constructor-parameter conformance against "
            "specs/patterns/*.yaml, checked only for (pattern, language) "
            "pairs where rung 1 (spec-presence) found an implementation. "
            "REPORT-ONLY -- see module docstring; not wired to fail any "
            "build. Extraction beyond Python is regex-based best-effort; "
            "'not_found' means the checker's regex didn't locate the "
            "construct, not that the pattern is missing (rung 1 already "
            "answers that)."
        ),
        "results": results,
        "totals": totals,
    }


def write_report(report: dict, output_file: Path) -> None:
    with output_file.open("w") as f:
        json.dump(report, f, indent=2)
    print(f"Rung-2 spec conformance written to: {output_file}")


def _normalize_for_diff(report: dict) -> dict:
    normalized = dict(report)
    normalized["generated_at"] = "<normalized>"
    return normalized


def check_report_current(fresh: dict, output_file: Path) -> list[str]:
    if not output_file.exists():
        return [f"{output_file} does not exist -- run spec_conformance_rung2.py to create it"]
    committed = json.loads(output_file.read_text())
    if _normalize_for_diff(committed) != _normalize_for_diff(fresh):
        return [f"{output_file} is stale relative to a fresh regenerate"]
    return []


def print_summary(report: dict) -> None:
    totals = report["totals"]
    print("Rung-2 constructor-parameter conformance:")
    print("-" * 60)
    print(f"  match        {totals['match']}")
    print(f"  mismatch     {totals['mismatch']}")
    print(f"  not_found    {totals['not_found']}  (extractor couldn't locate the constructor)")
    print(f"  not_present  {totals['not_present']}  (rung 1: pattern not implemented in language)")
    print(f"  no_interface {totals['no_interface']}  (stub spec, nothing to check)")
    print()

    mismatches = []
    for stem, per_lang in report["results"].items():
        for lang, entry in per_lang.items():
            if entry.get("status") == "mismatch":
                mismatches.append((stem, lang, entry))

    if mismatches:
        print(f"Mismatches ({len(mismatches)}):")
        for stem, lang, entry in mismatches:
            print(f"  {stem} / {lang}:")
            if entry["missing_in_code"]:
                print(f"    declared in spec but not found in code: {entry['missing_in_code']}")
            if entry["extra_in_code"]:
                print(f"    found in code but not declared in spec: {entry['extra_in_code']}")
    else:
        print("No mismatches found.")


def main() -> int:
    check_only = "--check" in sys.argv
    report = build_rung2_report()
    output_file = ROOT / "spec-conformance-rung2.json"

    if check_only:
        errors = check_report_current(report, output_file)
        if errors:
            for e in errors:
                print(f"FAIL: {e}")
            print("\nRun: uv run python scripts/parity/spec_conformance_rung2.py")
            return 1
        print(f"{output_file} is current")
        return 0

    write_report(report, output_file)
    print_summary(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
