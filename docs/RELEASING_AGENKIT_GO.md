# Releasing agenkit-go

This guide covers releasing the Go SDK to the standalone repository.

## Release Philosophy

**Releases are separate from code syncing:**
- **Sync** = Automatic, happens on every push to `agenkit-go/**`
- **Release** = Manual, happens when you want to cut a versioned release

This separation provides flexibility:
- Test changes in standalone repo before releasing
- Release on your schedule, not tied to every commit
- Write proper release notes
- Follow semantic versioning

## When to Release

Release when you have:
- ✅ Completed a feature or significant fix
- ✅ Passed all CI/CD checks
- ✅ Updated documentation
- ✅ Verified standalone repo works

## Release Process

### Option 1: GitHub Actions (Recommended)

1. Go to [Actions → Release agenkit-go](https://github.com/scttfrdmn/agenkit/actions/workflows/release-agenkit-go.yml)
2. Click "Run workflow"
3. Enter version (e.g., `v0.10.1`)
4. Optionally add release notes
5. Click "Run workflow"

The workflow will:
- Validate version format
- Sync latest code to standalone repo
- Create tag and GitHub release
- Make it available via `go get`

### Option 2: Manual Script

```bash
./scripts/release-agenkit-go.sh v0.10.1 "Release notes here"
```

**What it does:**
1. Validates you're on main with no uncommitted changes
2. Syncs latest code to standalone repo
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
