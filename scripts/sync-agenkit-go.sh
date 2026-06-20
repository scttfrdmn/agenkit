#!/bin/bash
set -e

# Sync agenkit-go subdirectory to standalone repository
# This script handles module path transformation for the standalone repo

echo "Syncing agenkit-go to standalone repository..."

# 1. Create a temporary branch with the subtree
echo "Creating subtree split..."
SPLIT_COMMIT=$(git subtree split --prefix=agenkit-go HEAD)

# 2. Create a temporary directory
TEMP_DIR=$(mktemp -d)
echo "Using temporary directory: $TEMP_DIR"

# 3. Clone the split into temp directory
git clone . "$TEMP_DIR" --branch main --single-branch
cd "$TEMP_DIR"
git checkout "$SPLIT_COMMIT"

# 4. Transform import paths for standalone repository (.go, go.mod, and .md docs)
echo "Transforming import paths..."
grep -rl 'github.com/scttfrdmn/agenkit/agenkit-go' . \
  --include='*.go' --include='*.mod' --include='*.md' \
  | xargs -r sed -i '' 's|github.com/scttfrdmn/agenkit/agenkit-go|github.com/scttfrdmn/agenkit-go|g'

# 5. Verify no stale references remain
if grep -rq 'github.com/scttfrdmn/agenkit/agenkit-go' . --include='*.go' --include='*.mod' --include='*.md'; then
  echo "Error: stale references to monorepo path remain after transform"
  grep -rl 'github.com/scttfrdmn/agenkit/agenkit-go' . --include='*.go' --include='*.mod' --include='*.md'
  exit 1
fi

# 6. Commit the transformation
git add -A
git commit -m "chore: Transform import paths for standalone repository" || true

# 7. Force push to standalone repo
echo "Pushing to standalone repository..."
git push --force https://github.com/scttfrdmn/agenkit-go HEAD:main

# 8. Cleanup
cd -
rm -rf "$TEMP_DIR"

echo "✓ Sync complete!"
echo "Standalone repository updated at: https://github.com/scttfrdmn/agenkit-go"
