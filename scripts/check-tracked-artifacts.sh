#!/usr/bin/env bash
#
# Fail if the tracked tree contains build artifacts.
#
# Between v0.82.0 and v0.85.0 this repo tracked ~1 GB of compiled binaries —
# 20 MB Go example executables, Rust incremental-compilation caches, Zig object
# files. That pushed the Go module zip past the proxy's ceiling and made
# `github.com/scttfrdmn/agenkit/agenkit-go` un-`go get`-able (#660). They were
# removed by hand in v0.86.0, which dropped the repo to 48.9 MB, but nothing
# stopped them coming back. This is that guard.
#
# Two independent checks, because either alone has a blind spot:
#
#   1. Compiled object/executable formats, detected by content via `file(1)`.
#      Catches the actual problem regardless of filename — the offenders were
#      named `main`, `websocket`, `router_pattern`, with no extension to match.
#   2. A size ceiling. Catches large non-executable artifacts (dep-graph.bin,
#      *.rlib on a host where file(1) reports plain data, vendored archives).
#
# Usage:
#   scripts/check-tracked-artifacts.sh            # check HEAD
#   MAX_TRACKED_FILE_MB=2 scripts/...            # tighter ceiling
#
# Exits 0 when clean, 1 with a report otherwise.

set -euo pipefail

# 4 MB. The largest legitimate tracked file today is uv.lock at ~0.55 MB, so
# this leaves real headroom for generated reports and lockfiles while still
# catching the class of thing that caused #660 (the smallest offender there
# was 3.0 MB). tests/cross_language/equivalence_report.json was the previous
# largest (0.90 MB) until #763 gitignored it -- a committed result nothing
# regenerated stayed "accurate" for 6.5 months.
MAX_MB="${MAX_TRACKED_FILE_MB:-4}"
max_bytes=$((MAX_MB * 1024 * 1024))

# Paths exempt from the *executable* check only — never from the size check.
# .wasm is a legitimate build output that this repo publishes on purpose:
# packages/wasm ships prebuilt modules to npm, and the browser examples copy
# them at build time. file(1) reports them as WebAssembly binaries.
is_allowed_binary() {
  case "$1" in
    *.wasm) return 0 ;;
    *) return 1 ;;
  esac
}

failures=0

echo "==> Checking tracked files for compiled artifacts"

# Content-based detection. `file --mime-type` is used rather than a name
# pattern because the #660 binaries had no extensions. Object files
# (application/x-object) count too: agenkit-zig/.zig-cache/*.o was tracked.
while IFS= read -r path; do
  [ -n "$path" ] || continue
  is_allowed_binary "$path" && continue
  printf '  ✗ %s\n' "$path"
  failures=$((failures + 1))
done < <(
  git ls-files -z |
    xargs -0 file --mime-type --separator '|' 2>/dev/null |
    awk -F'\\|' '
      {
        type = $NF
        sub(/^[ \t]+/, "", type)
        # Reconstruct the path: file(1) prints "path|type", and a path may itself
        # contain the separator, so take everything before the final field.
        path = $1
        for (i = 2; i < NF; i++) path = path "|" $i
        if (type ~ /^application\/x-(mach-binary|executable|pie-executable|sharedlib|object|archive)$/)
          print path
      }
    '
)

if [ "$failures" -eq 0 ]; then
  echo "    no compiled executables or object files tracked"
fi

echo "==> Checking tracked file sizes (ceiling ${MAX_MB} MB)"

oversize=0
while IFS=$'\t' read -r size path; do
  [ -n "${path:-}" ] || continue
  printf '  ✗ %s (%.1f MB)\n' "$path" "$(awk -v s="$size" 'BEGIN{print s/1048576}')"
  oversize=$((oversize + 1))
done < <(
  git ls-tree -r -l HEAD |
    awk -v max="$max_bytes" '$4 != "-" && $4+0 > max { size=$4; $1=$2=$3=$4=""; sub(/^ +/, ""); print size "\t" $0 }'
)

if [ "$oversize" -eq 0 ]; then
  echo "    no tracked file exceeds ${MAX_MB} MB"
fi

total=$((failures + oversize))
if [ "$total" -gt 0 ]; then
  cat <<EOF

FAILED: $total tracked path(s) look like build artifacts.

Build outputs must not be committed — they bloat every clone and, for the Go
module, can push the published zip past the module proxy's 500 MB ceiling (#660).

To fix:
  git rm --cached <path>          # untrack, keep the local file
  # then add the path to .gitignore

If a file is a legitimate committed artifact (as packages/wasm/wasm/*.wasm is),
add it to is_allowed_binary() in this script with a comment explaining why, or
raise MAX_TRACKED_FILE_MB.
EOF
  exit 1
fi

echo
echo "OK: tracked tree is source-only."
