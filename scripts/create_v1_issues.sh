#!/bin/bash
# create_v1_issues.sh - Create all v1.0 milestones and issues
# Usage: ./scripts/create_v1_issues.sh

set -e

echo "🚀 Creating v1.0.0 milestones and issues for Agenkit"
echo "=================================================="
echo ""

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "❌ Error: GitHub CLI (gh) is not installed"
    echo "   Install from: https://cli.github.com/"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "❌ Error: Not authenticated with GitHub CLI"
    echo "   Run: gh auth login"
    exit 1
fi

echo "✅ GitHub CLI authenticated"
echo ""

# Create Milestones
echo "📅 Creating milestones..."
echo "-------------------------"

gh milestone create "v1.0 - Cross-Language Testing" \
  --due-date "2026-01-06" \
  --description "Verify behavioral parity across all 6 languages with comprehensive equivalence tests" \
  2>/dev/null || echo "⚠️  Milestone 'v1.0 - Cross-Language Testing' already exists"

gh milestone create "v1.0 - Performance Benchmarks" \
  --due-date "2026-01-20" \
  --description "Benchmark all 18 patterns across all 6 languages and create performance comparison matrix" \
  2>/dev/null || echo "⚠️  Milestone 'v1.0 - Performance Benchmarks' already exists"

gh milestone create "v1.0 - Documentation" \
  --due-date "2026-02-03" \
  --description "Complete comprehensive user-facing documentation for v1.0 release" \
  2>/dev/null || echo "⚠️  Milestone 'v1.0 - Documentation' already exists"

gh milestone create "v1.0 - Core Reasoning" \
  --due-date "2026-02-24" \
  --description "Implement core reasoning techniques (CoT, ToT, Self-Consistency) across all 6 languages" \
  2>/dev/null || echo "⚠️  Milestone 'v1.0 - Core Reasoning' already exists"

gh milestone create "v1.0 - WASM Browser Story" \
  --due-date "2026-03-31" \
  --description "Complete browser story with WASM support across Rust, C++, and Zig" \
  2>/dev/null || echo "⚠️  Milestone 'v1.0 - WASM Browser Story' already exists"

gh milestone create "v1.0 - Final Release Prep" \
  --due-date "2026-04-07" \
  --description "Final testing, release notes, migration guides, and conference prep" \
  2>/dev/null || echo "⚠️  Milestone 'v1.0 - Final Release Prep' already exists"

gh milestone create "v1.0.0 Release" \
  --due-date "2026-04-15" \
  --description "Official v1.0.0 release with conference demo" \
  2>/dev/null || echo "⚠️  Milestone 'v1.0.0 Release' already exists"

echo "✅ Milestones created"
echo ""

# Create Issues
echo "📝 Creating issues..."
echo "--------------------"

# Phase 1: Cross-Language Equivalence Testing (Dec 16 - Jan 6)

echo "Creating Phase 1: Cross-Language Testing issues..."

gh issue create --title "Create pattern behavior specifications for cross-language testing" \
  --milestone "v1.0 - Cross-Language Testing" \
  --label "testing,cross-language,v1.0,priority: high" \
  --body "$(cat <<'EOF'
Create YAML/JSON specifications defining expected behavior for all 18 patterns to enable cross-language equivalence testing.

## Acceptance Criteria

- [ ] Create `tests/cross_language/specs/` directory
- [ ] Pattern specifications for all 18 patterns in YAML format
- [ ] Each spec includes:
  - Pattern name
  - Test scenarios (input/output pairs)
  - Expected metadata
  - Edge cases
- [ ] Specification schema documented
- [ ] README explaining spec format

## Estimated Effort

3 days

## Dependencies

None

## Related Documentation

- See [docs/WASM_V1_IMPLEMENTATION_PLAN.md](../docs/WASM_V1_IMPLEMENTATION_PLAN.md) for context
- See [docs/V1_ISSUE_TRACKING_PLAN.md](../docs/V1_ISSUE_TRACKING_PLAN.md) for full tracking plan
EOF
)" 2>/dev/null && echo "✅ Issue #268 created" || echo "⚠️  Issue may already exist"

gh issue create --title "Build test harness for running cross-language equivalence tests" \
  --milestone "v1.0 - Cross-Language Testing" \
  --label "testing,cross-language,v1.0,infrastructure" \
  --body "$(cat <<'EOF'
Create test infrastructure to execute pattern specifications across all 6 languages and verify behavioral equivalence.

## Acceptance Criteria

- [ ] Python test runner reads YAML specs
- [ ] Subprocess execution for Go/Rust/C++/Zig binaries
- [ ] JSON-based communication protocol
- [ ] Test harness binaries for each language:
  - `agenkit-go/tests/cross_language_harness.go`
  - `agenkit-rust/tests/cross_language_harness.rs`
  - `agenkit-cpp/tests/cross_language_harness.cpp`
  - `agenkit-zig/tests/cross_language_harness.zig`
- [ ] Result comparison and reporting
- [ ] CI integration

## Estimated Effort

5 days

## Dependencies

Depends on #268 (pattern specifications)
EOF
)" 2>/dev/null && echo "✅ Issue #269 created" || echo "⚠️  Issue may already exist"

gh issue create --title "Execute and validate cross-language equivalence tests for all patterns" \
  --milestone "v1.0 - Cross-Language Testing" \
  --label "testing,cross-language,v1.0,validation" \
  --body "$(cat <<'EOF'
Run equivalence tests across all 6 languages for all 18 patterns and document any behavioral differences.

## Acceptance Criteria

- [ ] All 18 patterns tested across all 6 languages (108 implementations)
- [ ] Test results documented
- [ ] Any behavioral differences identified and resolved
- [ ] Equivalence report generated
- [ ] CI workflow running cross-language tests

## Estimated Effort

3 days

## Dependencies

Depends on #268, #269
EOF
)" 2>/dev/null && echo "✅ Issue #270 created" || echo "⚠️  Issue may already exist"

# Phase 2: Performance Benchmarks (Jan 6 - Jan 20)

echo "Creating Phase 2: Performance Benchmarks issues..."

gh issue create --title "Create pattern benchmark suite for all 18 patterns" \
  --milestone "v1.0 - Performance Benchmarks" \
  --label "performance,benchmarks,v1.0,priority: high" \
  --body "$(cat <<'EOF'
Create standardized benchmark suite for all 18 patterns with consistent test scenarios across all languages.

## Acceptance Criteria

- [ ] Benchmark scenarios defined for each pattern:
  - Small workload (fast execution)
  - Medium workload (realistic)
  - Large workload (stress test)
- [ ] Benchmark implementations in all 6 languages
- [ ] Consistent measurement methodology
- [ ] JSON output format for results
- [ ] Documentation: `benchmarks/PATTERN_BENCHMARKS.md`

## Estimated Effort

4 days
EOF
)" 2>/dev/null && echo "✅ Issue #271 created" || echo "⚠️  Issue may already exist"

gh issue create --title "Execute performance benchmarks across all 6 languages" \
  --milestone "v1.0 - Performance Benchmarks" \
  --label "performance,benchmarks,v1.0" \
  --body "$(cat <<'EOF'
Run pattern benchmarks across all 6 languages and collect performance data.

## Acceptance Criteria

- [ ] Benchmarks executed on standardized hardware
- [ ] Results for all 18 patterns × 6 languages = 108 data points
- [ ] Raw performance data collected (JSON format)
- [ ] Statistical significance testing (benchstat)
- [ ] Memory usage profiling
- [ ] Reproducible benchmark execution

## Estimated Effort

2 days

## Dependencies

Depends on #271
EOF
)" 2>/dev/null && echo "✅ Issue #272 created" || echo "⚠️  Issue may already exist"

gh issue create --title "Create performance comparison matrix and documentation" \
  --milestone "v1.0 - Performance Benchmarks" \
  --label "performance,benchmarks,v1.0,documentation" \
  --body "$(cat <<'EOF'
Create comprehensive performance comparison documentation with analysis and recommendations.

## Acceptance Criteria

- [ ] Performance comparison matrix (table format)
- [ ] Language-by-language analysis
- [ ] Pattern-by-pattern analysis
- [ ] Performance visualization (charts/graphs)
- [ ] Language selection guidance based on performance
- [ ] Documentation: `docs/PERFORMANCE_COMPARISON.md`
- [ ] Update README with performance data

## Estimated Effort

2 days

## Dependencies

Depends on #272
EOF
)" 2>/dev/null && echo "✅ Issue #273 created" || echo "⚠️  Issue may already exist"

# Phase 3: Documentation (Jan 20 - Feb 3)

echo "Creating Phase 3: Documentation issues..."

gh issue create --title "Create language migration guides" \
  --milestone "v1.0 - Documentation" \
  --label "documentation,v1.0,migration" \
  --body "$(cat <<'EOF'
Create comprehensive migration guides for moving between any language pair (e.g., Python → Go, TypeScript → Rust).

## Acceptance Criteria

- [ ] Migration guides for common transitions:
  - Python → Go (prototype → production)
  - Python → TypeScript (server → full-stack)
  - TypeScript → Rust (web → performance)
  - Go → C++ (cloud → embedded)
- [ ] Each guide includes:
  - Syntax differences
  - Pattern translation
  - Idiom mapping
  - Common pitfalls
  - Example conversions
- [ ] Documentation: `docs/migration/`

## Estimated Effort

2 days
EOF
)" 2>/dev/null && echo "✅ Issue #274 created" || echo "⚠️  Issue may already exist"

gh issue create --title "Generate comprehensive API reference for all 6 languages" \
  --milestone "v1.0 - Documentation" \
  --label "documentation,v1.0,api-reference" \
  --body "$(cat <<'EOF'
Create complete API reference documentation for all patterns, middleware, and utilities across all languages.

## Acceptance Criteria

- [ ] API docs generated from source code
- [ ] Python: Sphinx documentation
- [ ] Go: godoc documentation
- [ ] TypeScript: TypeDoc documentation
- [ ] Rust: rustdoc documentation
- [ ] C++: Doxygen documentation
- [ ] Zig: autodoc documentation
- [ ] Cross-language API comparison table
- [ ] Published to docs site

## Estimated Effort

3 days
EOF
)" 2>/dev/null && echo "✅ Issue #275 created" || echo "⚠️  Issue may already exist"

gh issue create --title "Create interactive examples and tutorials" \
  --milestone "v1.0 - Documentation" \
  --label "documentation,v1.0,examples,tutorials" \
  --body "$(cat <<'EOF'
Create interactive examples and tutorials for common use cases across all languages.

## Acceptance Criteria

- [ ] 5 step-by-step tutorials:
  - "Your First Agent" (beginner)
  - "Building a Multi-Agent System" (intermediate)
  - "Production Deployment" (advanced)
  - "Cross-Language Integration" (advanced)
  - "Browser Agents with WASM" (advanced)
- [ ] Interactive code examples (runnable in browser where possible)
- [ ] Video walkthroughs (optional, can defer)
- [ ] Documentation: `docs/tutorials/`

## Estimated Effort

3 days
EOF
)" 2>/dev/null && echo "✅ Issue #276 created" || echo "⚠️  Issue may already exist"

# Phase 4: Core Reasoning Techniques (Feb 3 - Feb 24)

echo "Creating Phase 4: Core Reasoning Techniques issues..."

gh issue create --title "Implement Chain-of-Thought (CoT) prompting across all 6 languages" \
  --milestone "v1.0 - Core Reasoning" \
  --label "reasoning,v1.0,priority: critical,enhancement" \
  --body "$(cat <<'EOF'
Implement Chain-of-Thought prompting technique to enable step-by-step reasoning in agent responses.

## Acceptance Criteria

- [ ] CoT implementation in all 6 languages:
  - Python: `agenkit/techniques/chain_of_thought.py`
  - Go: `agenkit-go/techniques/chain_of_thought.go`
  - TypeScript: `packages/core/src/techniques/chain-of-thought.ts`
  - Rust: `agenkit-rust/src/techniques/chain_of_thought.rs`
  - C++: `agenkit-cpp/src/techniques/chain_of_thought.cpp`
  - Zig: `agenkit-zig/src/techniques/chain_of_thought.zig`
- [ ] CoTAgent pattern implementation
- [ ] Step extraction and formatting
- [ ] Comprehensive tests (10+ per language)
- [ ] Examples for each language
- [ ] Documentation: `docs/techniques/CHAIN_OF_THOUGHT.md`

## Estimated Effort

5 days
EOF
)" 2>/dev/null && echo "✅ Issue #277 created" || echo "⚠️  Issue may already exist"

gh issue create --title "Implement Tree-of-Thought (ToT) reasoning across all 6 languages" \
  --milestone "v1.0 - Core Reasoning" \
  --label "reasoning,v1.0,priority: critical,enhancement" \
  --body "$(cat <<'EOF'
Implement Tree-of-Thought reasoning technique to enable exploration of multiple reasoning paths.

## Acceptance Criteria

- [ ] ToT implementation in all 6 languages
- [ ] ToTAgent pattern implementation
- [ ] Branch exploration strategies:
  - BFS (breadth-first)
  - DFS (depth-first)
  - Best-first
- [ ] Branch evaluation and pruning
- [ ] Comprehensive tests (10+ per language)
- [ ] Examples for each language
- [ ] Documentation: `docs/techniques/TREE_OF_THOUGHT.md`

## Estimated Effort

6 days
EOF
)" 2>/dev/null && echo "✅ Issue #278 created" || echo "⚠️  Issue may already exist"

gh issue create --title "Implement Self-Consistency decoding across all 6 languages" \
  --milestone "v1.0 - Core Reasoning" \
  --label "reasoning,v1.0,priority: critical,enhancement" \
  --body "$(cat <<'EOF'
Implement Self-Consistency decoding to improve answer quality through multiple sampling and voting.

## Acceptance Criteria

- [ ] Self-Consistency implementation in all 6 languages
- [ ] SelfConsistencyAgent pattern implementation
- [ ] Multiple sampling with temperature control
- [ ] Voting mechanisms:
  - Majority vote
  - Weighted vote
  - Confidence-based vote
- [ ] Comprehensive tests (10+ per language)
- [ ] Examples for each language
- [ ] Documentation: `docs/techniques/SELF_CONSISTENCY.md`

## Estimated Effort

5 days
EOF
)" 2>/dev/null && echo "✅ Issue #279 created" || echo "⚠️  Issue may already exist"

gh issue create --title "Create reasoning techniques integration tests" \
  --milestone "v1.0 - Core Reasoning" \
  --label "reasoning,v1.0,testing,integration" \
  --body "$(cat <<'EOF'
Create integration tests verifying reasoning techniques work correctly across all languages and patterns.

## Acceptance Criteria

- [ ] Integration tests for CoT + existing patterns
- [ ] Integration tests for ToT + existing patterns
- [ ] Integration tests for Self-Consistency + existing patterns
- [ ] Cross-language reasoning equivalence tests
- [ ] Performance benchmarks for reasoning techniques
- [ ] Documentation: `tests/reasoning/README.md`

## Estimated Effort

3 days

## Dependencies

Depends on #277, #278, #279
EOF
)" 2>/dev/null && echo "✅ Issue #280 created" || echo "⚠️  Issue may already exist"

# Phase 5: WASM Browser Story (Feb 24 - Mar 31)

echo "Creating Phase 5: WASM Browser Story issues..."

gh issue create --title "Rust WASM: Replace tokio with wasm-bindgen-futures for browser compatibility" \
  --milestone "v1.0 - WASM Browser Story" \
  --label "wasm,rust,v1.0,priority: critical,bug" \
  --body "$(cat <<'EOF'
Fix 6 broken patterns in Rust WASM by replacing tokio runtime with browser-native wasm-bindgen-futures.

## Acceptance Criteria

- [ ] Replace tokio in 6 broken patterns:
  - Task pattern
  - Planning pattern
  - Multiagent pattern
  - Autonomous pattern
  - Memory Hierarchy pattern
  - Reasoning with Tools pattern
- [ ] Use wasm-bindgen-futures for async operations
- [ ] Replace tokio::spawn with spawn_local
- [ ] Replace tokio::time with gloo_timers
- [ ] All patterns tested in browser (wasm-pack test)
- [ ] Zero compilation errors
- [ ] Documentation: `agenkit-rust/WASM_MIGRATION.md`

## Estimated Effort

5 days (Week 1 of WASM implementation)

## Implementation Plan

See [docs/WASM_V1_IMPLEMENTATION_PLAN.md](../docs/WASM_V1_IMPLEMENTATION_PLAN.md) Phase 1
EOF
)" 2>/dev/null && echo "✅ Issue #281 created" || echo "⚠️  Issue may already exist"

gh issue create --title "Rust WASM: Implement 7 new patterns with WASM-first approach" \
  --milestone "v1.0 - WASM Browser Story" \
  --label "wasm,rust,v1.0,priority: critical,enhancement" \
  --body "$(cat <<'EOF'
Implement 7 new patterns in Rust using wasm-bindgen-futures from the start (no tokio dependency).

## Acceptance Criteria

- [ ] Implement WASM-compatible patterns:
  - RouterAgent
  - FallbackAgent
  - CollaborativeAgent
  - HumanInLoopAgent
  - SupervisorAgent
  - OrchestrationPatterns
  - ReasoningWithToolsAgent
- [ ] Browser-native async using spawn_local
- [ ] Comprehensive browser tests for each pattern
- [ ] Working examples for each pattern
- [ ] All 18 patterns working in WASM ✅

## Estimated Effort

5 days (Week 2 of WASM implementation)

## Dependencies

Depends on #281
EOF
)" 2>/dev/null && echo "✅ Issue #282 created" || echo "⚠️  Issue may already exist"

gh issue create --title "C++ WASM: Compile agenkit-cpp to WASM using Emscripten" \
  --milestone "v1.0 - WASM Browser Story" \
  --label "wasm,cpp,v1.0,priority: critical,enhancement" \
  --body "$(cat <<'EOF'
Set up Emscripten build system and compile all 18 C++ patterns to WebAssembly.

## Acceptance Criteria

- [ ] CMake configuration for Emscripten builds
- [ ] Build script: `agenkit-cpp/scripts/build_wasm.sh`
- [ ] Async pattern adaptations using Emscripten's ASYNCIFY
- [ ] All 18 patterns compiled to WASM
- [ ] JavaScript bindings via Embind
- [ ] Browser test harness
- [ ] Working example: `examples/wasm/cpp_browser_demo.html`
- [ ] Documentation: `agenkit-cpp/WASM.md`

## Estimated Effort

5 days (Week 3 of WASM implementation)

## Implementation Plan

See [docs/WASM_V1_IMPLEMENTATION_PLAN.md](../docs/WASM_V1_IMPLEMENTATION_PLAN.md) Phase 2
EOF
)" 2>/dev/null && echo "✅ Issue #283 created" || echo "⚠️  Issue may already exist"

gh issue create --title "Zig WASM: Implement Zig native WASM build for all 18 patterns" \
  --milestone "v1.0 - WASM Browser Story" \
  --label "wasm,zig,v1.0,priority: critical,enhancement" \
  --body "$(cat <<'EOF'
Leverage Zig's native WASM support to compile all 18 patterns to WebAssembly.

## Acceptance Criteria

- [ ] build.zig configuration for WASM target (wasm32-freestanding)
- [ ] WASM entry point: `agenkit-zig/src/wasm_entry.zig`
- [ ] Export all 18 patterns to JavaScript
- [ ] TypeScript definition generation
- [ ] Browser test harness
- [ ] Working example: `examples/wasm/zig_browser_demo.html`
- [ ] Documentation: `agenkit-zig/WASM.md`
- [ ] Smallest bundle size among 3 languages ✅

## Estimated Effort

5 days (Week 4 of WASM implementation)

## Implementation Plan

See [docs/WASM_V1_IMPLEMENTATION_PLAN.md](../docs/WASM_V1_IMPLEMENTATION_PLAN.md) Phase 2
EOF
)" 2>/dev/null && echo "✅ Issue #284 created" || echo "⚠️  Issue may already exist"

gh issue create --title "NPM Package: Create and publish @agenkit/wasm" \
  --milestone "v1.0 - WASM Browser Story" \
  --label "wasm,npm,v1.0,priority: critical,infrastructure" \
  --body "$(cat <<'EOF'
Create unified NPM package providing consistent API across Rust, C++, and Zig WASM implementations.

## Acceptance Criteria

- [ ] Package structure: `@agenkit/wasm/`
- [ ] TypeScript wrapper providing unified API
- [ ] Language selection: `createAgenkit('rust' | 'cpp' | 'zig')`
- [ ] Pattern loading API
- [ ] Agent creation API
- [ ] Bundle includes all 3 WASM implementations
- [ ] TypeScript definitions
- [ ] Published to NPM registry
- [ ] Documentation: `@agenkit/wasm/README.md`
- [ ] Bundle size: <500KB gzipped total

## Estimated Effort

4 days (Week 5 of WASM implementation)

## Dependencies

Depends on #282, #283, #284

## Implementation Plan

See [docs/WASM_V1_IMPLEMENTATION_PLAN.md](../docs/WASM_V1_IMPLEMENTATION_PLAN.md) Phase 3
EOF
)" 2>/dev/null && echo "✅ Issue #285 created" || echo "⚠️  Issue may already exist"

gh issue create --title "Browser Examples: Create React, Vue, and Svelte integration examples" \
  --milestone "v1.0 - WASM Browser Story" \
  --label "wasm,examples,v1.0,documentation" \
  --body "$(cat <<'EOF'
Create comprehensive browser integration examples demonstrating WASM agents in popular frameworks.

## Acceptance Criteria

- [ ] React example: `examples/react-chat-agent/`
  - Chat interface using ConversationalAgent
  - Pattern selector
  - Language switcher (Rust/C++/Zig)
  - Full TypeScript
- [ ] Vue example: `examples/vue-agent-demo/`
  - Pattern showcase
  - Interactive demos for all 18 patterns
  - Performance comparison
- [ ] Svelte example: `examples/svelte-agent-workflow/`
  - Workflow visualization
  - PlanningAgent demo
  - Step-by-step execution
- [ ] All examples deployable to Vercel/Netlify
- [ ] README for each example

## Estimated Effort

5 days (Week 6 of WASM implementation)

## Dependencies

Depends on #285
EOF
)" 2>/dev/null && echo "✅ Issue #286 created" || echo "⚠️  Issue may already exist"

gh issue create --title "WASM Testing: Implement automated browser testing and CI/CD" \
  --milestone "v1.0 - WASM Browser Story" \
  --label "wasm,testing,ci-cd,v1.0,infrastructure" \
  --body "$(cat <<'EOF'
Set up comprehensive automated testing for WASM implementations across multiple browsers.

## Acceptance Criteria

- [ ] Playwright test suite: `tests/wasm/playwright.config.ts`
- [ ] Browser tests for all 18 patterns (Chrome, Firefox, Safari)
- [ ] Cross-language parity tests (Rust vs C++ vs Zig)
- [ ] Performance benchmarks (WASM vs native)
- [ ] Bundle size tracking
- [ ] CI workflow: `.github/workflows/wasm-tests.yml`
- [ ] Automated NPM publishing on release
- [ ] Documentation: `tests/wasm/README.md`

## Estimated Effort

5 days (Week 7 of WASM implementation)

## Dependencies

Depends on #285, #286
EOF
)" 2>/dev/null && echo "✅ Issue #287 created" || echo "⚠️  Issue may already exist"

# Phase 6: Final Release Prep (Mar 31 - Apr 7)

echo "Creating Phase 6: Final Release Prep issues..."

gh issue create --title "Write comprehensive release notes and changelog for v1.0.0" \
  --milestone "v1.0 - Final Release Prep" \
  --label "documentation,v1.0,release,priority: high" \
  --body "$(cat <<'EOF'
Create detailed release notes and changelog documenting all features, improvements, and breaking changes.

## Acceptance Criteria

- [ ] CHANGELOG.md updated with all v1.0 changes
- [ ] Release notes covering:
  - 6-language parity achievement
  - All 18 patterns
  - WASM browser support
  - Reasoning techniques
  - Performance benchmarks
  - Breaking changes (if any)
  - Migration guides
- [ ] Feature comparison vs other frameworks
- [ ] Upgrade instructions from v0.x

## Estimated Effort

2 days
EOF
)" 2>/dev/null && echo "✅ Issue #288 created" || echo "⚠️  Issue may already exist"

gh issue create --title "Final end-to-end testing across all languages and platforms" \
  --milestone "v1.0 - Final Release Prep" \
  --label "testing,v1.0,release,priority: critical" \
  --body "$(cat <<'EOF'
Comprehensive final testing to ensure v1.0 is production-ready across all languages and platforms.

## Acceptance Criteria

- [ ] All 2,101+ tests passing across all languages
- [ ] Cross-language equivalence tests passing
- [ ] Performance benchmarks validated
- [ ] WASM browser tests passing (Chrome, Firefox, Safari)
- [ ] Docker images tested
- [ ] Kubernetes deployment tested
- [ ] Security audit completed
- [ ] No critical or high-severity bugs
- [ ] Documentation links verified

## Estimated Effort

2 days
EOF
)" 2>/dev/null && echo "✅ Issue #289 created" || echo "⚠️  Issue may already exist"

gh issue create --title "Prepare live demo and presentation for April conference" \
  --milestone "v1.0 - Final Release Prep" \
  --label "demo,v1.0,conference,priority: high" \
  --body "$(cat <<'EOF'
Create polished conference demo showcasing v1.0 capabilities.

## Acceptance Criteria

- [ ] 5-minute live demo script
- [ ] Demo application (browser-based WASM demo)
- [ ] Slides covering:
  - 6-language parity
  - WASM browser support
  - Performance comparison
  - Quick start example
- [ ] Backup recordings (in case of technical issues)
- [ ] Demo repository published
- [ ] Practice runs completed

## Estimated Effort

2 days
EOF
)" 2>/dev/null && echo "✅ Issue #290 created" || echo "⚠️  Issue may already exist"

gh issue create --title "Official v1.0.0 release and public announcement" \
  --milestone "v1.0.0 Release" \
  --label "release,v1.0,announcement,priority: critical" \
  --body "$(cat <<'EOF'
Coordinate v1.0.0 release across all platforms and channels.

## Acceptance Criteria

- [ ] Git tag: v1.0.0
- [ ] GitHub release created with release notes
- [ ] NPM packages published:
  - @agenkit/core (Python via PyPI)
  - @agenkit/wasm (NPM)
- [ ] Go module tagged (v1.0.0)
- [ ] Rust crate published (crates.io)
- [ ] Docker images published
- [ ] Documentation site updated
- [ ] Blog post published
- [ ] Social media announcements (Twitter, LinkedIn, Reddit)
- [ ] Hacker News post
- [ ] Product Hunt launch (optional)
- [ ] Conference presentation delivered

## Estimated Effort

1 day

## Dependencies

All issues #268-#290 must be complete
EOF
)" 2>/dev/null && echo "✅ Issue #291 created" || echo "⚠️  Issue may already exist"

echo ""
echo "=================================================="
echo "✅ v1.0.0 Issue Creation Complete!"
echo "=================================================="
echo ""
echo "Summary:"
echo "- 7 milestones created"
echo "- 24 issues created (#268-#291)"
echo ""
echo "Timeline:"
echo "- Dec 16 - Jan 6:  Cross-Language Testing (3 issues)"
echo "- Jan 6 - Jan 20:  Performance Benchmarks (3 issues)"
echo "- Jan 20 - Feb 3:  Documentation (4 issues)"
echo "- Feb 3 - Feb 24:  Core Reasoning (4 issues)"
echo "- Feb 24 - Mar 31: WASM Browser Story (7 issues)"
echo "- Mar 31 - Apr 7:  Final Release Prep (3 issues)"
echo "- Early April:     v1.0.0 Release (1 issue)"
echo ""
echo "Next steps:"
echo "1. View milestones: gh milestone list"
echo "2. View issues: gh issue list --milestone 'v1.0 - Cross-Language Testing'"
echo "3. Create GitHub Project board for tracking"
echo "4. Begin Phase 1: Cross-Language Testing (Dec 16)"
echo ""
echo "Documentation:"
echo "- Full tracking plan: docs/V1_ISSUE_TRACKING_PLAN.md"
echo "- WASM implementation plan: docs/WASM_V1_IMPLEMENTATION_PLAN.md"
echo "- Updated roadmap: ROADMAP.md"
