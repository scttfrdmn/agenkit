#!/usr/bin/env bash
#
# Assert that scripts/release.sh actually aborts when the test gate fails.
#
# WHY THIS GATE EXISTS (#863)
# ===========================
#
# release.sh's test step was unreachable code for its entire life:
#
#     if ! uv run pytest tests/ -v --tb=short 2>&1 | tail -20; then
#         ... prompt, git reset --soft HEAD~1, exit 1 ...
#     fi
#
# That condition tests `tail`'s exit status, not pytest's, and `tail` succeeds
# whenever it can read its input — always. So a release with a red suite printed
# "✓ Tests completed" and went on to tag and push. `set -e` does not help: in a
# pipeline only the last command's status is checked, and pipefail is not set.
#
# The lesson from #849 and #857 is that a check nobody verified is not a check.
# So this does not merely grep for the bad pattern — it RUNS release.sh against a
# `make` stub that fails, and asserts the release actually stops. Pattern-matching
# alone would not have caught the original, which looked entirely plausible.
#
# Run locally: ./scripts/check-release-gate.sh
set -uo pipefail

cd "$(dirname "$0")/.."
repo_root=$(pwd)

fail=0

# ------------------------------------------------------------------
# Part 1: no `if ! <cmd> | ...` anywhere in the release scripts.
# ------------------------------------------------------------------
# The exact construct that made #863 unreachable. A redirect (`> /dev/null`) is
# fine and deliberately not matched — only a pipe reassigns which command's exit
# status the `if` sees.
echo "==> Checking release scripts for status-swallowing pipes"

release_scripts=(scripts/release.sh scripts/release-agenkit-go.sh)
for s in "${release_scripts[@]}"; do
  [ -f "$s" ] || continue
  # Match `if ! something | something`, ignoring commented-out lines (the #863
  # postmortem in release.sh quotes the original defect on purpose).
  if grep -nE '^[[:space:]]*if[[:space:]]+!.*[^|]\|[^|]' "$s" | grep -v '^\s*[0-9]*:\s*#'; then
    echo "FAIL: $s tests the exit status of a pipe, not of the command."
    echo "      \`if ! cmd | tail\` checks tail, which always succeeds. Redirect to"
    echo "      a file and tail the file instead. This is #863."
    fail=1
  fi
done
[ "$fail" -eq 0 ] && echo "    no status-swallowing pipes in ${#release_scripts[@]} release script(s)"

# ------------------------------------------------------------------
# Part 2: release.sh aborts when the gate fails, and creates no tag.
# ------------------------------------------------------------------
# Behavioural, not textual. A stub `make` that exits non-zero stands in for a red
# suite; release.sh must exit non-zero and must not tag.
echo
echo "==> Verifying release.sh aborts on a failing gate"

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

# A throwaway clone, so the assertion cannot touch the real repo's tags, commits,
# or remotes. --no-hardlinks keeps the object stores independent.
if ! git clone --quiet --no-hardlinks --no-tags "$repo_root" "$work/repo" 2>"$work/clone.err"; then
  echo "FAIL: could not clone the repo to test the release gate:"
  cat "$work/clone.err"
  exit 1
fi

cd "$work/repo"
git remote remove origin 2>/dev/null || true

# A local identity for the clone, because release.sh makes its own version-bump
# commit and a CI runner has no global user.name/user.email — `git commit` then
# fails with "empty ident name", release.sh aborts under `set -e` before reaching
# the gate, and the probe proves nothing. This passed locally (where a global
# identity exists) and failed on ubuntu-latest; the "did the probe reach the gate"
# assertion below is what surfaced it rather than a false pass. Signing off too:
# the runner has no key, and a signature is irrelevant to a throwaway clone.
git config user.email "release-gate-probe@localhost"
git config user.name "release gate probe"
git config commit.gpgsign false
git config tag.gpgsign false

# Overlay the WORKING TREE's scripts/ onto the clone. `git clone` copies HEAD, so
# without this the probe exercises the committed release.sh rather than the one
# under review — a fix would appear to fail and a regression would appear to pass,
# both silently. Caught during this check's own negative verification, when the
# probe ran HEAD's `uv run pytest` (2209 tests, 4 minutes) instead of the stub.
cp -R "$repo_root/scripts/." "$work/repo/scripts/"

# ...and commit it in the clone. release.sh's second preflight rejects a dirty
# tree, so an uncommitted overlay aborts the probe before the step under test.
git add -A scripts/ >/dev/null 2>&1 || true
git commit --quiet -m "probe: overlay working-tree scripts" >/dev/null 2>&1 || true

# release.sh's first preflight rejects any branch but main. The clone checks out
# whatever branch the source repo is on, so without this the probe run dies at
# that preflight and never reaches the step under test — while still exiting 1,
# which reads as a pass. That is the vacuous-gate trap from #849 and it caught
# this check during its own negative verification. Assertions below therefore
# confirm the gate step actually RAN, not merely that the exit code was non-zero.
git checkout --quiet -B main

# Stub `make` (fails, standing in for a red suite) and `uv`/`python3` passthroughs
# are unnecessary — release.sh reaches `make test` before anything network-bound.
mkdir -p "$work/bin"
cat > "$work/bin/make" <<'STUB'
#!/usr/bin/env bash
echo "stub make: pretending the suite is red" >&2
exit 1
STUB
chmod +x "$work/bin/make"

# `git pull origin main` in the preflight has no origin now, and `set -e` would
# abort there rather than at the step under test — which would pass this check
# for the wrong reason. Stub git's pull subcommand only.
cat > "$work/bin/git" <<STUB
#!/usr/bin/env bash
if [ "\${1:-}" = "pull" ]; then exit 0; fi
exec /usr/bin/git "\$@"
STUB
chmod +x "$work/bin/git"

# A version that cannot already be tagged, so the preflight tag check passes.
probe_version="v99.99.99"

set +e
PATH="$work/bin:$PATH" ./scripts/release.sh "$probe_version" --skip-go \
  > "$work/out.log" 2>&1
rc=$?
set -e

# Prove the probe reached the step under test. Without this, an abort in an
# earlier preflight (wrong branch, dirty tree, existing tag) exits non-zero and
# masquerades as the gate working. This assertion is why the check is not vacuous.
if ! grep -q 'Running the full local gate' "$work/out.log"; then
  echo "FAIL: the probe run never reached the test gate, so this check proved nothing."
  echo "      release.sh aborted earlier — its last 20 lines:"
  tail -20 "$work/out.log" | sed 's/^/      /'
  exit 1
fi
if ! grep -q 'stub make' "$work/out.log"; then
  echo "FAIL: the stub \`make\` was never invoked, so the gate step did not run the suite."
  tail -20 "$work/out.log" | sed 's/^/      /'
  exit 1
fi

if [ "$rc" -eq 0 ]; then
  echo "FAIL: release.sh exited 0 with a failing test gate — a red suite can be released."
  echo "      Last 20 lines of its output:"
  tail -20 "$work/out.log" | sed 's/^/      /'
  fail=1
elif /usr/bin/git rev-parse "$probe_version" >/dev/null 2>&1; then
  echo "FAIL: release.sh created tag $probe_version despite the gate failing."
  fail=1
else
  echo "    release.sh exited $rc and created no tag"
fi

# The abort path must also undo its own version-bump commit, or a re-run starts
# from a dirty tree and the preflight rejects it — a release that cannot be retried.
if /usr/bin/git log -1 --format=%s | grep -q 'chore(release): Bump version'; then
  echo "FAIL: the version-bump commit survived the abort; a re-run will hit the"
  echo "      'uncommitted changes' preflight and cannot proceed."
  fail=1
else
  echo "    the version-bump commit was rolled back"
fi

cd "$repo_root"

if [ "$fail" -eq 0 ]; then
  echo
  echo "OK: the release gate blocks a failing test suite."
fi

exit "$fail"
