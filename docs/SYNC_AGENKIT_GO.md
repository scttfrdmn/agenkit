# Syncing agenkit-go to Standalone Repository

The `agenkit-go` directory is developed in the main monorepo but also distributed as a standalone repository at https://github.com/scttfrdmn/agenkit-go.

## Why Two Repositories?

- **Monorepo** (`github.com/scttfrdmn/agenkit/agenkit-go`): Development happens here
- **Standalone** (`github.com/scttfrdmn/agenkit-go`): Distribution for Go users who only want the Go SDK

## Import Path Transformation

The sync process transforms import paths:

```go
// Monorepo uses:
import "github.com/scttfrdmn/agenkit/agenkit-go/agenkit"

// Standalone uses:
import "github.com/scttfrdmn/agenkit-go/agenkit"
```

## Automated Sync (Recommended)

A GitHub Actions workflow automatically syncs changes on every push to `main`:

**Setup:**
1. Create a Personal Access Token with `repo` scope
2. Add it as a repository secret named `AGENKIT_GO_TOKEN`
3. Workflow runs automatically on push to `agenkit-go/**`

**Workflow:** `.github/workflows/sync-agenkit-go.yml`

## Manual Sync

If you need to sync manually:

```bash
./scripts/sync-agenkit-go.sh
```

**What it does:**
1. Splits the `agenkit-go` subtree from the monorepo
2. Transforms import paths for standalone distribution
3. Force pushes to the standalone repository

## Troubleshooting

### "Updates were rejected because the remote contains work"

This happens when the standalone repo has commits not in the monorepo. This is expected because of import path transformations.

**Solution:** Use the sync script, which handles this with force push.

### Import paths not working in standalone repo

Check that the transformation happened:
```bash
# In standalone repo, should see:
grep "github.com/scttfrdmn/agenkit-go" go.mod
# NOT:
grep "github.com/scttfrdmn/agenkit/agenkit-go" go.mod
```

## Development Workflow

1. **Make changes** in the monorepo (`agenkit-go/` directory)
2. **Test locally** with monorepo import paths
3. **Commit and push** to main branch
4. **Automated sync** runs and updates standalone repo
5. **Verify** standalone repo has correct import paths

## DO NOT

- ❌ Make changes directly in the standalone repository
- ❌ Manually sync without import path transformation
- ❌ Use `git subtree push` directly (doesn't handle import paths)

## DO

- ✅ Always develop in the monorepo
- ✅ Use the sync script or automated workflow
- ✅ Verify import paths after sync
- ✅ Test standalone repo works after major changes
