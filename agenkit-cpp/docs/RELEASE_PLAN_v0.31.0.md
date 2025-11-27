# Release Plan: v0.31.0 - LLM Ecosystem

**Target Date**: 1 week from start
**Theme**: Expand LLM provider support and real-world examples
**Status**: Planning

---

## Goals

1. Support 4 LLM providers (Claude ✅, OpenAI, Gemini, Ollama)
2. Create 3 comprehensive examples with real LLMs
3. Improve HTTP performance by 50%+
4. Optimize parallel agent execution

---

## Issues

### LLM Adapters (High Priority)

- **#168** - Add Ollama adapter ⭐ **START HERE**
  - Local LLMs (free, fast, no API costs)
  - Perfect for development and testing
  - Models: Llama3.3, Mistral, Qwen, Phi-3
  - Estimated: 2-3 hours

- **#166** - Add OpenAI GPT adapter
  - GPT-4, GPT-4 Turbo, GPT-3.5
  - Most popular API
  - Estimated: 2-3 hours

- **#167** - Add Google Gemini adapter
  - Gemini Pro, Ultra, Flash
  - Google's latest models
  - Estimated: 2-3 hours

### Examples (High Priority)

- **#169** - ReAct pattern with tool use ⭐
  - Shows tool selection and reasoning
  - Uses Ollama (free) or Claude
  - 3 tools: Calculator, Weather, Search
  - Estimated: 3-4 hours

- **#170** - Multiagent collaboration
  - Multiple LLMs working together
  - Software dev team use case
  - Demonstrates LLM specialization
  - Estimated: 3-4 hours

### Performance (Medium Priority)

- **#171** - HTTP connection pooling ⭐
  - Expected: 50-75% latency reduction
  - Thread-safe connection reuse
  - Estimated: 4-6 hours

- **#172** - Parallel agent execution
  - Expected: 2-3x speedup for multi-agent
  - True async/parallel execution
  - Estimated: 3-4 hours

---

## Implementation Order

### Phase 1: Ollama First (Day 1-2)
1. **#168** - Ollama adapter (2-3h)
2. **#169** - ReAct example with Ollama (3-4h)

**Rationale**: Ollama is free and fast, perfect for development. Get this working first for immediate value.

### Phase 2: More Adapters (Day 2-3)
3. **#166** - OpenAI adapter (2-3h)
4. **#167** - Gemini adapter (2-3h)

**Rationale**: Expand LLM options once pattern is established.

### Phase 3: Advanced Examples (Day 3-4)
5. **#170** - Multiagent example (3-4h)

**Rationale**: Shows real-world collaboration with multiple LLMs.

### Phase 4: Performance (Day 4-5)
6. **#171** - Connection pooling (4-6h)
7. **#172** - Parallel execution (3-4h)

**Rationale**: Performance improvements benefit all adapters.

### Phase 5: Documentation & Testing (Day 6-7)
8. Update README with all examples
9. Update ROADMAP progress
10. Run all tests and benchmarks
11. Performance comparison document
12. Tag v0.31.0 release

---

## Success Criteria

### Must Have ✅
- [ ] Ollama adapter working (#168)
- [ ] At least 1 new real-world example (#169)
- [ ] All tests passing
- [ ] Documentation updated

### Should Have
- [ ] OpenAI adapter working (#166)
- [ ] Connection pooling implemented (#171)
- [ ] Performance benchmarks showing improvements

### Nice to Have
- [ ] Gemini adapter (#167)
- [ ] Multiagent example (#170)
- [ ] Parallel execution optimization (#172)

---

## Testing Plan

### Adapter Tests
- **Unit tests**: Mock HTTP responses
- **Integration tests**: Real API calls (manual, not in CI)
- **Example tests**: Verify examples compile and run

### Performance Tests
```bash
# Before/after benchmarks
./build/benchmarks/bench_http

# Connection pooling test
./build/benchmarks/bench_connection_pool

# Parallel execution test
./build/benchmarks/bench_multiagent
```

---

## Documentation Updates

### README.md
- Add Ollama example section
- Update "Examples" with new count
- Add "Supported LLMs" section

### ROADMAP.md
- Mark v0.31.0 tasks as complete
- Update progress percentages

### New Files
- `docs/LLM_ADAPTERS.md` - Adapter comparison guide
- `docs/EXAMPLES.md` - All examples with descriptions

---

## Release Checklist

- [ ] All priority issues closed (#168, #169, #171)
- [ ] Examples compile and run successfully
- [ ] Benchmarks show performance improvements
- [ ] README updated with new features
- [ ] CHANGELOG updated
- [ ] All tests passing (17/17 suites)
- [ ] No memory leaks (valgrind clean)
- [ ] Git tag created: v0.31.0
- [ ] GitHub release published
- [ ] Announcement prepared

---

## Estimated Total Time

**Minimum (Must Have)**: 5-7 hours (Ollama + ReAct example)
**Target (Should Have)**: 15-20 hours (All adapters + 2 examples + perf)
**Maximum (All features)**: 25-30 hours (Everything including nice-to-have)

**Realistic for 1 week**: Target scope (Should Have)

---

## Post-Release

After v0.31.0 ships:
1. Gather feedback on Ollama integration
2. Performance metrics collection
3. Plan v0.32.0 (Production Hardening)
4. Start Doxygen documentation work

---

## Notes

- **Ollama priority**: Free, local, fast - best for development
- **Connection pooling impact**: Biggest performance win
- **Examples over features**: Real examples drive adoption
- **Keep scope manageable**: Ship v0.31.0 in 1 week, iterate
