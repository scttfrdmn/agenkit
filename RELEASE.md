# Release Process

This document describes the coordinated release process for Agenkit across all three language implementations.

## Overview

Agenkit uses a **multi-repository** architecture with coordinated releases:

- **Main Repository** (this repo): Python + TypeScript implementations
  - Python: Published to [PyPI](https://pypi.org/project/agenkit/)
  - TypeScript: Published to [npm](https://www.npmjs.com/package/@agenkit/core)
- **Go Repository**: Separate repository for Go module publishing
  - Go: Published via [github.com/scttfrdmn/agenkit-go](https://github.com/scttfrdmn/agenkit-go)

## Version Strategy

Agenkit uses **semantic versioning** with coordinated major.minor versions across languages:

- **Python & Go**: Share the same version (e.g., `v0.10.0`)
- **TypeScript**: Independent minor/patch versions (e.g., `v0.2.0`)
  - TypeScript started later, so versions are offset

### Version Mapping

| Release | Python | Go | TypeScript | Notes |
|---------|--------|-----|-----------|-------|
| v0.10.0 | 0.10.0 | 0.10.0 | 0.2.0 | Phase 7 & 8 Complete |
| v0.9.0  | 0.9.0  | 0.9.0  | 0.1.0 | Initial TypeScript |
| v0.8.0  | 0.8.0  | 0.8.0  | -     | Pre-TypeScript |

## Release Checklist

### Prerequisites

- [ ] All tests passing in CI/CD
- [ ] CHANGELOG.md updated with release notes
- [ ] Version numbers updated in all files
- [ ] No outstanding critical bugs

### 1. Prepare Main Repository (Python + TypeScript)

```bash
# Update version numbers
# Python: pyproject.toml, agenkit/__init__.py
# TypeScript: agenkit-ts/package.json

# Update CHANGELOG.md
vim CHANGELOG.md

# Update ROADMAP.md (if milestones completed)
vim ROADMAP.md

# Commit changes
git add -A
git commit -m "release: Prepare vX.Y.Z - <brief description>"
git push

# Wait for CI/CD to pass
gh run list --limit 3
```

### 2. Create GitHub Release (Main Repo)

```bash
# Create and push tag
git tag vX.Y.Z
git push origin vX.Y.Z

# Create GitHub release
gh release create vX.Y.Z \
  --title "vX.Y.Z - <Release Title>" \
  --notes-file CHANGELOG.md \
  --latest

# Release URL: https://github.com/scttfrdmn/agenkit/releases/tag/vX.Y.Z
```

### 3. Publish TypeScript to npm

```bash
cd agenkit-ts

# Verify authentication
npm whoami

# Build and test
npm run build
npm test

# Dry run
npm publish --dry-run --access public

# Publish
npm publish --access public

# Verify publication
npm view @agenkit/core

# Package URL: https://www.npmjs.com/package/@agenkit/core
```

### 4. Publish Python to PyPI

```bash
# Install build tools
pip install build twine

# Build distributions
python -m build

# Check distributions
twine check dist/*

# Upload to PyPI
twine upload dist/*

# Verify publication
pip install agenkit==X.Y.Z

# Package URL: https://pypi.org/project/agenkit/
```

### 5. Sync Go Repository

```bash
# Navigate to Go repository
cd ../agenkit-go  # Or git clone if needed

# Add remote if not exists
git remote add upstream https://github.com/scttfrdmn/agenkit.git

# Sync Go code from main repo
# Option A: Manual sync (recommended for selective sync)
rsync -av --delete ../agenkit/agenkit-go/ ./ \
  --exclude='.git' \
  --exclude='go.sum' \
  --exclude='vendor'

# Option B: Git subtree (if using subtree setup)
git fetch upstream
git merge upstream/main --allow-unrelated-histories

# Review changes
git status
git diff

# Commit sync
git add -A
git commit -m "sync: Update from main repo for vX.Y.Z release"
git push origin main
```

### 6. Create Go Release

```bash
# Still in agenkit-go repository

# Create and push tag (Go uses 'v' prefix)
git tag vX.Y.Z
git push origin vX.Y.Z

# Create GitHub release
gh release create vX.Y.Z \
  --title "vX.Y.Z - <Release Title>" \
  --notes "Go implementation for Agenkit vX.Y.Z

See main repository for full release notes:
https://github.com/scttfrdmn/agenkit/releases/tag/vX.Y.Z" \
  --latest

# Go modules are automatically available once tag is pushed
# Users can: go get github.com/scttfrdmn/agenkit-go@vX.Y.Z

# Release URL: https://github.com/scttfrdmn/agenkit-go/releases/tag/vX.Y.Z
```

### 7. Verify All Releases

```bash
# Python
pip install agenkit==X.Y.Z
python -c "import agenkit; print(agenkit.__version__)"

# TypeScript
npm install @agenkit/core@X.Y.Z
node -e "console.log(require('@agenkit/core').version)"

# Go
go get github.com/scttfrdmn/agenkit-go@vX.Y.Z
go list -m github.com/scttfrdmn/agenkit-go
```

### 8. Announce Release

- [ ] Post on GitHub Discussions
- [ ] Update documentation site (if applicable)
- [ ] Tweet/social media announcement
- [ ] Update README badges if needed

## File Version Locations

### Main Repository

**Python:**
- `pyproject.toml` → `version = "X.Y.Z"`
- `agenkit/__init__.py` → `__version__ = "X.Y.Z"`

**TypeScript:**
- `agenkit-ts/package.json` → `"version": "X.Y.Z"`

### Go Repository

**Go:**
- `go.mod` → `module github.com/scttfrdmn/agenkit-go`
- Version is managed via Git tags only (no version file)

## Troubleshooting

### npm publish fails with "scope not found"

Ensure the `@agenkit` organization exists on npm:
- Create at: https://www.npmjs.com/org/create
- Add yourself as a member

### PyPI upload fails with authentication error

```bash
# Configure PyPI credentials
pip install twine
python -m twine upload dist/* --verbose
```

### Go module not accessible after release

Wait 5-10 minutes for Go proxy to update:
```bash
# Force proxy refresh
GOPROXY=direct go get github.com/scttfrdmn/agenkit-go@vX.Y.Z
```

## Hotfix Process

For critical bugs requiring immediate patches:

1. Create hotfix branch from release tag
2. Fix bug and add tests
3. Increment patch version (e.g., v0.10.0 → v0.10.1)
4. Follow standard release process for affected languages only
5. Cherry-pick fix to main branch

## Release Frequency

- **Major releases** (X.0.0): Breaking changes, yearly
- **Minor releases** (0.X.0): New features, monthly/quarterly
- **Patch releases** (0.0.X): Bug fixes, as needed

## Automation Future

Consider automating with GitHub Actions:
- Trigger on tag push
- Auto-publish to PyPI and npm
- Auto-sync and tag Go repository
- Auto-generate release notes from commits

## Related Documentation

- [CHANGELOG.md](./CHANGELOG.md) - Release history
- [ROADMAP.md](./ROADMAP.md) - Future plans
- [CONTRIBUTING.md](./CONTRIBUTING.md) - Contribution guidelines

## Questions?

File an issue or discussion at:
- Main repo: https://github.com/scttfrdmn/agenkit/issues
- Go repo: https://github.com/scttfrdmn/agenkit-go/issues
