# Test Failures - v0.48.0 Release Blockers

**Date**: January 15, 2026
**Status**: RELEASE BLOCKED - Critical test failures must be fixed

---

## Summary

Cross-language test verification revealed **multiple critical failures** that block the v0.48.0 release:

| Language   | Status | Failures | Details |
|------------|--------|----------|---------|
| Python     | ⚠️  | 2 tests  | Chaos tests failing |
| Go         | ✅ | 0        | All tests passed |
| TypeScript | ❌ | 14 tests | adapter.name() not a function |
| Rust       | ❌ | Compile errors | Message API mismatches in examples |
| C++        | ⏳ | Unknown  | Tests still running |
| Zig        | ✅ | 0        | All tests passed |

**Verdict**: Cannot release until TypeScript and Rust are fixed. Python chaos tests are lower priority.

---

## Failure Details

### 1. TypeScript: 14 Test Failures (CRITICAL)

**Issue**: `adapter.name()` is not a function

**Affected Files**:
- `agenkit-ts/src/__tests__/anthropic.test.ts` (7 failures)
- `agenkit-ts/src/__tests__/openai.test.ts` (7 failures)

**Failing Tests**:
Both Anthropic and OpenAI adapters:
- should create with default config
- should create with custom model
- should have correct capabilities
- should return agent name with model
- should use custom temperature
- should use custom maxTokens
- should use environment variable for API key

**Root Cause**:
The `name()` method is either:
1. Missing from the adapter classes
2. Changed from method to property (or vice versa)
3. Not properly exported/inherited

**Error Message**:
```
TypeError: adapter.name is not a function
```

**Test Results**:
- 1,119 tests passed
- 14 tests failed
- 7 tests skipped (pattern benchmarks)

**Priority**: 🔴 CRITICAL - Blocks release

**Fix Required**:
1. Investigate AnthropicAdapter and OpenAIAdapter classes
2. Ensure `name()` method is properly defined
3. Verify inheritance chain if using base class
4. Re-run tests to confirm fix

---

### 2. Rust: Compilation Errors (CRITICAL)

**Issue**: Message API mismatches in examples causing compilation failures

**Affected Examples**:
1. `examples/production_secure.rs`
2. `examples/pattern-parallel-usage.rs`

**Error 1 - production_secure.rs**:
```
error[E0599]: no method named `content_as_str` found for struct `Message`
  --> examples/production_secure.rs:45:67
   |
45 |             format!("{} processed: {}", self.name, message.content_as_str()),
   |                                                                   ^^^^^^^^^^
```

**Error 2 - pattern-parallel-usage.rs**:
```
error[E0308]: mismatched types
  --> examples/pattern-parallel-usage.rs:45:13
   |
45 |             format!("{} processed: {}", self.name, message.content()),
   |             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   |             expected `Value`, found `String`
```

**Root Cause**:
1. `message.content_as_str()` doesn't exist (removed or renamed)
2. `message.content()` returns wrong type (String vs Value)
3. Examples not updated after Message API change

**Additional Warnings**:
- Unused variables: `agent1`, `agent2`, `agent3`
- Some tests generated 22 warnings (20 duplicates)

**Priority**: 🔴 CRITICAL - Blocks release

**Fix Required**:
1. Check current Message API in agenkit-rust/src/core/message.rs
2. Update examples to use correct API
   - Replace `content_as_str()` with correct method
   - Fix `content()` return type handling
3. Fix unused variable warnings
4. Re-compile all examples
5. Run full test suite

---

### 3. Python: 2 Chaos Test Failures (LOW PRIORITY)

**Issue**: Flaky chaos tests failing

**Failing Tests**:
1. `tests/chaos/test_slow_responses.py::test_gradual_performance_degradation`
2. `tests/chaos/test_partial_failures.py::test_stream_cancellation_cleanup`

**Test Results**:
- 1,788 tests passed ✅
- 2 tests failed ❌
- 42 tests skipped
- Coverage: 72%
- Time: 358.09s (5:58)

**Context**:
- Chaos tests are designed to test edge cases
- These are known to be flaky
- May be timing-dependent
- Do not block core functionality

**Priority**: 🟡 LOW - Investigate but don't block release

**Investigation Plan**:
1. Re-run tests 3 times to confirm not transient
2. Review test expectations vs actual behavior
3. Check if timing assumptions need adjustment
4. Consider marking as flaky if not reproducible

---

### 4. C++: Status Unknown

**Status**: Tests still running after 10+ minutes

**Expected**:
- Should complete in ~50 seconds
- Tests launched at 22:07:59
- Now 22:19+ (12+ minutes elapsed)

**Potential Issues**:
1. Tests hanging/deadlocked
2. Build issues
3. Resource exhaustion
4. Background task not reporting correctly

**Priority**: ⏳ WAITING

**Next Steps**:
1. Check if ctest process is still running
2. Kill and restart if hung
3. Review build logs for errors
4. Check test output file

---

## Test Environment

**System**:
- OS: macOS Darwin 25.2.0
- Working Directory: /Users/scttfrdmn/src/agenkit
- Branch: main
- Commit: b45edeb8 (docs: Update ROADMAP.md - mark v0.48.0 as complete)

**Test Commands Used**:
- Python: `make test` (parallel execution)
- Go: `cd agenkit-go && go test ./... -v`
- TypeScript: `cd agenkit-ts && npm test`
- Rust: `cd agenkit-rust && cargo test`
- C++: `cd agenkit-cpp/build && ctest --output-on-failure`
- Zig: `cd agenkit-zig && zig build test`

---

## Fix Priority

### Must Fix Before Release (CRITICAL)

1. **TypeScript adapter.name() issue** - 14 tests failing
   - Estimated: 1-2 hours
   - Impact: Core adapter functionality broken

2. **Rust Message API mismatches** - Examples won't compile
   - Estimated: 2-3 hours
   - Impact: Users can't use examples

### Should Investigate (C++ status)

3. **C++ test status** - Unknown if passing or hanging
   - Estimated: 30 minutes - 2 hours
   - Impact: Unknown until investigated

### Can Defer (LOW PRIORITY)

4. **Python chaos tests** - 2 flaky tests
   - Estimated: 2-4 hours to properly fix
   - Impact: Edge case testing only
   - Note: Known flaky, don't block release

---

## Action Plan

### Immediate Actions (Next 30 minutes)

1. Check C++ test status:
   ```bash
   ps aux | grep ctest
   kill -9 <pid> if hung
   cd agenkit-cpp/build && ctest --output-on-failure
   ```

2. Fix TypeScript adapter.name():
   ```bash
   cd agenkit-ts
   # Investigate AnthropicAdapter and OpenAIAdapter
   # Check src/adapters/llm/ files
   # Add/fix name() method
   npm test -- anthropic.test.ts openai.test.ts
   ```

3. Fix Rust Message API:
   ```bash
   cd agenkit-rust
   # Check src/core/message.rs for correct API
   # Update examples/production_secure.rs
   # Update examples/pattern-parallel-usage.rs
   cargo test
   cargo build --examples
   ```

### Before Final Release

4. Re-run full test suite:
   ```bash
   # Python
   make test

   # Go
   cd agenkit-go && go test ./...

   # TypeScript
   cd agenkit-ts && npm test

   # Rust
   cd agenkit-rust && cargo test && cargo build --examples

   # C++
   cd agenkit-cpp/build && ctest

   # Zig
   cd agenkit-zig && zig build test
   ```

5. Verify parity:
   ```bash
   bash scripts/test-parity.sh
   pytest tests/test_parity_validation.py -v
   ```

---

## Success Criteria for Release

Before creating v0.48.0 release tag:

- [ ] TypeScript: All tests passing (0 failures)
- [ ] Rust: All examples compile and tests pass
- [ ] C++: All tests passing
- [ ] Go: All tests passing (already ✅)
- [ ] Zig: All tests passing (already ✅)
- [ ] Python: <5 failures, none in core functionality
- [ ] Parity validation: All thresholds met
- [ ] Documentation: All docs generated successfully

**Current Status**: 3/7 languages passing, 2 critical failures, 1 unknown, 1 low-priority

---

**Last Updated**: January 15, 2026 22:19 UTC
**Owner**: Release preparation
**Milestone**: v0.48.0 (BLOCKED)
