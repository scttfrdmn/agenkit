# Releasing Agenkit

Complete guide for releasing agenkit (monorepo) and agenkit-go (standalone).

## Quick Start

**Release everything (recommended):**
```bash
./scripts/release.sh v0.11.0
```

This will:
1. ✅ Update version in `pyproject.toml`
2. ✅ Run tests
3. ✅ Tag and release monorepo
4. ✅ Push the `vX.Y.Z` tag, which triggers the `sync-agenkit-go.yml` workflow to
      sync, tag, and release the agenkit-go standalone repo automatically
5. ✅ Keep both repos in sync

> The agenkit-go mirror is released by CI in response to the tag push — not by the
> release script directly. See [RELEASING_AGENKIT_GO.md](./RELEASING_AGENKIT_GO.md).

**Release only monorepo:**
```bash
./scripts/release.sh v0.11.0 --skip-go
```

**Release only agenkit-go:**
```bash
./scripts/release-agenkit-go.sh v0.11.0
```

## Release Types

### Unified Release (Recommended)

**When:** Releasing a new version that includes changes across Python and/or Go

**Command:**
```bash
./scripts/release.sh v0.11.0
```

**What happens:**
1. Updates Python version in `pyproject.toml`
2. Commits version bump
3. Runs tests
4. Creates tag on monorepo
5. Creates GitHub release on monorepo
6. Automatically releases agenkit-go standalone repo with same version
7. Both repos stay in sync

**Benefits:**
- ✅ Version numbers stay synchronized
- ✅ One command releases everything
- ✅ Consistent release notes
- ✅ Less room for error

### Go-Only Release

**When:** Releasing Go-specific fixes without Python changes

**Command:**
```bash
./scripts/release-agenkit-go.sh v0.10.1
```

**What happens:**
- Only releases standalone agenkit-go repo
- Monorepo stays at current version
- Use when Go SDK needs a patch but Python doesn't

## Version Numbering Strategy

### Synchronized Versions (Recommended)

Keep both Python and Go at the same version:
- **Monorepo:** v0.11.0
- **Go SDK:** v0.11.0

**Advantages:**
- Easier to understand compatibility
- Simpler documentation
- Clear what's included in each release

### Independent Versions (When Needed)

Use different versions if needed:
- **Monorepo:** v0.11.0
- **Go SDK:** v0.10.5 (if only Go needed patch)

**When to use:**
- Go-specific bug fix
- Python-specific feature
- Different release cadences

## Semantic Versioning

Follow [semver](https://semver.org/):

**MAJOR.MINOR.PATCH** (e.g., v1.2.3)

- **MAJOR (v1.0.0 → v2.0.0)**
  - Breaking API changes
  - Incompatible changes
  - Major redesigns

- **MINOR (v0.10.0 → v0.11.0)**
  - New features
  - Backwards compatible
  - New capabilities

- **PATCH (v0.10.0 → v0.10.1)**
  - Bug fixes
  - Performance improvements
  - Security fixes

### Pre-releases

```bash
v0.11.0-alpha.1  # Early testing
v0.11.0-beta.1   # Feature complete, testing
v0.11.0-rc.1     # Release candidate
```

## Release Checklist

### Before Release

- [ ] All CI/CD checks passing
- [ ] All PRs merged
- [ ] Changelog updated (if exists)
- [ ] Documentation updated
- [ ] Breaking changes documented
- [ ] Migration guide written (if needed)
- [ ] Version number decided

### During Release

The script handles:
- [ ] Version bump in `pyproject.toml`
- [ ] Git commit and tag creation
- [ ] GitHub releases
- [ ] agenkit-go sync and release

### After Release

- [ ] Verify releases exist:
  - https://github.com/scttfrdmn/agenkit/releases
  - https://github.com/scttfrdmn/agenkit-go/releases
- [ ] Test installations:
  ```bash
  # Python
  pip install agenkit==0.11.0

  # Go
  go get github.com/scttfrdmn/agenkit-go@v0.11.0
  ```
- [ ] Announce release (if appropriate)
- [ ] Monitor for issues
- [ ] Update dependent projects

## Examples

### Standard Release

```bash
# Release v0.11.0 (both Python and Go)
./scripts/release.sh v0.11.0

# What you'll see:
# 📋 Pre-flight checks...
# 📝 Updating version numbers...
# 🧪 Running tests...
# 🏷️  Creating git tag...
# 🚀 Pushing to GitHub...
# 📦 Creating GitHub release...
# 🔧 Releasing agenkit-go...
# 🎉 Release Complete!
```

### Bug Fix Release

```bash
# Fix critical bug, release v0.10.1
./scripts/release.sh v0.10.1
```

### Go-Only Patch

```bash
# Only fix Go issue, release v0.10.2
./scripts/release-agenkit-go.sh v0.10.2 "Fix Go-specific memory leak"
```

### Pre-release

```bash
# Release beta for testing
./scripts/release.sh v0.11.0-beta.1
```

## Troubleshooting

### "Not on main branch"

```bash
git checkout main
git pull origin main
```

### "Working directory has uncommitted changes"

```bash
git status
git add -A && git commit -m "Pre-release cleanup"
# or
git stash
```

### "Tag already exists"

Delete the tag and retry:
```bash
git tag -d v0.11.0
git push --delete origin v0.11.0
```

### Tests failed

The script will ask if you want to continue. Consider:
- Fix the tests first (recommended)
- Continue anyway if it's a known issue
- Abort and investigate

### Release script failed mid-way

**If before tag creation:**
- Reset version bump: `git reset --soft HEAD~1`
- Fix the issue and retry

**If after tag creation:**
- Tag exists but release might not
- Delete tag and retry, or manually create release

### Wrong version number

If you haven't pushed yet:
```bash
git tag -d v0.11.0  # Delete local tag
git reset --soft HEAD~1  # Undo version commit
# Start over with correct version
```

If you already pushed:
- Create a new patch version
- Don't reuse or change existing tags

## PyPI Publishing (Optional)

After release, publish to PyPI:

```bash
# Build distribution
python -m build

# Check the build
twine check dist/*

# Upload to Test PyPI first
twine upload --repository testpypi dist/*

# Test installation
pip install --index-url https://test.pypi.org/simple/ agenkit

# Upload to PyPI
twine upload dist/*
```

## Release Frequency

**Recommended schedule:**
- **Patch releases:** As needed for critical bugs
- **Minor releases:** Every 2-4 weeks
- **Major releases:** When breaking changes are necessary

**Balance:**
- Release often enough to deliver fixes quickly
- Not so often that users can't keep up
- Coordinate with user feedback and roadmap

## Communication

### Release Notes Template

```markdown
## Agenkit v0.11.0

### ✨ Features
- New middleware for rate limiting
- Added streaming support for gRPC

### 🐛 Bug Fixes
- Fixed memory leak in connection pool
- Corrected error handling in timeout middleware

### 📚 Documentation
- Added comprehensive examples
- Updated API documentation

### 🔧 Internal
- Improved test coverage
- Performance optimizations

## Installation

**Python:**
\`\`\`bash
pip install agenkit==0.11.0
\`\`\`

**Go:**
\`\`\`bash
go get github.com/scttfrdmn/agenkit-go@v0.11.0
\`\`\`

## Breaking Changes

None in this release.

## Upgrade Guide

No special steps required - drop-in replacement for v0.10.0.
```

### Where to Announce

- GitHub Releases (automatic)
- Project README
- Documentation site
- Community channels (if any)
- Social media (if appropriate)

## Advanced: CI/CD Integration

You can also trigger releases via GitHub Actions:

```yaml
# .github/workflows/release.yml
on:
  workflow_dispatch:
    inputs:
      version:
        description: 'Version (e.g., v0.11.0)'
        required: true
      skip_go:
        description: 'Skip Go release'
        type: boolean
        default: false
```

This allows releases via GitHub UI instead of CLI.
