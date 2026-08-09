#!/bin/bash
set -e

# Master release script for agenkit
# Releases both the monorepo AND the standalone agenkit-go repository
# Usage: ./scripts/release.sh <version> [--skip-go]

VERSION=$1
SKIP_GO=false

# Parse arguments
shift || true
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-go)
            SKIP_GO=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

if [ -z "$VERSION" ]; then
    echo "Error: Version required"
    echo ""
    echo "Usage: $0 <version> [--skip-go]"
    echo ""
    echo "Examples:"
    echo "  $0 v0.10.1                 # Release both monorepo and agenkit-go"
    echo "  $0 v0.10.1 --skip-go       # Release only monorepo"
    echo ""
    exit 1
fi

# Validate version format
if [[ ! "$VERSION" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Error: Version must be in format vX.Y.Z (e.g., v0.10.1)"
    exit 1
fi

# Extract version without 'v' prefix for Python
PYTHON_VERSION="${VERSION#v}"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              Agenkit Release $VERSION                    "
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# 1. Pre-flight checks
echo "📋 Pre-flight checks..."
echo ""

# Check branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "❌ Error: Must be on main branch (currently on $CURRENT_BRANCH)"
    exit 1
fi

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo "❌ Error: Working directory has uncommitted changes"
    git status --short
    exit 1
fi

# Check if tag exists
if git rev-parse "$VERSION" >/dev/null 2>&1; then
    echo "❌ Error: Tag $VERSION already exists"
    exit 1
fi

# Pull latest
echo "   Pulling latest changes..."
git pull origin main

echo "   ✓ All pre-flight checks passed"
echo ""

# 2. Update version numbers
echo "📝 Updating version numbers..."
echo ""

# The root VERSION file is the single source of truth; scripts/version.py
# propagates it to every language manifest and every MCP wire constant.
#
# This used to be a lone `sed -i '' ...` against pyproject.toml, which (a) only
# touched 1 of 17 declarations and (b) is BSD-only syntax that fails on Linux.
# That is how the version came to be declared sixteen ways spanning 0.10.0 to
# v0.87.0 — see #842.
echo "   Setting VERSION to $PYTHON_VERSION and propagating..."
python3 scripts/version.py set "$PYTHON_VERSION"

# Fail loudly rather than tagging a release whose manifests disagree.
if ! python3 scripts/version.py check; then
    echo "❌ Error: version declarations still disagree after sync"
    echo "   A manifest's layout probably changed; update scripts/version.py"
    exit 1
fi

# Commit version bump. `-u` (tracked files only), not `-A`: version.py only
# ever rewrites existing declaration files, so there's no legitimate reason
# for this step to stage an untracked file -- `-A` swept in a 22.8MB stray
# compiled Go binary sitting in the working tree into the v0.91.0 tag.
git add -u
git commit -m "chore(release): Bump version to $VERSION"

echo "   ✓ Version numbers updated"
echo ""

# 3. Run the full local gate. Blocking — a red suite must not be tagged.
#
# This step used to be unreachable code (#863):
#
#     if ! uv run pytest tests/ -v --tb=short 2>&1 | tail -20; then
#
# tests `tail`'s exit status, not pytest's, and `tail` succeeds whenever it can
# read its input — always. So the prompt, the `git reset`, and the `exit 1` below
# could never run, and a release with failing tests printed "✓ Tests completed"
# and went straight on to tag and push. `set -e` does not save this: in a
# pipeline only the last command's status is checked, and pipefail is not set.
#
# Two further gaps closed here: it ran `pytest tests/` (the Python leg only,
# ~1/9th of the gate that CLAUDE.md and docs/RELEASING.md both specify), so
# broken Go/Rust/C++/Zig/C#/Java/Scala could not block a release either — which
# is most of the recent breakage (#857, #851, #831, #829, #811, #817). And it
# prompted interactively, so it could not run unattended.
#
# Redirect to a file and tail the FILE; never pipe the command whose status you
# are testing. (`make test` output is also far too large to read inline.)
echo "🧪 Running the full local gate (make test)..."
echo ""
TEST_LOG="${TMPDIR:-/tmp}/agenkit-release-$PYTHON_VERSION-test.log"
if ! make test > "$TEST_LOG" 2>&1; then
    echo ""
    tail -40 "$TEST_LOG"
    echo ""
    echo "❌ Release aborted: the local gate failed."
    echo "   Full log: $TEST_LOG"
    echo ""
    # Undo the version-bump commit made above. VERSION and the 18 propagated
    # manifests stay modified in the working tree, so fix the tests and re-run;
    # `git checkout -- .` discards the bump if you want a clean slate.
    git reset --soft HEAD~1
    echo "   The version-bump commit was undone. VERSION + manifests remain"
    echo "   staged at $PYTHON_VERSION — re-run this script after fixing."
    exit 1
fi

echo "   ✓ All tests passed"
echo ""

# 3b. The suite must not have modified any tracked file.
#
# `make test` runs `uv run pytest`, and uv self-heals uv.lock on resolve. Because
# the version bump was committed in step 2 and the suite runs here in step 3, a
# generated file rewritten by the suite lands in the working tree *after* the
# commit — so the tag ships the pre-suite content and the tree is left dirty.
#
# That is exactly how the v0.89.0 tag came to contain `version = "0.87.0"` in
# uv.lock while VERSION said 0.89.0, and why `make check-version` could truthfully
# report success (#868). uv.lock is now a tracked declaration in scripts/version.py,
# so the specific case is fixed at the source — but the ordering hazard is general,
# and any future generated artifact would repeat it silently. This makes it loud.
#
# Deliberately placed after the gate, not before: a file the suite regenerates is
# only detectable once the suite has run.
if ! git diff-index --quiet HEAD --; then
    echo "❌ Release aborted: the test suite modified tracked files."
    git status --short
    echo ""
    echo "   These changes are NOT in the tag, because the version-bump commit was"
    echo "   made before the suite ran. A generated file (uv.lock, a lockfile, a"
    echo "   fixture) is regenerated during testing and needs to be either committed"
    echo "   before release or propagated by scripts/version.py — see #868."
    echo ""
    git reset --soft HEAD~1
    echo "   The version-bump commit was undone; nothing was tagged or pushed."
    exit 1
fi

# 4. Create git tag
echo "🏷️  Creating git tag..."
echo ""

# The previous release, for the compare link. This used to be hardcoded to
# v0.10.0, so every tag since has advertised a diff spanning the entire project
# history instead of the release (#865).
PREV_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
if [ -z "$PREV_TAG" ]; then
    echo "❌ Error: no previous tag found; cannot build a compare link"
    exit 1
fi
echo "   Previous release: $PREV_TAG"

# Release notes come from this version's CHANGELOG section, not from boilerplate.
# The notes used to say "See commit history for detailed changes" while a fully
# written CHANGELOG entry sat unused in the repo (#865).
NOTES_FILE="${TMPDIR:-/tmp}/agenkit-release-$PYTHON_VERSION-notes.md"
if ! python3 - "$PYTHON_VERSION" "$NOTES_FILE" <<'EXTRACT'
import re, sys
version, out = sys.argv[1], sys.argv[2]
text = open("CHANGELOG.md").read()
# Match this version's heading through the next `## [` heading.
pattern = rf"^## \[v?{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[)"
m = re.search(pattern, text, re.MULTILINE | re.DOTALL)
if not m:
    sys.exit(f"CHANGELOG.md has no '## [v{version}]' section — add it before releasing")
body = m.group(1).strip()
if len(body) < 50:
    sys.exit(f"the CHANGELOG section for {version} is only {len(body)} chars; it looks empty")
# GitHub rejects a release body over 125000 characters. Leave room for the
# installation preamble and compare-link footer appended below (~600 chars).
if len(body) > 120000:
    sys.exit(
        f"the CHANGELOG section for {version} is {len(body)} chars, over GitHub's "
        "125000-char release-body limit. Summarize it, or publish the detail as a "
        "linked document."
    )
open(out, "w").write(body + "\n")
print(f"   Release notes: {len(body)} chars from CHANGELOG.md")
EXTRACT
then
    echo "❌ Error: could not extract release notes from CHANGELOG.md"
    exit 1
fi

git tag -a "$VERSION" -m "Release $VERSION

This release includes:
- Python SDK (agenkit)
- Go SDK (agenkit-go)
- Cross-language compatibility

**Python Installation:**
\`\`\`bash
pip install agenkit==$PYTHON_VERSION
\`\`\`

**Go Installation:**
\`\`\`bash
go get github.com/scttfrdmn/agenkit-go@$VERSION
\`\`\`

**Full Changelog:** https://github.com/scttfrdmn/agenkit/compare/$PREV_TAG...$VERSION"

echo "   ✓ Tag created: $VERSION"
echo ""

# 5. Push to GitHub
echo "🚀 Pushing to GitHub..."
echo ""

git push origin main
git push origin "$VERSION"

echo "   ✓ Pushed to origin"
echo ""

# 6. Create GitHub Release
echo "📦 Creating GitHub release..."
echo ""

# Prepend installation instructions to the CHANGELOG body extracted above.
RELEASE_BODY="${TMPDIR:-/tmp}/agenkit-release-$PYTHON_VERSION-body.md"
{
    echo "## Installation"
    echo ""
    echo '**Python:**'
    echo '```bash'
    echo "pip install agenkit==$PYTHON_VERSION"
    echo '```'
    echo ""
    echo '**Go:**'
    echo '```bash'
    echo "go get github.com/scttfrdmn/agenkit-go@$VERSION"
    echo '```'
    echo ""
    echo "---"
    echo ""
    cat "$NOTES_FILE"
    echo ""
    echo "---"
    echo ""
    echo "**Full Changelog:** https://github.com/scttfrdmn/agenkit/compare/$PREV_TAG...$VERSION"
} > "$RELEASE_BODY"

gh release create "$VERSION" \
    --title "Agenkit $VERSION" \
    --notes-file "$RELEASE_BODY" \
    --repo scttfrdmn/agenkit

echo "   ✓ GitHub release created"
echo ""

# 7. agenkit-go standalone repository
# The sync-agenkit-go.yml workflow triggers on the tag pushed above and
# automatically syncs the mirror, tags it, and publishes its GitHub release.
# We don't release it from here to avoid a double-release race with CI.
if [ "$SKIP_GO" = false ]; then
    echo "🔧 agenkit-go standalone repository..."
    echo ""
    echo "   The sync-agenkit-go.yml workflow will release the mirror automatically"
    echo "   in response to the $VERSION tag push above."
    echo ""
    echo "   Watch:  gh run watch --repo scttfrdmn/agenkit \\"
    echo "             \$(gh run list --repo scttfrdmn/agenkit \\"
    echo "                 --workflow sync-agenkit-go.yml --limit 1 --json databaseId \\"
    echo "                 --jq '.[0].databaseId')"
    echo ""
    echo "   Fallback (if CI is unavailable):"
    echo "     ./scripts/release-agenkit-go.sh $VERSION"
    echo ""
else
    echo "⏭️  Skipping agenkit-go release (--skip-go flag)"
    echo "    Note: a vX.Y.Z tag still triggers the mirror sync workflow."
    echo ""
fi

# 8. Python package
echo "📦 Python package..."
echo ""
echo "   Publishing to PyPI is automated: .github/workflows/pypi-publish.yml"
echo "   runs on this release being published (via Trusted Publisher OIDC,"
echo "   no manual upload). To retry a failed run: gh workflow run pypi-publish.yml"
echo "   -f tag=$VERSION"
echo ""

# Done!
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                 🎉 Release Complete! 🎉                      "
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "✅ Monorepo released: https://github.com/scttfrdmn/agenkit/releases/tag/$VERSION"
if [ "$SKIP_GO" = false ]; then
    echo "✅ Go SDK released:   https://github.com/scttfrdmn/agenkit-go/releases/tag/$VERSION"
fi
echo ""
echo "📝 Next steps:"
echo "   • Update changelog/release notes if needed"
echo "   • Announce the release"
echo "   • Monitor for issues"
if [ "$SKIP_GO" = false ]; then
    echo "   • Verify: go get github.com/scttfrdmn/agenkit-go@$VERSION"
fi
echo ""
