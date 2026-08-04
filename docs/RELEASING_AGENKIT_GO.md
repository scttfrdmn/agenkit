# Releasing agenkit-go

This guide covers releasing the Go SDK to the standalone repository.

## Which module path is canonical?

Two module paths resolve, and they are **not** interchangeable. This section is the
single authority; other docs should link here rather than restate it.

| Path | What it is | Can a consumer pin a release? |
|------|-----------|-------------------------------|
| **`github.com/scttfrdmn/agenkit-go`** | the published distribution mirror | **Yes** — `v0.9.0`, `v0.10.1`, `v0.85.0`, `v0.86.0`, `v0.87.0` |
| `github.com/scttfrdmn/agenkit/agenkit-go` | the in-tree module in this monorepo | No — pseudo-versions only |

**`github.com/scttfrdmn/agenkit-go` is the canonical install path**, because it is the
only one a user can pin. The monorepo path has **zero** tagged versions on the proxy:
a nested module needs subdirectory-prefixed tags (`agenkit-go/v0.87.0`), and this repo
publishes bare `vX.Y.Z` tags, which the Go tooling does not associate with a nested
module. `go get github.com/scttfrdmn/agenkit/agenkit-go` therefore succeeds but resolves
to a `v0.0.0-<timestamp>-<hash>` pseudo-version.

### Which path a given file should use

The sync workflow rewrites `github.com/scttfrdmn/agenkit/agenkit-go` →
`github.com/scttfrdmn/agenkit-go` in the `.go`, `.mod` and `.md` files it copies, so:

- **Inside `agenkit-go/`** — use the **monorepo** path. It must compile in-tree, and the
  workflow rewrites it to the mirror path on the way out. Writing the mirror path here
  would break the in-tree build *and* survive the rewrite untouched.
- **In-tree Go code outside `agenkit-go/`** (`examples/apps/*/go/`,
  `tests/cross_language/harness_go/`) — also the **monorepo** path. Each of these
  modules carries a `replace github.com/scttfrdmn/agenkit/agenkit-go => <relative path>`,
  so it builds against the working tree rather than the proxy. That is deliberate: an
  in-tree example should test the code in this commit, not the last release.
- **Prose and docs** (`README.md`, `docs/`, `docs-site/`, migration guides) — use the
  **mirror** path. These files are never synced and carry no `replace`, so whatever they
  say is exactly what the reader will run.

The exception is documentation *about* the monorepo layout — `go.mod`'s own `module`
line, `RELEASING.md`'s proxy-verification commands, or prose contrasting the two paths as
in the table above.

## Release Philosophy

**Syncing is automatic; releases are driven by tags:**
- **Sync** = Automatic. On every push to `main` that touches `agenkit-go/**`, the
  [`sync-agenkit-go.yml`](../.github/workflows/sync-agenkit-go.yml) workflow updates
  the mirror's `main` (so `go get ...@latest` stays current).
- **Release** = Automatic on tag. When a `vX.Y.Z` tag is pushed to the monorepo, the
  same workflow syncs the mirror and creates the matching tag + GitHub release on it.

This means you do **not** run a separate Go release step — releasing the monorepo
(`./scripts/release.sh vX.Y.Z`, which pushes the tag) releases the mirror too.

## When to Release

Release when you have:
- ✅ Completed a feature or significant fix
- ✅ Passed all CI/CD checks
- ✅ Updated documentation
- ✅ Verified standalone repo works

## Release Process

### Option 1: Tag the monorepo (Recommended)

Releasing the monorepo automatically releases the mirror. Push a `vX.Y.Z` tag
(the unified release script does this for you):

```bash
./scripts/release.sh v0.11.0
```

When the tag lands, [`sync-agenkit-go.yml`](../.github/workflows/sync-agenkit-go.yml):
- Syncs `agenkit-go/` into the mirror (transforming import paths)
- Creates the matching `vX.Y.Z` tag on the mirror
- Publishes a GitHub release, making it available via `go get ...@vX.Y.Z`

### Option 2: Manual workflow run

To re-sync `main` without cutting a release, trigger the workflow manually:

1. Go to [Actions → Sync agenkit-go to Standalone Repository](https://github.com/scttfrdmn/agenkit/actions/workflows/sync-agenkit-go.yml)
2. Click "Run workflow" on `main`

### Option 3: Local script (fallback)

If CI is unavailable, run the local equivalents from a clean `main` checkout:

```bash
./scripts/release-agenkit-go.sh v0.11.0 "Release notes here"
```

**What it does:**
1. Validates you're on main with no uncommitted changes
2. Syncs latest code to standalone repo (transforming import paths)
3. Creates annotated tag
4. Creates GitHub release
5. Outputs installation instructions

## Version Numbering

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR** (`v1.0.0` → `v2.0.0`): Breaking API changes
- **MINOR** (`v0.10.0` → `v0.11.0`): New features, backwards compatible
- **PATCH** (`v0.10.0` → `v0.10.1`): Bug fixes, backwards compatible

### Pre-releases

For alpha/beta releases:
```bash
./scripts/release-agenkit-go.sh v0.11.0-alpha.1 "Alpha release"
./scripts/release-agenkit-go.sh v0.11.0-beta.1 "Beta release"
./scripts/release-agenkit-go.sh v0.11.0-rc.1 "Release candidate"
```

## Release Checklist

Before releasing:

- [ ] All CI/CD checks passing
- [ ] Code synced to standalone repo
- [ ] go.mod version is correct
- [ ] Documentation updated
- [ ] CHANGELOG updated (if exists)
- [ ] Breaking changes documented
- [ ] Migration guide written (if needed)

After releasing:

- [ ] Verify tag exists: https://github.com/scttfrdmn/agenkit-go/tags
- [ ] Verify release exists: https://github.com/scttfrdmn/agenkit-go/releases
- [ ] Test installation: `go get github.com/scttfrdmn/agenkit-go@vX.Y.Z`
- [ ] Update any dependent projects
- [ ] Announce release (if appropriate)

## Example Release Notes

```markdown
## What's Changed

### Features
- Add comprehensive linting and idiomatic code fixes
- Improve error handling across all packages
- Add CLAUDE.md with coding guidelines

### Bug Fixes
- Fix errcheck issues with proper error handling
- Fix printf format errors with time.Duration
- Remove unnecessary nil checks

### Documentation
- Add sync infrastructure documentation
- Improve code examples with production patterns

**Installation:**
\`\`\`bash
go get github.com/scttfrdmn/agenkit-go@v0.10.1
\`\`\`

**Full Changelog:** https://github.com/scttfrdmn/agenkit/compare/v0.10.0...v0.10.1
```

## Troubleshooting

### "Tag already exists"

The tag exists in standalone repo. Either:
- Use a new version number
- Delete the existing tag: `git push --delete origin vX.Y.Z`

### "Not on main branch"

Checkout main first:
```bash
git checkout main
git pull origin main
```

### "Uncommitted changes"

Commit or stash your changes:
```bash
git status
git add -A && git commit -m "Your message"
# or
git stash
```

### Release failed but tag was created

Delete the tag and try again:
```bash
# In standalone repo
git push --delete origin vX.Y.Z
git tag -d vX.Y.Z
```

## Go Module Best Practices

### Version Tags

Go modules use git tags for versioning:
```bash
go get github.com/scttfrdmn/agenkit-go@v0.10.1  # Specific version
go get github.com/scttfrdmn/agenkit-go@latest   # Latest release
```

### Breaking Changes

If you make breaking changes:
1. Bump MAJOR version (v1.x.x → v2.0.0)
2. Update module path in go.mod:
   ```
   module github.com/scttfrdmn/agenkit-go/v2
   ```
3. Update all import paths in code
4. Document migration guide

## Release Frequency

**Recommended:**
- Patch releases: As needed for bug fixes
- Minor releases: Every 2-4 weeks for new features
- Major releases: When breaking changes are necessary

**Balance:**
- Don't release too often (users can't keep up)
- Don't wait too long (fixes don't reach users)
- Follow monorepo release cadence when appropriate
