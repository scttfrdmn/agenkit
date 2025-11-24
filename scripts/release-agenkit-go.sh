#!/bin/bash
set -e

# Release agenkit-go to standalone repository
# Usage: ./scripts/release-agenkit-go.sh v0.10.0 "Release notes here"

VERSION=$1
RELEASE_NOTES=$2

if [ -z "$VERSION" ]; then
    echo "Error: Version required"
    echo "Usage: $0 <version> [release_notes]"
    echo "Example: $0 v0.10.0 'Go SDK release with lint fixes'"
    exit 1
fi

# Validate version format
if [[ ! "$VERSION" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Error: Version must be in format vX.Y.Z (e.g., v0.10.0)"
    exit 1
fi

echo "=== Releasing agenkit-go $VERSION ==="

# 1. Ensure we're on main and up to date
echo "Checking branch and status..."
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "Error: Must be on main branch (currently on $CURRENT_BRANCH)"
    exit 1
fi

if ! git diff-index --quiet HEAD --; then
    echo "Error: Working directory has uncommitted changes"
    exit 1
fi

echo "Pulling latest changes..."
git pull origin main

# 2. Sync to standalone repo (this will push latest code)
echo "Syncing to standalone repository..."
./scripts/sync-agenkit-go.sh

# 3. Tag and release on standalone repo
echo "Creating release on standalone repository..."
cd "$(mktemp -d)"
git clone https://github.com/scttfrdmn/agenkit-go.git .
git checkout main

# Create annotated tag
if [ -z "$RELEASE_NOTES" ]; then
    RELEASE_NOTES="agenkit-go $VERSION

This release contains the Go SDK from the agenkit monorepo.

**Installation:**
\`\`\`bash
go get github.com/scttfrdmn/agenkit-go@$VERSION
\`\`\`

**Full Changelog:** https://github.com/scttfrdmn/agenkit/releases/tag/$VERSION"
fi

git tag -a "$VERSION" -m "$RELEASE_NOTES"
git push origin "$VERSION"

# Create GitHub release
gh release create "$VERSION" \
    --repo scttfrdmn/agenkit-go \
    --title "agenkit-go $VERSION" \
    --notes "$RELEASE_NOTES"

cd -

echo "✓ Release complete!"
echo ""
echo "Standalone repository: https://github.com/scttfrdmn/agenkit-go/releases/tag/$VERSION"
echo ""
echo "Users can install with:"
echo "  go get github.com/scttfrdmn/agenkit-go@$VERSION"
