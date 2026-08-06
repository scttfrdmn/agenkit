#!/usr/bin/env bash
#
# Assert that every tracked Go file belongs to a Go module, and that every Go
# module in the repo compiles.
#
# WHY THIS GATE EXISTS (#857)
# ===========================
#
# A .go file that is in no module is invisible to every gate we have:
#
#   * `go build ./...` / `go vet ./...` need a module — they cannot even be run.
#   * The #848 build-tag gate greps for `^//go:build ignore` from
#     `working-directory: agenkit-go`, so a file that is both untagged and outside
#     agenkit-go/ is doubly excluded.
#   * `gofmt` is purely syntactic, so the #849 gate happily formatted these files.
#     Formatting a file that cannot compile is not the same as it working.
#
# Seven tracked .go files were in this state. Five of them did not compile:
# fictional imports of a root `github.com/scttfrdmn/agenkit/agenkit-go` package
# that contains no .go files at all, agent types missing the Introspect() that
# #847 added to the interface, and four APIs called with signatures that never
# existed.
#
# The second half of the gate — building every module — is what would have caught
# #851 breaking examples/apps/{code-review-bot,customer-support}: those trees DO
# have a go.mod, but nothing in CI ever built them, so changing
# GRPCServer.Start() to Start(ctx) broke both silently.
#
# Run locally: ./scripts/check-go-modules.sh
set -uo pipefail

cd "$(dirname "$0")/.."

fail=0

# Build outputs go to a scratch directory, never into the tree. A bare
# `go build ./...` writes each main package's executable into the working
# directory, named after the module (so `examples/infrastructure/go` grows a
# 2.8 MB `infrastructure-go`). Running this gate would then dirty the tree with
# exactly the compiled artifacts scripts/check-tracked-artifacts.sh exists to
# keep out, and a subsequent `git add -A` would commit them (#660 is how ~1 GB
# of these got tracked in the first place).
build_out=$(mktemp -d)
trap 'rm -rf "$build_out"' EXIT

# ------------------------------------------------------------------
# Part 1: every tracked *.go file must be inside a module.
# ------------------------------------------------------------------
mapfile -t go_files < <(git ls-files '*.go' | sort)
mapfile -t module_dirs < <(git ls-files '*go.mod' | sed -E 's#(^|/)go\.mod$##' | sort -u)

# Guard against a vacuous pass (#849): an empty file list would make every check
# below trivially true, which reads as success.
if [ "${#go_files[@]}" -lt 100 ]; then
  echo "FAIL: expected >=100 tracked .go files, found ${#go_files[@]} — is this the repo root?"
  exit 1
fi
if [ "${#module_dirs[@]}" -lt 4 ]; then
  echo "FAIL: expected >=4 Go modules, found ${#module_dirs[@]} — the go.mod discovery is broken."
  exit 1
fi

echo "Checking ${#go_files[@]} tracked .go files against ${#module_dirs[@]} modules"

orphans=()
for f in "${go_files[@]}"; do
  dir=$(dirname "$f")
  found=""
  # Walk up to the repo root looking for a go.mod. "." is the root; a go.mod
  # there would be a root module.
  while :; do
    for m in "${module_dirs[@]}"; do
      # module_dirs entries are "" for the repo root, "agenkit-go" etc otherwise.
      if [ "$dir" = "${m:-.}" ]; then
        found=1
        break
      fi
    done
    [ -n "$found" ] && break
    [ "$dir" = "." ] && break
    dir=$(dirname "$dir")
  done

  if [ -z "$found" ]; then
    orphans+=("$f")
  fi
done

if [ "${#orphans[@]}" -gt 0 ]; then
  echo
  echo "FAIL: ${#orphans[@]} tracked .go file(s) are in no Go module, so nothing"
  echo "      compiles them — not go build, not go vet, not the build-tag gate:"
  printf '  %s\n' "${orphans[@]}"
  echo
  echo "Fix: add a go.mod to the tree (with a \`replace\` to ../../agenkit-go for"
  echo "     in-repo examples), or delete the file if it is dead."
  fail=1
else
  echo "OK: every tracked .go file belongs to a module"
fi

# ------------------------------------------------------------------
# Part 2: every module must build and vet.
# ------------------------------------------------------------------
echo
for m in "${module_dirs[@]}"; do
  d="${m:-.}"
  echo "--- building module: $d"
  # -o "$build_out/" keeps executables out of the tree; see the mktemp above.
  if ! (cd "$d" && go build -o "$build_out/" ./... && go vet ./...); then
    echo "FAIL: module $d does not build"
    fail=1
  fi
done

if [ "$fail" -eq 0 ]; then
  echo
  echo "OK: all ${#module_dirs[@]} Go modules build and vet cleanly"
fi

exit "$fail"
