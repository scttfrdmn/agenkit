# Release Process

This document describes the release process for agenkit.

## Versioning

We follow [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html):

- **MAJOR** version: Incompatible API changes
- **MINOR** version: Backwards-compatible functionality additions
- **PATCH** version: Backwards-compatible bug fixes

## Release Checklist

### 1. Update CHANGELOG.md

Following [Keep a Changelog](https://keepachangelog.com/) format:

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
- New features

### Changed
- Changes in existing functionality

### Deprecated
- Soon-to-be removed features

### Removed
- Removed features

### Fixed
- Bug fixes

### Security
- Security fixes
```

### 2. Update Version

Update version in `pyproject.toml`:

```toml
[project]
version = "X.Y.Z"
```

### 3. Run Tests

```bash
# Type check
mypy

# Run all tests
pytest tests/ benchmarks/ -v

# Verify examples work
python examples/01_basic_agent.py
# ... test other examples
```

### 4. Commit and Tag

```bash
# Commit version bump
git add pyproject.toml CHANGELOG.md
git commit -m "chore: bump version to X.Y.Z"

# Create annotated tag
git tag -a vX.Y.Z -m "Release vX.Y.Z"
```

### 5. Create Release Notes

**REQUIRED:** Every release MUST have release notes.

Release notes should include:
- **Summary:** Brief description of the release
- **Highlights:** Key features/changes (3-5 bullet points)
- **Breaking Changes:** If any (MAJOR versions)
- **Full Changelog:** Link to CHANGELOG.md section
- **Installation:** How to install this version
- **Documentation:** Link to docs
- **Contributors:** Thank contributors (if applicable)

Use the template below.

### 6. Push and Publish

```bash
# Push commits and tags
git push origin main --tags

# Create GitHub release with notes
gh release create vX.Y.Z --title "Release vX.Y.Z" --notes-file RELEASE_NOTES.md

# Or create release interactively
gh release create vX.Y.Z --generate-notes
```

### 7. Post-Release

- Verify release appears on GitHub
- Test installation from GitHub
- Update documentation links if needed
- Announce release (if applicable)

---

## Release Notes Template

Save as `RELEASE_NOTES.md` for each release:

```markdown
# Release vX.Y.Z

**Release Date:** YYYY-MM-DD

## Summary

Brief 1-2 sentence summary of this release.

## Highlights

- ✨ **New Feature:** Description
- 🚀 **Performance:** Description
- 🐛 **Bug Fix:** Description
- 📚 **Documentation:** Description

## Breaking Changes

⚠️ **MAJOR version only**

- Breaking change description
- Migration guide

## Installation

```bash
pip install agenkit==X.Y.Z
```

Or install from source:

```bash
git clone https://github.com/scttfrdmn/agenkit.git
cd agenkit
git checkout vX.Y.Z
pip install -e .
```

## Full Changelog

See [CHANGELOG.md](CHANGELOG.md#xyz---yyyy-mm-dd) for complete details.

## Documentation

- [API Documentation](docs/API.md)
- [Examples](examples/)
- [README](README.md)

## Contributors

Thank you to everyone who contributed to this release!

- @contributor1
- @contributor2
```

---

## Pre-Release Checklist

Before creating any release:

- [ ] All tests passing (`pytest tests/ benchmarks/`)
- [ ] Type checking clean (`mypy`)
- [ ] CHANGELOG.md updated
- [ ] Version bumped in pyproject.toml
- [ ] Examples tested manually
- [ ] Documentation reviewed
- [ ] **Release notes prepared** (REQUIRED)
- [ ] Breaking changes documented (if MAJOR)
- [ ] Migration guide provided (if breaking changes)

## Post-Release Checklist

After creating release:

- [ ] Release appears on GitHub
- [ ] Tag pushed successfully
- [ ] Release notes published
- [ ] Installation tested
- [ ] Documentation links work
- [ ] Announcement made (if applicable)

---

## Emergency Hotfix Process

For critical security or bug fixes:

1. Create hotfix branch from main
2. Fix issue with minimal changes
3. Bump PATCH version
4. Update CHANGELOG.md (Security or Fixed section)
5. Full test suite
6. Release notes (mark as HOTFIX)
7. Fast-track review and release

---

## Notes

- **Release notes are MANDATORY** - Never release without them
- Always use annotated tags (`git tag -a`)
- Follow Keep a Changelog format strictly
- Test everything before releasing
- Be conservative with MAJOR version bumps
- Document breaking changes thoroughly
