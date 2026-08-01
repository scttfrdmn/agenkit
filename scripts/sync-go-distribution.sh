#!/bin/bash
set -e

MAIN_REPO="/Users/scttfrdmn/src/agenkit"
DIST_REPO="/tmp/agenkit-go-dist"

echo "🔄 Syncing Go distribution repository..."

# Get current commit hash from main repo
cd "$MAIN_REPO"
COMMIT_HASH=$(git rev-parse --short HEAD)

# Update distribution repo
echo "📤 Updating distribution repository..."
if [ ! -d "$DIST_REPO" ]; then
    git clone https://github.com/scttfrdmn/agenkit-go.git "$DIST_REPO"
fi

cd "$DIST_REPO"
git pull origin main

# Remove old content, keep .git
find . -mindepth 1 -maxdepth 1 ! -name '.git' -exec rm -rf {} +

# Copy new content.
#
# `git archive` rather than `cp -r`: cp copies the *working tree*, which includes
# every gitignored build artifact sitting in agenkit-go/ — compiled example
# binaries, coverage.out, and so on. .gitignore does not protect the mirror,
# because the mirror has its own, so the `git add -A` below would commit them.
# That is how ~50 MB of dead binaries reached the mirror and pushed its module
# zip to 37.5 MB (#660). Exporting from HEAD makes it structurally impossible:
# only tracked files exist to copy. It also drops the previous staging directory
# and its two-step `cp -r .../*` + `cp -r .../.*`, where the second glob matched
# `.` and `..` and had to be silenced with `|| true`.
echo "📦 Exporting tracked Go source from HEAD..."
git -C "$MAIN_REPO" archive HEAD:agenkit-go | tar -x -C .

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
read -r -p "Enter commit message (or 'skip' to abort): " COMMIT_MSG

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
