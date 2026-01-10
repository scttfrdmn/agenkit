# v0.46.1 Release Checklist - Critical CI/CD Fixes

**Due Date:** January 9, 2026 (TODAY!)
**Theme:** Critical bug fixes and CI/CD improvements for production stability

---

## Priority Breakdown

### 🔴 CRITICAL (Must Complete Today)

#### #372 - Update Language Versions to 2026 Standards
**Estimate:** 1-2 hours
**Status:** Not started

**Tasks:**
- [ ] Update Python: 3.10/3.11/3.12 → 3.11/3.12/3.13
- [ ] Update Go: 1.21/1.22 → 1.22/1.23
- [ ] Update Node.js: 18/20 → 20/22
- [ ] Update Rust: latest stable
- [ ] Update CI matrix in `.github/workflows/*.yml`
- [ ] Test locally before pushing

**Files:**
- `.github/workflows/test.yml`
- `.github/workflows/lint.yml`
- `.github/workflows/benchmarks.yml`

---

#### #371 - Python Tests Running Extremely Slowly (11+ minutes)
**Estimate:** 2-3 hours
**Status:** Not started

**Current Problem:**
- Python tests taking 11+ minutes in CI
- Expected: 2-4 minutes (like v0.44.0)

**Potential Causes:**
- pytest-xdist not configured correctly
- Too many tests running serially
- Integration tests timing out
- No test parallelization

**Investigation Steps:**
- [ ] Run `make test` locally and time it (baseline)
- [ ] Check pytest configuration in `pyproject.toml`
- [ ] Review pytest-xdist settings (`-n auto`)
- [ ] Identify slow tests with `pytest --durations=10`
- [ ] Check if integration tests are timing out

**Solutions to Try:**
1. Increase pytest-xdist workers: `-n 4` or `-n 8`
2. Mark slow tests with `@pytest.mark.slow` and skip in quick mode
3. Optimize fixture teardown
4. Use `pytest-timeout` to catch hanging tests

**Files:**
- `pyproject.toml`
- `.github/workflows/test.yml`
- `scripts/test-local.sh`

---

#### #370 - Investigate Go Test Failures in Matrix Configurations
**Estimate:** 1-2 hours
**Status:** Not started

**Problem:**
- Some Go test matrix configurations failing
- Need to identify which OS/Go version combinations

**Investigation:**
- [ ] Check GitHub Actions logs for failure patterns
- [ ] Identify failing OS: Ubuntu/macOS/Windows?
- [ ] Identify failing Go version: 1.22/1.23?
- [ ] Reproduce locally if possible
- [ ] Check for race conditions (`go test -race`)

**Potential Causes:**
- OS-specific path issues
- Go version compatibility
- Network timeouts in CI
- Protobuf version conflicts (see v0.44.0 fix)

**Files:**
- `.github/workflows/test.yml`
- `agenkit-go/go.mod`
- Go test files

---

### 🟡 HIGH (Should Complete Today If Time)

#### #342 - Re-enable and Validate CI/CD Workflows
**Estimate:** 1-2 hours
**Status:** Not started

**Problem:**
- Some workflows may be disabled
- Need comprehensive validation

**Tasks:**
- [ ] List all workflows in `.github/workflows/`
- [ ] Check which are active/disabled
- [ ] Re-enable critical workflows:
  - `test.yml`
  - `lint.yml`
  - `benchmarks.yml`
- [ ] Run each workflow manually to validate
- [ ] Check for any failing checks

**Files:**
- `.github/workflows/*.yml`

---

### 🔵 OPTIONAL (If Time Permits - Can Defer)

#### #369 - Go Cross-Language Parity Breaks
**Estimate:** 2-3 hours
**Status:** Investigation phase

**Problem:**
- Some Go implementations not matching Python/TypeScript
- Breaks cross-language compatibility

**Defer Decision:**
- If investigation shows minor issue → Fix in v0.46.1
- If investigation shows major refactor → Defer to v0.47.0

**Tasks:**
- [ ] Run `./scripts/test-parity.sh` to identify breaks
- [ ] Document which patterns/features differ
- [ ] Assess scope: Quick fix or major work?
- [ ] Make defer/include decision

---

## Testing Strategy

### Local Testing (Before Push)

```bash
# 1. Test all languages locally
make test                                    # Python (should be <2 min)
cd agenkit-go && go test ./... -race        # Go
cd agenkit-ts && npm test                   # TypeScript
cd agenkit-rust && cargo test               # Rust
cd agenkit-cpp/build && ctest               # C++
cd agenkit-zig && zig build test            # Zig

# 2. Check cross-language parity
./scripts/test-parity.sh

# 3. Verify CI changes locally (if possible)
act -l  # List workflows with act (GitHub Actions locally)
```

### CI Validation

```bash
# After push, monitor:
# 1. All workflow runs pass
# 2. Python tests complete in <4 minutes
# 3. Go tests pass on all matrix combinations
# 4. No new failures introduced
```

---

## Timeline (Optimistic)

| Task | Time | Cumulative |
|------|------|------------|
| #372 - Language versions | 1-2h | 1-2h |
| #370 - Go test failures | 1-2h | 2-4h |
| #371 - Python test performance | 2-3h | 4-7h |
| #342 - CI validation | 1-2h | 5-9h |
| Testing & validation | 1h | 6-10h |
| **Total** | **6-10 hours** | - |

**Realistic Completion:** End of day (if started immediately)
**If blockers:** Extend to Jan 10-11, 2026

---

## Success Criteria

### Before Release

- [ ] All CI workflows passing (green checks)
- [ ] Python tests complete in <4 minutes (target <2 min)
- [ ] Go tests pass on all matrix configurations
- [ ] All language versions updated to 2026 standards
- [ ] No new test failures introduced
- [ ] Local tests: `make test` passes in <2 minutes

### After Release

- [ ] Create Git tag: `v0.46.1`
- [ ] Update CHANGELOG.md with fixes
- [ ] Announce in GitHub Discussions (optional)
- [ ] Update ROADMAP.md milestone status

---

## Rollback Plan

If critical issues discovered during testing:

1. **Revert problematic changes**
2. **Extend deadline to Jan 10-11**
3. **Document blocker issues**
4. **Create focused fixes**

Don't ship broken CI - it blocks all future development.

---

## Notes

**Why v0.46.1 Exists:**
- v0.46.0 is large (27 issues complete, 6 remaining)
- CI issues blocking development velocity
- Need quick patch release before continuing v0.46.0

**After v0.46.1:**
- Continue v0.46.0 work (performance optimization)
- Plan v0.47.0 (documentation & testing excellence)
- Update documentation to reflect "toolkit" not "framework" terminology
- Triage 50+ unmilestoned issues

---

## Quick Commands Reference

```bash
# Start work
git checkout main
git pull origin main
git checkout -b fix/v0.46.1-ci-fixes

# Test locally
make test                 # Must pass in <2 min
./scripts/test-parity.sh  # Cross-language check

# When ready
git add .
git commit -m "fix(ci): v0.46.1 - CI/CD performance and stability fixes"
git push origin fix/v0.46.1-ci-fixes

# Create PR
gh pr create --title "v0.46.1 - Critical CI/CD Fixes" \
  --body "Fixes #372 #371 #370 #342" \
  --milestone "v0.46.1 - Critical Fixes"

# After merge
git tag v0.46.1
git push origin v0.46.1
```

---

**Last Updated:** January 9, 2026
**Status:** Ready to start
**Owner:** TBD
