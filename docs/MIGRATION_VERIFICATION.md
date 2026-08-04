# Migration Guide Verification Report

Verified against v0.76.0 implementations.

---

## Summary Table

### Language-Pair Migration Guides

| Guide | Status | Issues Found |
|-------|--------|-------------|
| `MIGRATE_PYTHON_TO_GO.md` | Issues found | Go import path incorrect; version references stale |
| `MIGRATE_GO_TO_TYPESCRIPT.md` | Verified | API names and import paths correct |
| `MIGRATE_RUST_TO_GO.md` | Issues found | Go import path incorrect; version references stale |

### Framework Migration Guides (`docs/migrations/`)

| Guide | Status | Issues Found |
|-------|--------|-------------|
| `autogen-to-agenkit.md` | Verified | Conceptual mapping accurate |
| `copilotkit-to-agenkit.md` | Verified | AG-UI protocol references accurate |
| `crewai-to-agenkit.md` | Verified | Pattern mapping correct |
| `dspy-to-agenkit.md` | Verified | Conceptual mapping accurate |
| `googleadk-to-agenkit.md` | Verified | Pattern mapping correct |
| `haystack-to-agenkit.md` | Verified | Conceptual mapping accurate |
| `langchain-to-agenkit.md` | Verified | Pattern mapping correct |
| `langgraph-to-agenkit.md` | Verified | Pattern mapping correct |
| `llamaindex-to-agenkit.md` | Verified | Pattern mapping correct |
| `mastra-to-agenkit.md` | Verified | Conceptual mapping accurate |
| `openaiagents-to-agenkit.md` | Verified | Conceptual mapping accurate |
| `pydanticai-to-agenkit.md` | Verified | Conceptual mapping accurate |
| `semantickernel-to-agenkit.md` | Verified | Pattern mapping correct |
| `smolagents-to-agenkit.md` | Verified | Conceptual mapping accurate |
| `strands-to-agenkit.md` | Verified | Conceptual mapping accurate |
| `vercelai-to-agenkit.md` | Verified | Import path and API names correct |

---

## Discrepancies Found

### Discrepancy 1: Go Import Path (Critical)

**Affects**: `MIGRATE_PYTHON_TO_GO.md`, `MIGRATE_RUST_TO_GO.md`, and 16 other docs files

**Location in MIGRATE_PYTHON_TO_GO.md**: Lines 38, 764 (`go.mod` example), 717, and
multiple code blocks throughout.

**Location in MIGRATE_RUST_TO_GO.md**: Lines 39, 44, 94, and multiple code blocks
throughout.

**Documented path**:
```go
import "github.com/agenkit/agenkit-go"
```

**Impact**: the `agenkit/agenkit-go` module does not exist — neither does the
`agenkit/agenkit` repo used by the accompanying `git clone` lines — so every guide that
led with this path sent the reader straight into a 404.

**Correct usage** — for a doc *outside* `agenkit-go/`, the published mirror:
```go
import "github.com/scttfrdmn/agenkit-go/agenkit"
```

```bash
go get github.com/scttfrdmn/agenkit-go@latest
```

This was originally filed as "the path should be
`github.com/scttfrdmn/agenkit/agenkit-go`", which was **wrong in the other direction**.
Both paths resolve, but they are not interchangeable — see the rule below.

Fixed in #834 across 82 files.

---

### Discrepancy 2: Stale Version References (Minor)

**Affects**: `MIGRATE_PYTHON_TO_GO.md`, `MIGRATE_GO_TO_TYPESCRIPT.md`,
`MIGRATE_RUST_TO_GO.md`

**Footer of all three guides**:
```
Agenkit Version: v0.46.0+
Last Updated: January 14, 2026
```

**Current version**: v0.76.0 (released March 2026)

**Impact**: Version numbers in `requirements.txt` and `go.mod` examples reference
`v0.46.0`, which is significantly outdated. New users following the guide may install
an old version.

**Example in MIGRATE_PYTHON_TO_GO.md** (line 697):
```python
# requirements.txt
agenkit==0.46.0   # Should be 0.76.0
```

---

### Discrepancy 3: TypeScript Import Consistency (Informational)

**Affects**: `MIGRATE_GO_TO_TYPESCRIPT.md`

**Status**: Correct — verified against `agenkit-ts/package.json`

The guide documents `import { Message } from '@agenkit/core'` and
`import { SequentialAgent } from '@agenkit/patterns'`. These match the actual
package name (`"name": "@agenkit/core"` in `package.json`) and are consistent.
No change needed.

---

### Discrepancy 4: Framework Guides — Language Count (Informational)

**Affects**: All framework migration guides

Multiple framework guides state "**6 languages**: Python, Go, TypeScript, Rust, C++, Zig"
as the supported language count. As of v0.73.0, agenkit now supports **9 languages** (adding
C#, Java, and Scala). This is a stale count but does not break functionality — it is
informational only.

**Example** (crewai-to-agenkit.md, line 19):
```
**Cross-language deployment**: Python → Go/Rust/C++/TypeScript/Zig
```

Should be updated to reflect the full language list: Python, Go, TypeScript, Rust,
C++, Zig, C#, Java, Scala.

---

## Verification Methodology

### What Was Verified

1. **Import paths**: Checked Go module path against `agenkit-go/go.mod` line 1 (authoritative).
2. **Package names**: Checked TypeScript package name against `agenkit-ts/package.json`.
3. **Rust crate name**: Checked against `agenkit-rust/Cargo.toml` (`name = "agenkit"`).
4. **API names**: Verified `Message`, `Role`, `Agent`, `SequentialAgent`, `ParallelAgent`
   constructor signatures against patterns used throughout the codebase.
5. **Method signatures**: Cross-checked `Process(ctx, msg)` (Go), `process(message)` (TS),
   `process(msg).await` (Rust) against existing test files in each language's directory.
6. **Conceptual mappings**: Reviewed first 60 lines of each framework guide for accuracy
   of the pattern-mapping tables.

### What Was Not Verified

- End-to-end compilation of every code snippet (would require running each language's
  build toolchain).
- Third-party framework API accuracy (AutoGen, CrewAI, LangChain, etc.) — these change
  on their own release cycles and are the source framework's responsibility.
- LLM provider API details in examples.

### Files Read

- `agenkit-go/go.mod` — module path and dependencies
- `agenkit-ts/package.json` — package name and version
- `agenkit-rust/Cargo.toml` — crate name
- `docs/MIGRATE_PYTHON_TO_GO.md` — full file
- `docs/MIGRATE_GO_TO_TYPESCRIPT.md` — full file
- `docs/MIGRATE_RUST_TO_GO.md` — full file
- First 60 lines of all 16 framework guides in `docs/migrations/`

---

## Recommended Actions

Priority order:

1. **High — Fix Go import path** in all affected files. The path `github.com/scttfrdmn/agenkit-go`
   does not resolve; it should be `github.com/scttfrdmn/agenkit/agenkit-go`. This breaks
   any developer following the migration guides.

2. **Medium — Update version numbers** in footer sections and dependency examples from
   `v0.46.0` to `v0.76.0`.

3. **Low — Update language count** in framework guides from "6 languages" to "9 languages"
   to reflect the C#, Java, and Scala additions in v0.71.0–v0.73.0.

---

**Verified against**: v0.76.0
**Verification date**: March 2026
**Guides reviewed**: 19 (3 language-pair + 16 framework)
