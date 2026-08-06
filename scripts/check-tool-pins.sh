#!/usr/bin/env bash
# Assert that the linter/formatter versions declared in different files agree.
#
# Why this exists (#793): the repo declared ruff in three places with three
# different answers — `ruff>=0.1.0` in pyproject.toml's dev extra (a floor, so in
# practice whatever uv resolved: 0.14.4), `rev: v0.9.1` in .pre-commit-config.yaml,
# and a bare `ruff` in scripts/test-local.sh, which resolved to whatever was on
# $PATH (a Homebrew 0.15.10 here). Those three linters disagreed by 28 findings,
# because six of the rules involved are preview-only in 0.14.4 and stable by 0.15.x.
#
# The visible symptom was that `./scripts/test-local.sh --lint` passed or failed
# depending on whose machine ran it. A gate whose verdict depends on the developer's
# environment is not a gate. Formatters are worse than linters here: two versions
# that disagree will fight over the same file forever, each "fixing" the other.
#
# This is deliberately NOT part of scripts/version.py, which owns the *product*
# version (#842). Tool pins are unrelated to what agenkit reports as its own version.
set -euo pipefail

cd "$(dirname "$0")/.."

fail=0

note() { printf '%s\n' "$1"; }

# ---------------------------------------------------------------------------
# ruff: pyproject.toml dev extra vs .pre-commit-config.yaml rev
# ---------------------------------------------------------------------------
# Both patterns must match exactly once. A pattern that silently stops matching
# would turn this check into a no-op that reports success — the vacuous-gate bug
# from #849, where `gofmt -s -l` with an empty file list read stdin and exited 0.
py_count=$(grep -c '"ruff==[0-9]' pyproject.toml || true)
pc_count=$(grep -cE '^\s*rev: v[0-9]' .pre-commit-config.yaml || true)

if [ "$py_count" -ne 1 ]; then
    note "❌ expected exactly 1 pinned \"ruff==X.Y.Z\" in pyproject.toml, found $py_count"
    note "   If the pin moved or became a range, fix this check — do not trust it."
    exit 1
fi

if [ "$pc_count" -lt 1 ]; then
    note "❌ found no 'rev: vX.Y.Z' lines in .pre-commit-config.yaml; fix this check"
    exit 1
fi

py_ruff=$(sed -n 's/.*"ruff==\([0-9][0-9.]*\)".*/\1/p' pyproject.toml | head -1)

# The rev belonging to the ruff-pre-commit repo specifically, not the first rev in
# the file (mypy and others have their own).
pc_ruff=$(awk '
    /ruff-pre-commit/ { inblock = 1; next }
    inblock && /rev:/ { sub(/^[[:space:]]*rev:[[:space:]]*v?/, ""); print; exit }
' .pre-commit-config.yaml)

if [ -z "$py_ruff" ] || [ -z "$pc_ruff" ]; then
    note "❌ could not extract a ruff version (pyproject='$py_ruff' pre-commit='$pc_ruff')"
    note "   The extraction is wrong; fix this check rather than trusting it."
    exit 1
fi

if [ "$py_ruff" != "$pc_ruff" ]; then
    note "❌ ruff pin mismatch:"
    note "     pyproject.toml [dev]        ruff==$py_ruff"
    note "     .pre-commit-config.yaml     rev: v$pc_ruff"
    note "   Two ruff versions will disagree on both lint rules and formatting."
    note "   Bump them together (#793)."
    fail=1
else
    note "✓ ruff pinned consistently at $py_ruff (pyproject.toml, .pre-commit-config.yaml)"
fi

# ---------------------------------------------------------------------------
# No bare `ruff` invocations: they resolve against $PATH, not the pin
# ---------------------------------------------------------------------------
# Matches ruff only where a command *starts*: a line beginning (optionally after a
# make `@` prefix, a `run:`/`- ` YAML lead-in, or a shell `&&`/`|`/`(`), never mid-
# sentence. Without that anchoring this flagged three false positives — a make help
# string ("## Format code (Python: ruff format...)") and two workflow `name:` fields
# — which would have made the check cry wolf on prose. A guard that always fires is
# a guard nobody reads.
#
# Allows `uv run ... ruff` and `uvx ruff@...`, and skips comment lines and YAML
# `name:` fields (which are prose, and legitimately mention ruff).
bare=$(grep -nE '^[^#]*(^|@|&&|\||\(|run:)[[:space:]]*ruff[[:space:]]+(check|format)' \
    Makefile scripts/test-local.sh .github/workflows/*.yml 2>/dev/null \
    | grep -v 'uv run' | grep -v 'uvx' | grep -vE '^\S+:[0-9]+:[[:space:]]*(-[[:space:]]*)?name:' || true)

if [ -n "$bare" ]; then
    note "❌ bare 'ruff' invocation(s) — these use \$PATH, not the pinned version:"
    printf '%s\n' "$bare" | sed 's/^/     /'
    note "   Use 'uv run --extra dev ruff ...' so local and CI cannot diverge (#793)."
    fail=1
else
    note "✓ no bare ruff invocations (all go through uv, so all use the pin)"
fi

exit "$fail"
