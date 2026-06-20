#!/bin/bash
set -e

MAIN_REPO="/Users/scttfrdmn/src/agenkit"
DIST_REPO="/tmp/agenkit-go-dist"
TEMP_COPY="/tmp/agenkit-go-sync"

echo "🔄 Syncing Go distribution repository..."

# Get current commit hash from main repo
cd "$MAIN_REPO"
COMMIT_HASH=$(git rev-parse --short HEAD)

# Create fresh copy
echo "📦 Creating fresh copy of Go code..."
rm -rf "$TEMP_COPY"
cp -r "$MAIN_REPO/agenkit-go" "$TEMP_COPY"

# Update distribution repo
echo "📤 Updating distribution repository..."
if [ ! -d "$DIST_REPO" ]; then
    git clone https://github.com/scttfrdmn/agenkit-go.git "$DIST_REPO"
fi

cd "$DIST_REPO"
git pull origin main

# Remove old content, keep .git
find . -mindepth 1 -maxdepth 1 ! -name '.git' -exec rm -rf {} +

# Copy new content
cp -r "$TEMP_COPY"/* .
cp -r "$TEMP_COPY"/.* . 2>/dev/null || true

# Transform import paths for the standalone repository (.go, go.mod, .md docs).
# Without this the mirror ships the monorepo path and `go get` breaks.
echo "🔧 Transforming import paths..."
grep -rl 'github.com/scttfrdmn/agenkit/agenkit-go' . \
  --include='*.go' --include='*.mod' --include='*.md' \
  | xargs -r sed -i '' 's|github.com/scttfrdmn/agenkit/agenkit-go|github.com/scttfrdmn/agenkit-go|g'

if grep -rq 'github.com/scttfrdmn/agenkit/agenkit-go' . --include='*.go' --include='*.mod' --include='*.md'; then
    echo "❌ Stale references to monorepo path remain after transform"
    grep -rl 'github.com/scttfrdmn/agenkit/agenkit-go' . --include='*.go' --include='*.mod' --include='*.md'
    exit 1
fi

# Show changes
echo "📊 Changes to be synced:"
git status --short

# Prompt for commit
echo ""
read -p "Enter commit message (or 'skip' to abort): " COMMIT_MSG

if [ "$COMMIT_MSG" = "skip" ]; then
    echo "❌ Sync aborted"
    exit 0
fi

# Commit and push
git add -A
git commit -m "sync: $COMMIT_MSG

Synced from scttfrdmn/agenkit @ $COMMIT_HASH"
git push origin main

echo "✅ Sync complete!"
echo ""
echo "To create a new release tag:"
echo "  cd $DIST_REPO"
echo "  git tag v0.X.Y"
echo "  git push origin v0.X.Y"
