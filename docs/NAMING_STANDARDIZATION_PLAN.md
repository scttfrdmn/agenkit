# Pattern Naming Standardization Plan

Based on comprehensive audit of all 18 patterns across 6 languages.

## Executive Summary

**Current State:** Pattern naming is mostly consistent (95%+) but has 5 key inconsistencies
**Goal:** 100% naming consistency across all languages
**Breaking Changes:** Minimal - affects only 3 patterns in specific languages
**Timeline:** 1-2 weeks for implementation and testing

---

## Audit Findings

### ✅ What's Already Consistent (95%+)

1. **File naming**: snake_case in Python, Go, Rust, C++, Zig (TypeScript uses kebab-case)
2. **Class naming**: PascalCase with `*Agent` suffix across 15/18 patterns
3. **Factory functions**: Language-specific conventions (New* in Go, ::new() in Rust, etc.)
4. **Export names**: Consistent class names across languages

### ❌ Inconsistencies Found (5 issues)

| Issue | Affects | Languages | Severity |
|-------|---------|-----------|----------|
| 1. TypeScript kebab-case files | 3 patterns | TypeScript | Low |
| 2. Zig `*Pattern` suffix | 3 patterns | Zig | Medium |
| 3. Memory file naming | 1 pattern | Zig | Low |
| 4. Python orchestration duality | 3 patterns | Python | High |
| 5. Class suffix consistency | All patterns | All | Low |

---

## Issue 1: TypeScript File Naming (Low Priority)

### Current State
TypeScript uses kebab-case for multi-word patterns:
- `agents-as-tools.ts`
- `human-in-loop.ts`
- `reasoning-with-tools.ts`

All other patterns use kebab-case already (e.g., `sequential.ts`, `parallel.ts`).

### Proposed Standard
**Keep kebab-case** - This is idiomatic TypeScript/JavaScript convention.

### Actions Required
✅ **No changes needed** - TypeScript is already following its ecosystem conventions.

---

## Issue 2: Zig Pattern Suffix (Medium Priority)

### Current State
Zig uses inconsistent suffixes:
- Orchestration patterns: `SequentialPattern`, `ParallelPattern`, `RouterPattern`
- All other patterns: `ReflectionAgent`, `ReActAgent`, etc.

### Proposed Standard
**Standardize on `*Agent` suffix** for consistency with other languages.

### Actions Required

**Zig Files to Update:**
1. `agenkit-zig/src/patterns/sequential.zig`
   - Rename: `SequentialPattern` → `SequentialAgent`

2. `agenkit-zig/src/patterns/parallel.zig`
   - Rename: `ParallelPattern` → `ParallelAgent`

3. `agenkit-zig/src/patterns/router.zig`
   - Rename: `RouterPattern` → `RouterAgent`

**Impact:**
- Zig examples will need updates
- Zig tests will need updates
- Documentation already uses canonical names

**Migration Support:**
```zig
// Provide deprecated aliases for 1 release
pub const SequentialPattern = SequentialAgent; // Deprecated
pub const ParallelPattern = ParallelAgent; // Deprecated
pub const RouterPattern = RouterAgent; // Deprecated
```

---

## Issue 3: Memory File Naming (Low Priority)

### Current State
- Python: `memory.py` (exports `MemoryHierarchy`)
- Zig: `memory_hierarchy.zig` (exports `MemoryHierarchy`)
- Others: `memory.*`

### Proposed Standard
**Standardize on `memory.*`** - shorter, consistent with majority.

### Actions Required

**Zig:**
- Rename: `memory_hierarchy.zig` → `memory.zig`
- Update imports in any files that reference it

**Python:**
✅ Already correct

**Impact:** Minimal - internal file name change only

---

## Issue 4: Python Orchestration Duality (High Priority)

### Current State
Python has **two** implementations of orchestration patterns:

1. **`patterns/orchestration.py`:**
   - Exports: `SequentialPattern`, `ParallelPattern`, `RouterPattern`
   - Used by: ? (need to check usage)

2. **`patterns/sequential.py`, `patterns/parallel.py`, `patterns/router.py`:**
   - Exports: `SequentialAgent`, `ParallelAgent`, `RouterAgent`
   - Used by: Examples, tests, documentation

### Proposed Standard
**Remove orchestration.py** - Keep only the `*Agent` versions in individual files.

### Rationale
1. Individual files are more discoverable
2. `*Agent` naming is consistent with other patterns
3. Reduces confusion about which to import
4. Other languages don't have orchestration.py

### Actions Required

1. **Check usage of orchestration.py:**
   ```bash
   grep -r "from.*orchestration import" agenkit/
   grep -r "import.*orchestration" agenkit/
   ```

2. **If used, add deprecation warnings:**
   ```python
   # patterns/orchestration.py
   import warnings
   from .sequential import SequentialAgent
   from .parallel import ParallelAgent
   from .router import RouterAgent

   warnings.warn(
       "orchestration.py is deprecated. "
       "Import from individual pattern modules instead: "
       "from agenkit.patterns import SequentialAgent, ParallelAgent, RouterAgent",
       DeprecationWarning,
       stacklevel=2
   )

   # Provide aliases for backward compatibility
   SequentialPattern = SequentialAgent
   ParallelPattern = ParallelAgent
   RouterPattern = RouterAgent
   ```

3. **Update all internal imports:**
   - Examples: Use `SequentialAgent` not `SequentialPattern`
   - Tests: Use `SequentialAgent` not `SequentialPattern`
   - Documentation: Already uses `*Agent` naming

4. **Schedule removal:**
   - v0.42.0: Add deprecation warnings
   - v0.43.0: Remove orchestration.py entirely

**Impact:**
- **Breaking change** if users import from orchestration.py
- Mitigation: Deprecation warnings + 1 release cycle transition period

---

## Issue 5: Class Suffix Consistency (Low Priority)

### Current State
Most patterns use `*Agent` suffix, but there are exceptions:
- `Task` (no suffix)
- `AgentTool` (for AgentsAsTools pattern)
- `MemoryHierarchy` (no suffix)
- `MultiAgentOrchestrator` (uses `Orchestrator` instead of `Agent`)

### Proposed Standard
**Accept naming variations** where they make semantic sense:
- `Task` → Keep (represents a task, not an agent)
- `AgentTool` → Keep (is a tool wrapper, not an agent itself)
- `MemoryHierarchy` → Keep (is a data structure, not an agent)
- `MultiAgentOrchestrator` → Keep (orchestrates agents, semantic clarity)

### Actions Required
✅ **No changes needed** - These names are semantically appropriate.

---

## Implementation Plan

### Phase 1: Documentation (Week 1)

1. **Update PATTERNS.md**
   - Ensure canonical names are PascalCase
   - Use language-specific examples where appropriate

2. **Update API.md**
   - Document correct class names for each language
   - Show proper import statements

3. **Update MIGRATION.md**
   - Already uses correct names in examples
   - Add note about orchestration.py deprecation

### Phase 2: Code Changes (Week 1-2)

**Priority 1: Python orchestration.py** (Breaking)
- [ ] Add deprecation warnings
- [ ] Update examples to use `*Agent` imports
- [ ] Update tests to use `*Agent` imports
- [ ] Document in CHANGELOG

**Priority 2: Zig Pattern suffix** (Breaking)
- [ ] Rename `*Pattern` → `*Agent` in sequential.zig, parallel.zig, router.zig
- [ ] Add deprecated aliases
- [ ] Update Zig examples
- [ ] Update Zig tests
- [ ] Document in CHANGELOG

**Priority 3: Zig memory file** (Non-breaking)
- [ ] Rename `memory_hierarchy.zig` → `memory.zig`
- [ ] Update imports
- [ ] Test Zig build

### Phase 3: Testing (Week 2)

- [ ] Run all Python tests
- [ ] Run all Zig tests
- [ ] Build all examples in both languages
- [ ] Verify documentation examples

### Phase 4: Communication (Week 2)

- [ ] Update CHANGELOG with breaking changes
- [ ] Add migration guide for users
- [ ] Document deprecated imports
- [ ] Update release notes

---

## Breaking Changes Summary

### For Python Users

**Deprecated (will be removed in v0.43.0):**
```python
# ❌ Old (deprecated)
from agenkit.patterns.orchestration import SequentialPattern, ParallelPattern, RouterPattern

# ✅ New (use this)
from agenkit.patterns import SequentialAgent, ParallelAgent, RouterAgent
```

**Timeline:**
- v0.42.0: Deprecation warnings added
- v0.43.0: orchestration.py removed

### For Zig Users

**Renamed (aliases provided for transition):**
```zig
// ❌ Old (deprecated)
const sequential = @import("patterns/sequential.zig");
const seq = sequential.SequentialPattern.init(allocator, agents, name);

// ✅ New (use this)
const sequential = @import("patterns/sequential.zig");
const seq = sequential.SequentialAgent.init(allocator, agents, name);
```

**Timeline:**
- v0.42.0: Renamed with deprecated aliases
- v0.43.0: Remove deprecated aliases

---

## Success Criteria

- [ ] All 18 patterns use consistent naming within each language
- [ ] File names follow language-specific conventions
- [ ] Class names use `*Agent` suffix where semantically appropriate
- [ ] Documentation uses canonical PascalCase names
- [ ] Migration path documented for breaking changes
- [ ] All tests passing with new names
- [ ] Examples updated to use new names

---

## Non-Goals

1. **Changing factory function conventions** - Keep language-specific idioms (New* in Go, ::new() in Rust, etc.)
2. **Forcing *Agent suffix everywhere** - Accept semantic variations (Task, MemoryHierarchy, etc.)
3. **Changing file extensions** - Keep .py, .go, .rs, .cpp, .ts, .zig
4. **Renaming working, semantically clear names** - Only fix true inconsistencies

---

## Rollback Plan

If issues arise:
1. Revert commits from standardization PR
2. Keep orchestration.py (remove deprecation warnings)
3. Keep Zig `*Pattern` naming
4. Document decision to maintain status quo

---

## Next Steps

1. Review this plan with team
2. Get approval for breaking changes
3. Create implementation PR
4. Execute Phase 1 (documentation)
5. Execute Phase 2 (code changes)
6. Execute Phase 3 (testing)
7. Execute Phase 4 (communication)

---

## Appendix: Full Naming Matrix

See audit report from Explore agent (agent ID: a22c73e) for complete pattern-by-pattern breakdown across all languages.
