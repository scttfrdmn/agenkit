# Cross-Language Parity Plan

**Version:** 1.0
**Last Updated:** January 4, 2026
**Target Release:** v0.47.0

---

## Current State (Acceptable Drift)

Agenkit currently has intentional feature drift between languages. This is **acceptable** and allows each language to move at its own pace while we work toward eventual parity.

### Current Feature Status

| Feature Category | Python | Go | Rust | TypeScript | C++ | Zig |
|-----------------|--------|-----|------|-----------|-----|-----|
| **Core Patterns (18)** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Basic Reasoning (3)** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Advanced Reasoning (3)** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Compositions (9)** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Protocols (2)** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |

**Legend:**
- ✅ Fully implemented
- ❌ Not yet implemented

### Python-Ahead Features

**Advanced Reasoning Techniques (3):**
1. Graph-of-Thought - Multi-hop reasoning with logical relationships
2. Least-to-Most - Problem decomposition from simple to complex
3. Plan-and-Solve - Strategic planning before execution

**Compositions (9):**
1. SimpleRAG - Retrieval-augmented generation
2. CitedRAG - RAG with citations
3. ContextOptimization - Token reduction
4. TaskQueue - Priority-based execution
5. GoalMonitoring - Goal-based termination
6. ExplorationStrategy - UCB-based exploration
7. LearningFromFeedback - Interaction storage
8. ActorCritic - Reinforcement learning variation
9. HumanApproval - Simple approval wrapper

**Protocols (2):**
1. A2A (Agent-to-Agent) - Cross-platform agent communication
2. MCP (Model Context Protocol) - Tool and resource access

---

## Philosophy: Progressive Parity

### Why Drift is Acceptable

1. **Development Velocity** - Languages can move at different speeds
2. **Community Contribution** - Contributors focus on languages they know
3. **Use Case Driven** - Implement features when users need them
4. **Quality Over Speed** - Better to do it right than rush all languages

### When Parity Matters

Parity is **critical** for:
- ✅ Core patterns (18 agent patterns) - ALL languages must have
- ✅ Basic reasoning (CoT, ToT, SC) - ALL languages must have
- ✅ Core APIs and interfaces - ALL languages must match

Parity is **nice-to-have** for:
- ⚠️ Advanced reasoning techniques - Implement as needed
- ⚠️ Compositions - Utility patterns, language-specific variations OK
- ⚠️ Protocols - Not all languages need all protocols

---

## v0.47.0 Plan: Proper Cross-Language Implementation

**Theme:** Documentation & Testing Excellence + Cross-Language Parity (Subset)

### Goals

Achieve parity for **high-value features** across all languages using proper process:
1. RFC-driven design
2. Cross-language API contracts
3. Simultaneous implementation (or feature flags)
4. Comprehensive testing

### Scope for v0.47.0

**Target Features (Prioritize by User Value):**

**Phase 1: Advanced Reasoning (8 weeks)**
- Graph-of-Thought
- Least-to-Most
- Plan-and-Solve

**Phase 2: Essential Compositions (4 weeks)**
- SimpleRAG (highest user value)
- CitedRAG (documentation workflows)
- GoalMonitoring (common pattern)

**Defer to Future:**
- Other compositions (can be language-specific)
- Protocols (complex, lower priority)

---

## Implementation Process

### Step 1: RFC Creation (Week 1)

For each feature, create RFC in `docs/rfcs/`:

**RFC Template:**
```markdown
# RFC-XXX: [Feature Name] Cross-Language Implementation

## Summary
One-paragraph overview

## Motivation
Why this feature is valuable across languages

## Design
Language-agnostic API design with examples

## Cross-Language Considerations
- Type mappings (e.g., Python dict → Go map → Rust HashMap)
- Error handling patterns per language
- Async/sync variations
- Memory management differences

## API Contract
Precise input/output specification for equivalence tests

## Implementation Notes
Language-specific considerations

## Alternatives Considered
Other approaches and why rejected

## Timeline
Expected implementation schedule
```

**RFCs to Create:**
1. RFC-001: Graph-of-Thought Cross-Language API
2. RFC-002: Least-to-Most Cross-Language API
3. RFC-003: Plan-and-Solve Cross-Language API
4. RFC-004: SimpleRAG Cross-Language API
5. RFC-005: CitedRAG Cross-Language API
6. RFC-006: GoalMonitoring Cross-Language API

### Step 2: API Contract Definition (Week 2)

Define precise contracts for equivalence testing:

**Example: Graph-of-Thought Contract**
```yaml
feature: graph_of_thought
inputs:
  - name: problem
    type: string
    description: Problem statement
  - name: max_thoughts
    type: integer
    default: 10
  - name: aggregation_mode
    type: enum
    values: [path_based, node_based]

outputs:
  - name: conclusion
    type: string
  - name: graph
    type: object
    fields:
      - nodes: array of ThoughtNode
      - edges: array of LogicalEdge

metadata:
  - technique: "graph_of_thought"
  - num_thoughts: integer
  - num_edges: integer
  - reasoning_paths: integer
```

### Step 3: Equivalence Test Creation (Week 2)

Write tests BEFORE implementation:

**Example:**
```python
# tests/cross_language/equivalence/test_graph_of_thought.py

def test_graph_of_thought_basic():
    """Test Graph-of-Thought produces equivalent outputs"""
    problem = "Is the statement 'All birds can fly' true?"

    # Run in all languages
    results = run_cross_language(
        'graph_of_thought',
        {'problem': problem, 'max_thoughts': 5}
    )

    # Check equivalence
    assert_equivalent_outputs(results)
    assert_metadata_matches(results, 'num_thoughts')
```

### Step 4: Implementation Schedule (Weeks 3-10)

**Week 3-4: Graph-of-Thought**
- Go implementation (2 days)
- Rust implementation (2 days)
- TypeScript implementation (2 days)
- C++ implementation (2 days)
- Zig implementation (2 days)
- Total: 10 days / 5 contributors = 2 weeks (parallel)

**Week 5-6: Least-to-Most**
- All languages (parallel implementation)

**Week 7-8: Plan-and-Solve**
- All languages (parallel implementation)

**Week 9-10: SimpleRAG**
- All languages (parallel implementation)

**Week 11-12: CitedRAG + GoalMonitoring**
- All languages (parallel implementation)

### Step 5: Testing & Validation (Week 13)

**Cross-Language Equivalence Tests:**
- All tests passing in all languages
- Metadata matches across implementations
- Performance benchmarks comparable

**Integration Tests:**
- Features work with existing patterns
- Examples demonstrate usage
- Documentation complete

### Step 6: Documentation (Week 14)

**Per-Language Documentation:**
- API reference for each language
- Usage examples
- Migration guides (if API differs)
- Performance characteristics

**Cross-Language Documentation:**
- Feature availability matrix
- API compatibility notes
- Best practices per language

---

## Success Metrics

### v0.47.0 Completion Criteria

**Implementation:**
- [ ] 3 advanced reasoning techniques in all 6 languages
- [ ] 3 essential compositions in all 6 languages
- [ ] Total: 6 features × 6 languages = 36 implementations

**Testing:**
- [ ] Cross-language equivalence tests passing (100%)
- [ ] Integration tests in all languages
- [ ] Performance benchmarks documented

**Documentation:**
- [ ] 6 RFCs approved and published
- [ ] API reference complete for all languages
- [ ] Examples in each language (6 features × 6 languages = 36 examples)

**Quality:**
- [ ] No language-specific bugs
- [ ] Consistent behavior across languages
- [ ] Feature parity automatically enforced in CI

---

## CI/CD Enforcement

### New CI Check: Feature Parity Validation

**Add to GitHub Actions:**
```yaml
- name: Check Feature Parity
  run: |
    python scripts/check_feature_parity.py
    # Fails if new public APIs detected in one language without others
```

**Script Logic:**
1. Scan all language directories for public APIs
2. Compare against feature matrix (stored in `docs/FEATURE_MATRIX.md`)
3. Fail if new APIs found without corresponding matrix update
4. Require sign-off from language maintainers

### Feature Matrix Tracking

**`docs/FEATURE_MATRIX.md`:**
```markdown
| Feature | Python | Go | Rust | TS | C++ | Zig | Status |
|---------|--------|-----|------|-----|-----|-----|--------|
| Graph-of-Thought | ✅ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | In Progress |
| Least-to-Most | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | Planned |
| SimpleRAG | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | Planned |
```

Updated automatically by CI on each commit.

---

## Resource Requirements

### Team Composition

**Ideal:**
- 1 contributor per language (6 total)
- Each works 2-3 weeks (part-time)
- Total person-weeks: 12-18

**Reality:**
- Likely 1-2 core contributors
- Serial implementation per language
- Total time: 12-14 weeks (3.5 months)

### Decision: Parallel vs Serial

**Option A: Parallel (Recommended if resources available)**
- All languages implemented simultaneously
- Requires 6 contributors
- Completes in 12-14 weeks
- Ensures consistency

**Option B: Serial (Fallback)**
- One language at a time
- Can be done by 1-2 contributors
- Takes 6-12 months (1-2 weeks per language per feature)
- Risk of drift

**Recommendation:** Hybrid
- Implement 2-3 languages in parallel (Python/Go/Rust as reference)
- Others follow within 2-4 weeks
- Use feature flags to mark incomplete implementations

---

## Risk Mitigation

### Risk 1: Time/Resource Constraints

**Mitigation:**
- Use feature flags for incomplete implementations
- Document feature availability clearly
- Allow partial rollout (e.g., 3 languages in v0.47.0, rest in v0.48.0)

### Risk 2: Design Disagreements

**Mitigation:**
- RFC process with review period
- Get language maintainer buy-in upfront
- Prototype in 2 languages before committing to API

### Risk 3: Implementation Bugs

**Mitigation:**
- Equivalence tests catch cross-language inconsistencies
- Property-based testing for edge cases
- Fuzzing with same inputs across languages

---

## Timeline Summary

```
v0.47.0 Development (May 2026 Release)
├─ Week 1-2: RFC Creation + API Contracts
├─ Week 3-4: Graph-of-Thought (all languages)
├─ Week 5-6: Least-to-Most (all languages)
├─ Week 7-8: Plan-and-Solve (all languages)
├─ Week 9-10: SimpleRAG (all languages)
├─ Week 11-12: CitedRAG + GoalMonitoring
├─ Week 13: Testing & Integration
└─ Week 14: Documentation & Release
```

**Total:** 14 weeks (3.5 months)
**Start:** February 2026
**Release:** May 17, 2026

---

## Issue Tracking

### GitHub Issues to Create

**v0.47.0 Milestone:**
1. #TBD - Create RFCs for 6 cross-language features
2. #TBD - Implement Graph-of-Thought in Go/Rust/TS/C++/Zig
3. #TBD - Implement Least-to-Most in Go/Rust/TS/C++/Zig
4. #TBD - Implement Plan-and-Solve in Go/Rust/TS/C++/Zig
5. #TBD - Implement SimpleRAG in Go/Rust/TS/C++/Zig
6. #TBD - Implement CitedRAG in Go/Rust/TS/C++/Zig
7. #TBD - Implement GoalMonitoring in Go/Rust/TS/C++/Zig
8. #TBD - Add cross-language equivalence tests for all features
9. #TBD - Add feature parity CI enforcement
10. #TBD - Update feature matrix documentation

---

## Future Work (Post-v0.47.0)

### v0.48.0 or Later

**Remaining Compositions:**
- ContextOptimization
- TaskQueue
- ExplorationStrategy
- LearningFromFeedback
- ActorCritic

**Protocols (Complex, Long-Term):**
- A2A Protocol
- MCP Protocol

**Criteria for Implementation:**
- User demand for feature
- Proven value in Python
- Clear cross-language use case
- RFC approval and design

---

## Communication Plan

### User-Facing

**Documentation:**
- Clearly mark Python-ahead features in docs
- Show feature availability matrix on main README
- Provide migration timeline

**Example:**
```markdown
## Feature Availability

⚠️ Some features are available in Python but not yet in other languages.
We're working on cross-language implementations in v0.47.0 (May 2026).

| Feature | Python | Go | Rust | TypeScript | C++ | Zig |
|---------|--------|-----|------|-----------|-----|-----|
| Graph-of-Thought | ✅ | ⏳ v0.47.0 | ⏳ v0.47.0 | ⏳ v0.47.0 | ⏳ v0.47.0 | ⏳ v0.47.0 |
| SimpleRAG | ✅ | ⏳ v0.47.0 | ⏳ v0.47.0 | ⏳ v0.47.0 | ⏳ v0.47.0 | ⏳ v0.47.0 |
```

### Developer-Facing

**CONTRIBUTING.md Section:**
```markdown
## Adding Cross-Language Features

New features should be implemented across all languages. If implementing
in only one language:

1. Mark as experimental with clear documentation
2. Create tracking issues for other languages
3. Propose timeline for cross-language implementation
4. Update feature matrix in docs/FEATURE_MATRIX.md
```

---

## Conclusion

**Current State:** Python has advanced features other languages lack. This is **acceptable and intentional**.

**v0.47.0 Goal:** Bring other languages to parity for high-value features using proper RFC-driven process.

**Long-Term Vision:** All languages have same core features, with language-specific extensions documented clearly.

**Success:** Users can choose any language and get great experience, with clear expectations about feature availability.

---

**Document Owner:** Release Planning Team
**Status:** Approved Plan
**Next Review:** February 2026 (Start of v0.47.0 development)
