# Version Synchronization Plan

## Problem

Language versions are completely out of sync, violating the language parity principle.

**Current Versions** (as of 2025-11-28):
- **Python**: v0.13.0
- **Go**: No explicit version (uses git tags)
- **C++**: v0.29.2 (code) but v0.30.0 (latest release)
- **TypeScript**: v0.2.0
- **Rust**: v0.1.0

**Latest GitHub Release**: v0.30.0 - C++ Pattern Parity (2025-11-27)

## Critical Issues

1. **Version drift violates parity principle**: "No language is favored over another"
2. **User confusion**: Different versions imply different maturity levels
3. **Release chaos**: No coordinated release strategy
4. **Breaking changes**: Can't maintain SemVer across languages

## Proposed Version Strategy

### Option A: Unified Versioning (RECOMMENDED)

**Principle**: All languages share the same version number and release together.

**Benefits**:
- Clear communication: "AgentKit v0.31.0" means the same across all languages
- Forces coordination and parity
- Simpler for users to understand
- Industry standard (gRPC, Protobuf, OpenTelemetry)

**Drawbacks**:
- Language-specific work requires bumping all versions
- More complex release process

### Option B: Independent Versioning

**Principle**: Each language maintains its own version based on its progress.

**Benefits**:
- Languages can evolve independently
- Simpler individual releases

**Drawbacks**:
- Violates parity principle
- User confusion about feature availability
- Communication complexity

### Option C: Feature Versioning

**Principle**: Version numbers track feature parity, not individual releases.

**Example**:
- v1.0 = All 11 patterns + 3 LLM adapters + 10 examples (Tier 1 parity)
- v1.1 = Streaming support across all languages
- v1.2 = Advanced patterns across all languages

**Benefits**:
- Version communicates parity level
- Clear feature guarantees

**Drawbacks**:
- Frequent minor version bumps
- Requires strict feature coordination

## Recommendation: Option A (Unified Versioning)

**Rationale**: Aligns with the explicit parity principle stated in LANGUAGE_PARITY_PLAN.md.

## Immediate Action Plan

### Step 1: Sync to v0.31.0 (Next Release)

**Target Date**: 2025-12-01 (1 week)

**Release Name**: "v0.31.0 - Language Parity Foundation"

**Requirements for ALL languages**:
- Update version numbers to v0.31.0
- Verify parity status documented
- Update READMEs with current features
- Run full test suites (all must pass)

**Version Updates**:
- ✅ Python: v0.13.0 → v0.31.0
- ✅ Go: (tag) → v0.31.0
- ✅ C++: v0.30.0 → v0.31.0
- ✅ TypeScript: v0.2.0 → v0.31.0
- ✅ Rust: v0.1.0 → v0.31.0

### Step 2: Document Parity Status

Create **VERSION_STATUS.md** documenting:
- Current feature parity per language
- Known gaps
- Roadmap to full parity

### Step 3: Establish Release Process

**New Release Process** (all languages):
1. **Feature freeze** - No new features, only fixes
2. **Version bump** - Update all languages to same version
3. **Testing** - Run all test suites, verify parity
4. **Documentation** - Update READMEs, CHANGELOG
5. **Release** - Create GitHub release with all language tags
6. **Publish** - Publish packages (PyPI, npm, crates.io, vcpkg)

### Step 4: Create Release Automation

**Script**: `scripts/release.sh`
- Bump versions across all languages
- Generate unified CHANGELOG
- Create git tags for all languages
- Trigger package publications

## Version File Locations

### Python
- **File**: `pyproject.toml`
- **Line**: `version = "0.31.0"`

### Go
- **File**: N/A (uses git tags)
- **Tag**: `v0.31.0`, `agenkit-go/v0.31.0`

### C++
- **File**: `agenkit-cpp/CMakeLists.txt`
- **Line**: `project(agenkit VERSION 0.31.0 LANGUAGES CXX)`

### TypeScript
- **File**: `agenkit-ts/package.json`
- **Line**: `"version": "0.31.0"`

### Rust
- **File**: `agenkit-rust/Cargo.toml`
- **Line**: `version = "0.31.0"`

## v0.31.0 Release Content

Based on LANGUAGE_PARITY_PLAN.md and recent work:

**Theme**: Language Parity Foundation

**Key Changes**:
1. **Documentation**: Created LANGUAGE_PARITY_PLAN.md
2. **Issues**: Created 8 parity tracking issues (#173-#180)
3. **C++**: Ollama adapter + ReAct tools example (#168, #169)
4. **Analysis**: Created EXAMPLE_PARITY.md
5. **Version Sync**: All languages at v0.31.0

**Parity Status**:
- ✅ Python: 11/11 patterns, 3+ adapters, 20+ examples (leader)
- ✅ Go: 11/11 patterns, 3+ adapters, 15+ examples (complete)
- ✅ C++: 11/11 patterns, 3 adapters, 6 examples (feature complete, needs more examples)
- ⚠️ TypeScript: 8/11 patterns, 1 adapter, 4 examples (needs work - issues #173-176)
- ⚠️ Rust: 11/11 patterns, 0 adapters, 11 examples (needs adapters - issue #178)

**Known Gaps** (see LANGUAGE_PARITY_PLAN.md):
- TypeScript: Missing 3 patterns, 2 adapters, 6 examples
- Rust: Missing all 3 LLM adapters
- C++: Needs 4+ more comprehensive examples
- All: Need parity enforcement in CI/CD

## Future Releases

### v0.32.0 (Dec 2025)
**Focus**: TypeScript parity
- Complete TypeScript issues #173-176
- C++ OpenAI adapter + Multiagent example (#166, #170)
- All languages at v0.32.0

### v0.33.0 (Jan 2026)
**Focus**: Rust adapters
- Rust issue #178 (OpenAI, Anthropic, Ollama adapters)
- C++ additional examples
- All languages at v0.33.0

### v1.0.0 (Q2 2026)
**Focus**: Full production parity
- All languages: 11 patterns + 3 adapters + 10 examples + 95% tests
- Parity enforcement in CI/CD (#179)
- Migration guides (#180)
- Production-ready across all languages

## Success Criteria

**Definition of Version Sync Success**:
- ✅ All language version files updated to same version
- ✅ GitHub release with unified CHANGELOG
- ✅ All language test suites passing
- ✅ Documentation reflects current parity status
- ✅ Users understand version = parity level

## Communication Plan

**Release Announcement** (v0.31.0):
- Blog post: "AgentKit v0.31.0: Language Parity Foundation"
- Explain unified versioning strategy
- Document current parity status
- Outline path to v1.0.0
- Post to HN, Reddit, Twitter/X

**User Messaging**:
> "Starting with v0.31.0, all AgentKit languages share the same version number. This ensures you know exactly what features are available regardless of your language choice. We're committed to language parity - no language is favored over another."

## Questions for Decision

1. **Agree on unified versioning?** (Yes/No)
2. **Release date for v0.31.0?** (Proposed: 2025-12-01)
3. **Should we skip to v0.31.0 or use v0.30.1?** (Recommend v0.31.0 for clean break)
4. **Rust status?** (Mark as experimental or keep supported?)

## Next Steps

1. Get approval on unified versioning strategy
2. Create `VERSION_STATUS.md` documenting current parity
3. Create `scripts/release.sh` automation
4. Bump all versions to v0.31.0
5. Create unified CHANGELOG.md
6. Tag and release v0.31.0
