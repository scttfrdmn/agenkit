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

# Commit version bump
git add -A
git commit -m "chore(release): Bump version to $VERSION"

echo "   ✓ Version numbers updated"
echo ""

# 3. Run tests (optional but recommended)
echo "🧪 Running tests..."
echo ""
if command -v uv &> /dev/null; then
    echo "   Running Python tests..."
    if ! uv run pytest tests/ -v --tb=short 2>&1 | tail -20; then
        echo "   ⚠️  Some tests failed - continue anyway? (y/N)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            echo "   Aborting release"
            git reset --soft HEAD~1
            exit 1
        fi
    fi
fi

echo "   ✓ Tests completed"
echo ""

# 4. Create git tag
echo "🏷️  Creating git tag..."
echo ""

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

**Full Changelog:** https://github.com/scttfrdmn/agenkit/compare/v0.10.0...$VERSION"

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

gh release create "$VERSION" \
    --title "Agenkit $VERSION" \
    --notes "Release $VERSION

## Installation

**Python:**
\`\`\`bash
pip install agenkit==$PYTHON_VERSION
\`\`\`

**Go:**
\`\`\`bash
go get github.com/scttfrdmn/agenkit-go@$VERSION
\`\`\`

## What's Included

- ✅ Python SDK (agenkit)
- ✅ Go SDK (agenkit-go)
- ✅ Cross-language compatibility
- ✅ All transports (HTTP, gRPC, WebSocket)
- ✅ Middleware & composition patterns

See commit history for detailed changes." \
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

# 8. Build and publish Python package (optional)
echo "📦 Python package..."
echo ""
echo "   To publish to PyPI:"
echo "   1. Build: python -m build"
echo "   2. Publish: python -m twine upload dist/*"
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
