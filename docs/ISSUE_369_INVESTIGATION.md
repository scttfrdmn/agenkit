# Issue #369 Investigation - Cross-Language Parity Status

**Date:** January 4, 2026
**Issue:** #369 - CRITICAL: Incomplete Go-only implementations breaking cross-language test parity

---

## Current Status

### 🔴 PARITY STILL BROKEN (Opposite Direction)

After the revert executed in commit 50793ac3, the cross-language parity issue **still exists**, but now in the **opposite direction**: Python has features that Go (and other languages) don't have.

---

## Parity Analysis Results

### Reasoning Techniques

| Technique | Python | Go | Status |
|-----------|--------|-----|--------|
| chain_of_thought | ✅ | ✅ | ✅ Parity |
| self_consistency | ✅ | ✅ | ✅ Parity |
| tree_of_thought | ✅ | ✅ | ✅ Parity |
| **graph_of_thought** | ✅ | ❌ | ❌ Python-only |
| **least_to_most** | ✅ | ❌ | ❌ Python-only |
| **plan_and_solve** | ✅ | ❌ | ❌ Python-only |

**Summary:** Python has 6 reasoning techniques, Go has 3
**Gap:** 3 Python-only techniques

---

### Compositions

| Module | Python | Go | Status |
|--------|--------|-----|--------|
| Entire module | ✅ (9 files) | ❌ | ❌ Python-only |

**Python Compositions (9):**
1. actor_critic_variation.py
2. context_optimization.py
3. exploration.py
4. goal_monitoring.py
5. learning_feedback.py
6. prioritization.py
7. rag.py
8. rag_with_citations.py
9. simple_human_approval.py

**Go Compositions:** None (directory doesn't exist)

**Gap:** 9 Python-only compositions

---

### Protocols

| Protocol | Python | Go | Status |
|----------|--------|-----|--------|
| A2A | ✅ (~10 files) | ❌ | ❌ Python-only |
| MCP | ✅ (~10 files) | ❌ | ❌ Python-only |

**Python Protocols:** 2 complete implementations (A2A + MCP, ~20 files total)
**Go Protocols:** None (directory doesn't exist)

**Gap:** 2 Python-only protocol implementations

---

## Total Parity Gap

**Python has 3 categories of features that Go (and likely other languages) don't have:**

1. **3 Advanced Reasoning Techniques**
   - graph_of_thought.py (~500 lines + reasoning_graph.py ~400 lines)
   - least_to_most.py (~300 lines)
   - plan_and_solve.py (~350 lines)
   - **Total:** ~1,550 lines

2. **9 Composition Patterns**
   - Various compositions (~80-150 lines each)
   - **Total:** ~900-1,200 lines

3. **2 Protocol Implementations**
   - A2A protocol (~1,000 lines across 10 files)
   - MCP protocol (~1,000 lines across 10 files)
   - **Total:** ~2,000 lines

**Grand Total Gap:** ~4,500-4,750 lines of Python-only code

---

## What Happened

### Original Issue (December 2025)
- **Problem:** Go had ~12,000 lines of code that other languages didn't have
- **Commits:** c5a0fdb, de59f19, 771670e added Go-only implementations
- **Impact:** CI failing, cross-language tests breaking

### Resolution Attempt (Commit 50793ac3)
- **Action:** Reverted to commit 439c6bf (last stable state)
- **Result:** Removed ~12,000 lines of Go-only code
- **Goal:** Restore cross-language parity

### Current State (January 2026)
- **Problem:** Python still has those implementations (~4,750 lines)
- **Impact:** Parity broken in opposite direction
- **Status:** Go (and other languages) missing features that Python has

---

## Why This Happened

### Root Cause
The revert removed Go implementations but **did not remove Python implementations** because:

1. Python implementations were added BEFORE the problematic Go commits
2. The revert only went back to 439c6bf, which already had Python features
3. Python's advanced techniques/compositions/protocols were implemented earlier
4. No corresponding removal of Python-only features was done

### Timeline Reconstruction

**Earlier (Pre-439c6bf):**
- Python techniques, compositions, and protocols implemented
- These were Python-only at the time but not flagged as parity issues

**December 2025 (Commits c5a0fdb, de59f19, 771670e):**
- Go implementations added to match Python
- BUT: Implementations were incomplete/different
- CI started failing due to incompatibilities

**January 2026 (Commit 50793ac3 - Revert):**
- Reverted Go back to 439c6bf state
- Python kept its implementations (already present at 439c6bf)
- **Result:** Parity broken in opposite direction

---

## CI Status

### Current CI Failures

**Recent Run Analysis:**
- Lint workflow: ❌ FAILING (fixed with commit 4fb53f6b - formatting)
- Test workflows: ❌ FAILING (multiple languages)
- Integration tests: ❌ FAILING

**CI failures are likely due to:**
1. Cross-language equivalence tests expecting features in all languages
2. Import errors (Go/Rust/etc. trying to import non-existent modules)
3. Test fixtures assuming feature parity

---

## Resolution Options

### Option 1: Remove Python-Only Features (Quick Fix)

**Action:** Remove Python implementations to match Go's state

**Files to Remove:**
```bash
# Reasoning techniques
agenkit/techniques/reasoning/graph_of_thought.py
agenkit/techniques/reasoning/reasoning_graph.py
agenkit/techniques/reasoning/least_to_most.py
agenkit/techniques/reasoning/plan_and_solve.py

# Compositions (entire directory)
rm -rf agenkit/techniques/compositions/

# Protocols (entire directory)
rm -rf agenkit/techniques/protocols/
```

**Pros:**
- ✅ Immediate parity restoration
- ✅ CI should pass (no missing features)
- ✅ Clean baseline for future work

**Cons:**
- ❌ Loses significant Python functionality (~4,750 lines)
- ❌ Users with Python may be using these features
- ❌ Backwards incompatible change

**Estimated Effort:** 1-2 hours
**Risk:** Medium (breaking change for Python users)

---

### Option 2: Implement Missing Features in Go (And Other Languages)

**Action:** Bring Go (and other languages) up to Python's feature level

**Work Required:**

**Go Implementation:**
1. 3 reasoning techniques (~1,550 lines)
2. 9 compositions (~1,200 lines)
3. 2 protocols (~2,000 lines)
4. Tests for all (~1,500 lines)
5. Examples (~500 lines)

**Total per language:** ~6,750 lines

**For all languages (Rust, TypeScript, C++, Zig):**
- 5 languages × ~6,750 lines = ~33,750 lines

**Pros:**
- ✅ Achieves true cross-language parity
- ✅ Keeps Python functionality
- ✅ No breaking changes
- ✅ Follows proper cross-language development process

**Cons:**
- ❌ Massive effort (weeks/months of work)
- ❌ Requires careful design and testing
- ❌ Blocks v0.46.1 release

**Estimated Effort:** 4-8 weeks (1-2 weeks per language)
**Risk:** High (complexity, time, coordination)

---

### Option 3: Mark as Experimental/Python-Preview Features

**Action:** Document these as Python-only experimental features

**Implementation:**
1. Add `@experimental` decorators to Python code
2. Update documentation to clearly mark Python-only features
3. Exclude from cross-language equivalence tests
4. Create tracking issues for other language implementations

**Pros:**
- ✅ Quick fix (documentation only)
- ✅ Keeps Python functionality
- ✅ Sets expectations correctly
- ✅ Allows incremental implementation in other languages

**Cons:**
- ❌ Breaks "cross-language parity" philosophy
- ❌ Users confused about feature availability
- ❌ Maintenance burden (tracking which features exist where)

**Estimated Effort:** 1-2 days (documentation + CI exclusions)
**Risk:** Low (no code changes)

---

### Option 4: Hybrid Approach (RECOMMENDED)

**Action:** Combination of Option 1 and Option 2

**Phase 1 (Immediate - v0.46.1):**
1. **Remove compositions and protocols** from Python
   - These are newer, less critical
   - Users less likely to depend on them
   - Reduces gap to ~1,550 lines (just reasoning techniques)

2. **Mark reasoning techniques as experimental** in Python
   - Keep graph_of_thought, least_to_most, plan_and_solve
   - Add `@experimental` decorators
   - Exclude from cross-language tests
   - Document as Python-preview features

**Phase 2 (Future - v0.47.0 or later):**
1. Create RFCs for each feature category
2. Design cross-language APIs
3. Implement in all languages simultaneously
4. Add to cross-language equivalence tests

**Pros:**
- ✅ Immediate parity restoration (removes 50% of gap)
- ✅ Keeps core reasoning techniques in Python
- ✅ Sets expectations correctly
- ✅ Provides path forward for proper implementation

**Cons:**
- ⚠️ Some breaking changes (compositions/protocols removal)
- ⚠️ Requires careful communication to users

**Estimated Effort:**
- Phase 1: 1 day (removal + documentation)
- Phase 2: 4-8 weeks (proper implementation)

**Risk:** Medium (some breaking changes, but managed)

---

## Recommended Action

**Execute Option 4 (Hybrid Approach) in two phases:**

### Immediate (This Week - v0.46.1)

1. **Remove Python compositions module**
   ```bash
   git rm -r agenkit/techniques/compositions/
   ```

2. **Remove Python protocols module**
   ```bash
   git rm -r agenkit/techniques/protocols/
   ```

3. **Mark Python reasoning techniques as experimental**
   - Add decorators to graph_of_thought, least_to_most, plan_and_solve
   - Update documentation
   - Exclude from cross-language equivalence tests

4. **Update tests**
   - Remove composition/protocol tests
   - Update cross-language tests to skip experimental features

5. **Document changes**
   - CHANGELOG entry (breaking changes)
   - Migration guide for users
   - Roadmap for future implementations

**Estimated Timeline:** 1-2 days
**Impact:** Restores parity for 50% of gap, documents rest

### Future (v0.47.0 or later)

1. Create RFCs for compositions, protocols, and advanced reasoning
2. Design cross-language APIs with input from all language maintainers
3. Implement in all 6 languages simultaneously (or use feature flags)
4. Add comprehensive cross-language equivalence tests
5. Remove experimental markers once all languages have implementations

**Estimated Timeline:** 4-8 weeks
**Impact:** Full cross-language parity with proper process

---

## Success Criteria

**v0.46.1 (Immediate):**
- [ ] CI passing (all languages)
- [ ] Cross-language equivalence tests passing
- [ ] Parity gap reduced to <30% (from 100%)
- [ ] Experimental features clearly documented
- [ ] No unexpected breaking changes

**v0.47.0 (Future):**
- [ ] All 6 languages have same feature set
- [ ] Cross-language equivalence tests cover all features
- [ ] No experimental/preview features remaining
- [ ] Comprehensive documentation for all features
- [ ] Feature parity automatically enforced in CI

---

## Communication Plan

### User-Facing Changes (v0.46.1)

**Breaking Changes:**
```markdown
## ⚠️ Breaking Changes in v0.46.1

**Removed Python-only modules (cross-language parity restoration):**

- `agenkit.techniques.compositions` - All composition patterns removed
  - Migration: Use direct agent composition patterns instead
  - Will be re-added in v0.47.0 with cross-language support

- `agenkit.techniques.protocols` - A2A and MCP protocols removed
  - Migration: Use standard HTTP/gRPC adapters instead
  - Will be re-added in v0.47.0 with cross-language support

**Experimental features marked:**

- `graph_of_thought` - Now marked as experimental (Python-only)
- `least_to_most` - Now marked as experimental (Python-only)
- `plan_and_solve` - Now marked as experimental (Python-only)

These features remain available in Python but are not yet available in other
languages. They will be properly implemented across all languages in v0.47.0.
```

### Developer-Facing Changes

**New Development Process:**
```markdown
## Cross-Language Feature Development

Starting with v0.46.1, all new features must follow the cross-language
development process:

1. Create RFC in `docs/rfcs/` with cross-language API design
2. Get approval from language maintainers
3. Implement in all languages OR use experimental markers
4. Add cross-language equivalence tests
5. Document feature availability per language

This prevents future parity issues like #369.
```

---

## Next Steps

**Immediate Actions (Today):**

1. **Review this investigation** - Confirm analysis and recommendation
2. **Get approval** - Option 4 (Hybrid Approach) from maintainers
3. **Execute Phase 1** - Remove compositions/protocols, mark reasoning as experimental
4. **Update Issue #369** - Post this analysis as comment
5. **Create v0.46.1 PR** - With all changes and documentation

**This Week (v0.46.1):**

1. Complete Phase 1 implementation (1-2 days)
2. Verify CI passes in all languages
3. Update documentation and CHANGELOG
4. Release v0.46.1 with parity fixes
5. Close Issue #369

**Future (v0.47.0):**

1. Create RFCs for compositions, protocols, reasoning techniques
2. Plan proper cross-language implementation
3. Implement in all 6 languages with proper process
4. Add to v0.47.0 milestone

---

## Appendix: File Inventory

### Python-Only Files (To Be Addressed)

**Reasoning Techniques (Keep as experimental):**
- `agenkit/techniques/reasoning/graph_of_thought.py` (523 lines)
- `agenkit/techniques/reasoning/reasoning_graph.py` (422 lines)
- `agenkit/techniques/reasoning/least_to_most.py` (318 lines)
- `agenkit/techniques/reasoning/plan_and_solve.py` (367 lines)

**Compositions (Remove):**
- `agenkit/techniques/compositions/actor_critic_variation.py`
- `agenkit/techniques/compositions/context_optimization.py`
- `agenkit/techniques/compositions/exploration.py`
- `agenkit/techniques/compositions/goal_monitoring.py`
- `agenkit/techniques/compositions/learning_feedback.py`
- `agenkit/techniques/compositions/prioritization.py`
- `agenkit/techniques/compositions/rag.py`
- `agenkit/techniques/compositions/rag_with_citations.py`
- `agenkit/techniques/compositions/simple_human_approval.py`

**Protocols (Remove):**
- `agenkit/techniques/protocols/a2a/` (10 files)
- `agenkit/techniques/protocols/mcp/` (9 files)

---

**Document Owner:** Investigation Team
**Status:** Analysis Complete - Awaiting Decision
**Next Review:** After approval of recommended approach
