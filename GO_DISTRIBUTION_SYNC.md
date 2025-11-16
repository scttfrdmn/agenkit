# Go Distribution Repository Sync Process

## Overview

The Go implementation of Agenkit uses a **distribution mirror pattern**:

- **Development**: Happens in `/Users/scttfrdmn/src/agenkit/agenkit-go/` (main repository)
- **Distribution**: Published from https://github.com/scttfrdmn/agenkit-go (separate repository)

This provides Go users with a clean module path (`github.com/scttfrdmn/agenkit-go`) while keeping all language implementations together in the main repository for coordinated development.

## When to Sync

Sync the distribution repository whenever you:

1. Make changes to Go code in `/agenkit-go/`
2. Release a new version (0.9.1, 0.10.0, etc.)
3. Fix critical bugs in Go implementation
4. Update Go dependencies in `go.mod`

## Sync Process

### Step 1: Ensure Main Repo Changes Are Committed

```bash
cd /Users/scttfrdmn/src/agenkit

# Check status
git status

# Commit any pending Go changes
git add agenkit-go/
git commit -m "feat(go): <description of changes>"
git push
```

### Step 2: Copy Latest Go Code

```bash
# Create fresh copy
rm -rf /tmp/agenkit-go
cp -r /Users/scttfrdmn/src/agenkit/agenkit-go/ /tmp/agenkit-go/

# Navigate to copy
cd /tmp/agenkit-go
```

### Step 3: Update Import Paths (If Needed)

If this is the first sync after initial setup, skip this step. Otherwise, verify import paths:

```bash
# Check for any incorrect import paths
grep -r "github.com/scttfrdmn/agenkit/agenkit-go" . --include="*.go"

# Should find nothing. If found, fix with:
find . -name "*.go" -type f -exec sed -i '' 's|github.com/scttfrdmn/agenkit/agenkit-go|github.com/scttfrdmn/agenkit-go|g' {} \;
```

### Step 4: Pull Latest Distribution Repo State

```bash
# Clone or update distribution repo
if [ ! -d "/tmp/agenkit-go-dist" ]; then
    git clone https://github.com/scttfrdmn/agenkit-go.git /tmp/agenkit-go-dist
else
    cd /tmp/agenkit-go-dist
    git pull origin main
fi

cd /tmp/agenkit-go-dist
```

### Step 5: Sync Files

```bash
# Remove old content (except .git)
find . -mindepth 1 -maxdepth 1 ! -name '.git' -exec rm -rf {} +

# Copy new content
cp -r /tmp/agenkit-go/* .
cp -r /tmp/agenkit-go/.* . 2>/dev/null || true

# Check what changed
git status
```

### Step 6: Commit and Push

```bash
# Stage all changes
git add -A

# Commit with descriptive message
git commit -m "sync: Update from main repo - <brief description>

Synced from scttfrdmn/agenkit @ <commit-hash>
Changes: <list key changes>"

# Push to distribution repo
git push origin main
```

### Step 7: Tag New Version (If Applicable)

For version releases:

```bash
# Tag the release
git tag v0.9.1  # Use appropriate version

# Push tag
git push origin v0.9.1
```

### Step 8: Verify Distribution

```bash
# Test that Go module works
cd /tmp/test-import
go mod init test-import
go get github.com/scttfrdmn/agenkit-go@v0.9.1  # Use new version

# Verify it can be imported
cat > main.go << 'EOF'
package main

import (
    "github.com/scttfrdmn/agenkit-go/agenkit"
)

func main() {
    println("Import successful")
}
EOF

go run main.go
```

## Quick Sync Script

For convenience, create a script at `/Users/scttfrdmn/src/agenkit/scripts/sync-go-distribution.sh`:

```bash
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
```

Make it executable:

```bash
chmod +x /Users/scttfrdmn/src/agenkit/scripts/sync-go-distribution.sh
```

## Version Release Workflow

When releasing a new version:

1. **Update version in main repo:**
   ```bash
   cd /Users/scttfrdmn/src/agenkit
   # Update CHANGELOG.md
   git commit -am "chore: Prepare v0.X.Y release"
   git tag v0.X.Y
   git push && git push --tags
   ```

2. **Sync to distribution repo:**
   ```bash
   ./scripts/sync-go-distribution.sh
   ```

3. **Tag distribution repo:**
   ```bash
   cd /tmp/agenkit-go-dist
   git tag v0.X.Y
   git push origin v0.X.Y
   ```

4. **Verify Go module:**
   ```bash
   go list -m github.com/scttfrdmn/agenkit-go@v0.X.Y
   ```

## Automation Opportunities

### GitHub Actions (Future Enhancement)

Create `.github/workflows/sync-go-distribution.yml` in main repo:

```yaml
name: Sync Go Distribution

on:
  push:
    branches: [main]
    paths:
      - 'agenkit-go/**'
  workflow_dispatch:

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Sync to distribution repo
        env:
          DIST_TOKEN: ${{ secrets.GO_DIST_TOKEN }}
        run: |
          git clone https://${DIST_TOKEN}@github.com/scttfrdmn/agenkit-go.git /tmp/dist
          cd /tmp/dist
          rm -rf $(ls -A | grep -v "^\.git$")
          cp -r $GITHUB_WORKSPACE/agenkit-go/* .
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add -A
          git commit -m "sync: Auto-sync from main repo @ ${GITHUB_SHA:0:7}" || exit 0
          git push origin main
```

**Note:** Requires `GO_DIST_TOKEN` secret with write access to distribution repo.

## Troubleshooting

### Issue: Import paths are wrong

**Symptom:** Go imports show `github.com/scttfrdmn/agenkit/agenkit-go` instead of `github.com/scttfrdmn/agenkit-go`

**Fix:**
```bash
cd /tmp/agenkit-go-dist
find . -name "*.go" -type f -exec sed -i '' 's|github.com/scttfrdmn/agenkit/agenkit-go|github.com/scttfrdmn/agenkit-go|g' {} \;
git commit -am "fix: Correct import paths for standalone distribution"
git push
```

### Issue: `go get` fails to find version

**Symptom:** `go get github.com/scttfrdmn/agenkit-go@v0.X.Y` returns "unknown revision"

**Fix:**
```bash
# Verify tag exists
cd /tmp/agenkit-go-dist
git tag -l

# If missing, create it
git tag v0.X.Y
git push origin v0.X.Y

# Wait a few minutes for Go module proxy to update
# Force refresh: https://proxy.golang.org/github.com/scttfrdmn/agenkit-go/@v/list
```

### Issue: Dependency mismatches

**Symptom:** `go.mod` in distribution repo has different dependencies than main repo

**Fix:**
```bash
cd /tmp/agenkit-go-dist
go mod tidy
git commit -am "chore: Update dependencies"
git push
```

## Best Practices

1. **Sync frequently**: After every significant Go change
2. **Test before syncing**: Run Go tests in main repo first
3. **Keep versions aligned**: Use same version tags in both repos
4. **Document changes**: Use descriptive commit messages with main repo commit hash
5. **Verify imports**: Always check that import paths are correct after sync

## Monitoring

Check Go module status:
- **pkg.go.dev**: https://pkg.go.dev/github.com/scttfrdmn/agenkit-go
- **Module proxy**: https://proxy.golang.org/github.com/scttfrdmn/agenkit-go/@v/list
- **GitHub releases**: https://github.com/scttfrdmn/agenkit-go/releases

## Questions?

See also:
- `DISTRIBUTION_CHANNELS.md` - Overall multi-language distribution strategy
- `agenkit-go/README.md` - Go-specific documentation
