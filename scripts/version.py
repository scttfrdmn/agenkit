#!/usr/bin/env python3
"""Single source of truth for the Agenkit version.

The version lives in the root ``VERSION`` file. Every language manifest and every
MCP wire constant is *derived* from it, and the git tag is a consequence of it
rather than its source.

Why a committed file and not ``git describe``: source distributions have no
``.git`` (an sdist install, a ``zig fetch`` tarball, a vendored C++ copy),
CI checkouts are shallow by default, and ``build.zig.zon`` is a static data
literal that cannot compute anything. A committed file is readable by a one-line
regex from all nine build systems and is present in every checkout and tarball.

Usage::

    scripts/version.py check          # exit 1 if any declaration disagrees
    scripts/version.py sync           # rewrite every declaration from VERSION
    scripts/version.py set 0.88.0     # write VERSION, then sync
    scripts/version.py get            # print the version

``check`` is what CI runs. See issue #842: before this existed, the version was
declared 17 ways spanning 0.10.0 (Python's ``__version__``) to v0.87.0 (the
newest tag) — a 77-minor-version gap that accumulated silently because
``release.sh`` rewrote exactly one of them and nothing ever compared them.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT / "VERSION"

SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


@dataclass(frozen=True)
class Declaration:
    """One place the version is written down.

    ``pattern`` must contain exactly one capturing group around the version
    itself, and must match exactly once in the file. Both properties are
    asserted at runtime: a pattern that silently stops matching would turn this
    guard into a no-op, which is the failure mode it exists to prevent.
    """

    path: str
    pattern: str
    label: str

    @property
    def full_path(self) -> Path:
        return ROOT / self.path

    def read(self) -> str:
        """Return the version currently declared in this file."""
        text = self.full_path.read_text(encoding="utf-8")
        matches = list(re.finditer(self.pattern, text, flags=re.MULTILINE))
        if len(matches) != 1:
            raise SystemExit(
                f"{self.path}: pattern matched {len(matches)} times, expected "
                f"exactly 1 — the file's layout changed and this declaration's "
                f"pattern needs updating (pattern: {self.pattern!r})"
            )
        return matches[0].group(1)

    def write(self, version: str) -> bool:
        """Set this file's version. Returns True if the file changed."""
        text = self.full_path.read_text(encoding="utf-8")

        def replace(match: re.Match[str]) -> str:
            # Substitute only the captured group, preserving the surrounding
            # syntax — quoting and delimiters differ across nine build systems.
            start, end = match.span(1)
            return (
                match.group(0)[: start - match.start()]
                + version
                + match.group(0)[end - match.start() :]
            )

        new_text, count = re.subn(self.pattern, replace, text, flags=re.MULTILINE)
        if count != 1:
            raise SystemExit(f"{self.path}: pattern matched {count} times, expected exactly 1")
        if new_text == text:
            return False
        self.full_path.write_text(new_text, encoding="utf-8")
        return True


# Build manifests — what package managers publish.
MANIFESTS = [
    Declaration("pyproject.toml", r'^version = "([^"]+)"', "Python (PyPI)"),
    Declaration("agenkit-ts/package.json", r'^  "version": "([^"]+)"', "TypeScript (npm)"),
    Declaration("agenkit-rust/Cargo.toml", r'^version = "([^"]+)"', "Rust (crates.io)"),
    Declaration("agenkit-zig/build.zig.zon", r'^\s*\.version = "([^"]+)"', "Zig"),
    Declaration("agenkit-cpp/CMakeLists.txt", r"^project\(agenkit VERSION ([\d.]+)", "C++ (CMake)"),
    Declaration(
        "agenkit-cs/src/Agenkit/Agenkit.csproj", r"<Version>([^<]+)</Version>", "C# (NuGet)"
    ),
    Declaration("agenkit-java/pom.xml", r"^  <version>([^<]+)</version>", "Java (Maven)"),
    Declaration("agenkit-scala/build.sbt", r'^    version      := "([^"]+)"', "Scala (sbt)"),
]

# Lockfiles that record the core's own version because they depend on it by path.
# These are not free to omit: the Rust cross-language harness is built with
# `cargo build --locked`, which *fails* rather than self-heals when its lock is
# stale, so bumping agenkit-rust without updating this file breaks CI. Patched
# surgically rather than by `cargo update -p agenkit`, which also downgraded 30+
# unrelated transitive dependencies.
LOCKFILES = [
    Declaration(
        "tests/cross_language/harness_rust/Cargo.lock",
        r'\[\[package\]\]\nname = "agenkit"\nversion = "([^"]+)"',
        "Rust harness lock",
    ),
    Declaration(
        "agenkit-rust/Cargo.lock",
        r'\[\[package\]\]\nname = "agenkit"\nversion = "([^"]+)"',
        "Rust core lock",
    ),
    # uv.lock records the root project's own version, and uv self-heals it on the
    # next resolve rather than failing like `cargo --locked` does. That made it the
    # 20th declaration nobody propagated (#868), and the self-healing is precisely
    # what hid it: `release.sh` bumped pyproject.toml, committed, and only *then*
    # ran `make test`, whose `uv run pytest` rewrote this file after the commit. So
    # the v0.89.0 tag shipped `version = "0.87.0"` here, `make check-version`
    # truthfully reported "All 19 agree" because this was not one of the 19, and the
    # working tree was left dirty — which would trip the next release's own
    # uncommitted-changes preflight.
    #
    # Anchored on `source = { editable = "." }` so it can only ever match the
    # workspace root, never a hypothetical published `agenkit` pulled in as a dep.
    Declaration(
        "uv.lock",
        r'\[\[package\]\]\nname = "agenkit"\nversion = "([^"]+)"\nsource = \{ editable = "\." \}',
        "Python lock (uv)",
    ),
]

# MCP protocol clientInfo.version — transmitted to remote peers on handshake.
# These are not build metadata: a peer logging client versions for compatibility
# is told whatever is hardcoded here. Distinct from the MCP *spec* revision
# (#781); this is our product version.
MCP_CONSTANTS = [
    Declaration(
        "agenkit/protocols/mcp/client.py",
        r'^_CLIENT_INFO = \{"name": "agenkit", "version": "([^"]+)"\}',
        "MCP wire (Python)",
    ),
    Declaration(
        "agenkit-go/protocols/mcp/client.go",
        r'mcpClientVersion\s+= "([^"]+)"',
        "MCP wire (Go)",
    ),
    Declaration(
        "agenkit-ts/src/protocols/mcp/client.ts",
        r"^const CLIENT_VERSION = '([^']+)'",
        "MCP wire (TypeScript)",
    ),
    Declaration(
        "agenkit-zig/src/protocols/mcp.zig",
        r'^pub const CLIENT_VERSION = "([^"]+)"',
        "MCP wire (Zig)",
    ),
    Declaration(
        "agenkit-cpp/include/agenkit/protocols/mcp.hpp",
        r'^inline constexpr const char\* CLIENT_VERSION = "([^"]+)"',
        "MCP wire (C++)",
    ),
    Declaration(
        "agenkit-cs/src/Agenkit/Protocols/Mcp/McpTypes.cs",
        r'internal const string ClientVersion = "([^"]+)"',
        "MCP wire (C#)",
    ),
    Declaration(
        "agenkit-java/src/main/java/io/agenkit/protocols/mcp/McpConstants.java",
        r'static final String CLIENT_VERSION = "([^"]+)"',
        "MCP wire (Java)",
    ),
    Declaration(
        "agenkit-scala/src/main/scala/io/agenkit/protocols/mcp/McpTypes.scala",
        r'^val ClientVersion   = "([^"]+)"',
        "MCP wire (Scala)",
    ),
    # Rust inlines the version in a json! literal rather than naming a constant,
    # so the pattern is anchored on the surrounding clientInfo object.
    Declaration(
        "agenkit-rust/src/protocols/mcp/client.rs",
        r'"clientInfo": \{"name": "agenkit", "version": "([^"]+)"\}',
        "MCP wire (Rust)",
    ),
]

ALL_DECLARATIONS = MANIFESTS + MCP_CONSTANTS + LOCKFILES

# A floor on the list's own size. `cmd_check` prints "All N declarations agree", and
# nothing asserted N was the right N — so when uv.lock turned out to be a 20th
# declaration (#868), the guard reported complete success while missing one. The
# reassuring count was the tell. Deleting a Declaration is now a deliberate act that
# requires lowering this number, not an invisible narrowing of the guard.
#
# This does not catch a *new* manifest nobody adds here; nothing short of enumerating
# the filesystem can, and every non-example manifest in the tree was checked by hand
# when this was written (the harnesses and @agenkit/wasm carry their own independent
# versions and are deliberately excluded). Raise it when you add one.
_EXPECTED_DECLARATIONS = 20
if len(ALL_DECLARATIONS) < _EXPECTED_DECLARATIONS:
    raise SystemExit(
        f"scripts/version.py tracks {len(ALL_DECLARATIONS)} declarations but expected at "
        f"least {_EXPECTED_DECLARATIONS}. A declaration was removed from the lists above; "
        "if that was deliberate, lower _EXPECTED_DECLARATIONS in the same commit and say "
        "why. Silently shrinking this list is how #868 happened."
    )


def read_version() -> str:
    """Read and validate the canonical version."""
    if not VERSION_FILE.exists():
        raise SystemExit(f"{VERSION_FILE} does not exist — it is the source of truth")
    version = VERSION_FILE.read_text(encoding="utf-8").strip()
    if not SEMVER.match(version):
        raise SystemExit(f"VERSION contains {version!r}, which is not a bare X.Y.Z (no 'v' prefix)")
    return version


def cmd_get() -> int:
    print(read_version())
    return 0


def cmd_check() -> int:
    expected = read_version()
    mismatches = []
    for decl in ALL_DECLARATIONS:
        actual = decl.read()
        if actual != expected:
            mismatches.append((decl, actual))

    if mismatches:
        print(f"VERSION declares {expected}, but {len(mismatches)} declaration(s) disagree:\n")
        width = max(len(d.label) for d, _ in mismatches)
        for decl, actual in mismatches:
            print(f"  {decl.label:<{width}}  {actual:<10}  {decl.path}")
        print("\nRun: scripts/version.py sync")
        return 1

    print(f"All {len(ALL_DECLARATIONS)} version declarations agree: {expected}")
    return 0


def cmd_sync() -> int:
    version = read_version()
    changed = [decl for decl in ALL_DECLARATIONS if decl.write(version)]
    for decl in changed:
        print(f"  updated {decl.path} -> {version}")
    print(
        f"{len(changed)} file(s) updated; {len(ALL_DECLARATIONS)} declaration(s) now at {version}"
    )
    return 0


def cmd_set(version: str) -> int:
    # Accept a leading 'v' at the CLI for convenience, but never store it: the
    # manifests all want a bare X.Y.Z, and only the git tag carries the prefix.
    version = version.removeprefix("v")
    if not SEMVER.match(version):
        raise SystemExit(f"{version!r} is not a valid X.Y.Z version")
    VERSION_FILE.write_text(f"{version}\n", encoding="utf-8")
    print(f"VERSION -> {version}")
    return cmd_sync()


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("get", help="print the canonical version")
    sub.add_parser("check", help="verify every declaration matches VERSION")
    sub.add_parser("sync", help="rewrite every declaration from VERSION")
    set_parser = sub.add_parser("set", help="write VERSION and sync")
    set_parser.add_argument("version", help="new version, X.Y.Z")

    args = parser.parse_args()
    if args.command == "get":
        return cmd_get()
    if args.command == "check":
        return cmd_check()
    if args.command == "sync":
        return cmd_sync()
    if args.command == "set":
        return cmd_set(args.version)
    return 1


if __name__ == "__main__":
    sys.exit(main())
