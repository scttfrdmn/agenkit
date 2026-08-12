#!/usr/bin/env bash
# Build every cross-language equivalence-test harness binary at the paths
# tests/cross_language/harness_manager.py's discover_harnesses() expects.
#
# This is deliberately NOT part of `make test` (#763): it requires five
# separate language toolchains (Go, Node, Rust, a C++ compiler + CMake, Zig)
# on top of Python, several minutes of cold-build time (the C++ leg builds
# the whole agenkit-cpp static lib from source), and it produces no signal
# about correctness by itself -- only run_equivalence_tests.py does that,
# and it can take several more minutes across 21 patterns x 101 scenarios x
# 6 languages. See `make test-equivalence`.
#
# Usage:
#   ./scripts/build-cross-language-harnesses.sh          # build all 5
#   ./scripts/build-cross-language-harnesses.sh go rust  # build a subset
#
# Exits non-zero on the first failing build (no `|| true` swallowing --
# a harness that silently fails to build is exactly the #763 failure mode:
# discover_harnesses() would report it "missing" with no explanation of why).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CROSS_LANG_DIR="$REPO_ROOT/tests/cross_language"

# Python has no build step -- harness_python.py runs directly.
ALL_LANGS=(go typescript rust cpp zig)
REQUESTED=("${@:-${ALL_LANGS[@]}}")

for lang in "${REQUESTED[@]}"; do
    case "$lang" in
        go)
            echo "=== Building Go harness ==="
            ( cd "$CROSS_LANG_DIR/harness_go" && GOTOOLCHAIN=auto go build -o harness_go . )
            ;;
        typescript)
            echo "=== Building TypeScript harness ==="
            # Depends on agenkit-ts via `file:../../../agenkit-ts` -- npm
            # links the source tree, so the core must be built first.
            ( cd "$REPO_ROOT/agenkit-ts" && npm ci && npm run build )
            ( cd "$CROSS_LANG_DIR/harness_ts" && npm ci && npm run build )
            ;;
        rust)
            echo "=== Building Rust harness ==="
            # discover_harnesses() expects the binary at this crate's own
            # target/release/, not wherever a global CARGO_TARGET_DIR (set
            # in some developer shells) would redirect it -- override
            # locally so the build lands where discovery looks regardless
            # of environment.
            ( cd "$CROSS_LANG_DIR/harness_rust" \
              && CARGO_TARGET_DIR="$CROSS_LANG_DIR/harness_rust/target" cargo build --release --quiet )
            ;;
        cpp)
            echo "=== Building C++ harness ==="
            # Falls back to building agenkit-cpp from source when no
            # prebuilt libagenkit is present at agenkit-cpp/build/, which is
            # the common case for a fresh checkout -- this is the slowest
            # leg (a full static-lib build), matching the harness-gate CI
            # job's own comment on why cpp gets a longer timeout.
            #
            # If this fails locally with OpenTelemetry template/overload
            # errors, your machine's installed opentelemetry-cpp is likely
            # newer than the version agenkit-cpp/CMakeLists.txt was written
            # against (a known local macOS/Homebrew skew, not a CI issue --
            # CI installs no OTel package and AGENKIT_WITH_OBSERVABILITY
            # auto-disables). Work around it locally with:
            #   cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DAGENKIT_WITH_OBSERVABILITY=OFF
            ( cd "$CROSS_LANG_DIR/harness_cpp" \
              && cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
              && cmake --build build --target harness_cpp -j"$(getconf _NPROCESSORS_ONLN 2>/dev/null || nproc)" )
            ;;
        zig)
            echo "=== Building Zig harness ==="
            ( cd "$CROSS_LANG_DIR/harness_zig" && zig build )
            ;;
        *)
            echo "Unknown language: $lang (expected one of: ${ALL_LANGS[*]})" >&2
            exit 1
            ;;
    esac
done

echo ""
echo "Done. Verify with:"
echo "  uv run python tests/cross_language/run_equivalence_tests.py --health-check-only"
