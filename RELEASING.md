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

The root `VERSION` file is the single source of truth. Do **not** hand-edit
`pyproject.toml` or any other manifest — the version is declared in 19 places
across nine languages, and CI's blocking `version-guard` job fails if any of them
disagrees (#842):

```bash
scripts/version.py set X.Y.Z   # writes VERSION, then propagates to all 19
make check-version             # asserts they all agree
```

`scripts/release.sh` already does both, so this step is only for a manual release.

### 3. Run Tests

```bash
# Full local gate — this is the project's validation, not CI (see CLAUDE.md)
make test

# Lint and type check
make test-lint
```

### 4. Commit and Tag

```bash
# Commit version bump — -A because `version.py set` touched 19 files
git add -A
git commit -m "chore: bump version to X.Y.Z"

# Create annotated tag. One tag, bare vX.Y.Z — see below.
git tag -a vX.Y.Z -m "Release vX.Y.Z"
```

#### One tag only — do not add `agenkit-go/vX.Y.Z`

A directory-prefixed tag would make `github.com/scttfrdmn/agenkit/agenkit-go`
pinnable, and that is deliberately not wanted: if both module paths are pinnable, a
single build can import both, and the two byte-identical `agenkit.Message` types are
then not assignable, because Go type identity includes the module path. The monorepo
path instead carries a `// Deprecated:` block directing consumers to the mirror.

The mirror `github.com/scttfrdmn/agenkit-go` is the canonical, tagged path, and CI
tags it from the bare `vX.Y.Z` tag pushed here.

Full rationale and the rejected alternative:
[docs/RELEASING_AGENKIT_GO.md](docs/RELEASING_AGENKIT_GO.md#why-we-deprecated-the-monorepo-path-instead-of-tagging-it-660),
which is the single authority on module paths. See #660.

No other language needs a second tag: Python/npm/crates/Maven/NuGet all publish
from their own manifests and ignore git tags.

#### If you ever rewrite history, migrate the tags in the same operation

A `git filter-repo`/`filter-branch` pass rewrites every SHA, so **existing tags keep
pointing at the pre-rewrite objects** and become unreachable from any branch. This
already happened once, in the v0.86.0 binary purge: 83 of 85 tags (`v0.1.0`–`v0.85.0`
plus `v0.30.0-cpp`) descend from an orphaned root that is not an ancestor of `main`;
only `v0.86.0` and `v0.87.0` are reachable. The damage is permanent because it was
published — see #852 for the full measurement.

Consequences to avoid repeating: `git bisect` and `git describe` cannot cross the
boundary, and `git log v0.85.0..v0.86.0` reports 1128 commits because it is diffing
two unrelated trees, which makes every auto-generated `compare/A...B` release-note
link across it wrong.

If a rewrite is ever unavoidable, re-point every tag at its rewritten commit as part
of the same operation (`git filter-repo` does this automatically; `filter-branch`
needs `--tag-name-filter cat`), and verify before pushing:

```bash
# Every release tag should be reachable from main. Today this prints 83 orphans
# (v0.1.0–v0.85.0 plus v0.30.0-cpp); after a correct rewrite it prints nothing new.
git tag | while read -r t; do
    git merge-base --is-ancestor "$t" main 2>/dev/null || echo "orphaned: $t"
done

# Every tag should share main's root commit. Compare against main specifically —
# not `--all`, which also reports the gh-pages root (MkDocs deploys to an orphan
# branch by design) and any stale local branches.
git rev-list --max-parents=0 main
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

> `--generate-notes` derives its commit list and `compare/A...B` link from tag
> ancestry, so it is only meaningful for releases after v0.86.0. Across the
> v0.85.0→v0.86.0 boundary it emits a 1128-commit diff of two unrelated trees
> (see step 4). Prefer `--notes-file` if you ever release from an older tag.

### 7. Post-Release

- Verify release appears on GitHub
- Test installation from GitHub
- Update documentation links if needed
- Announce release (if applicable)

Verify the Go module resolves at the new version — on the **mirror**, which is the
canonical path. The monorepo path is expected *not* to resolve; that is the design
(#660), not a bug to fix:

```bash
# Should print v0.87.0 (or whatever you just released)
go list -m github.com/scttfrdmn/agenkit-go@vX.Y.Z

# Should list every released version
go list -m -versions github.com/scttfrdmn/agenkit-go

# The monorepo path should report "(deprecated)" and only ever a pseudo-version:
#   github.com/scttfrdmn/agenkit/agenkit-go v0.0.0-20260805030849-5fe6703 (deprecated)
# The @latest suffix is required (-u alone only inspects modules already in the
# build list), and GOPROXY=direct because the proxy's @latest lags a merge.
GOPROXY=direct go list -m -u github.com/scttfrdmn/agenkit/agenkit-go@latest
```

The proxy caches on first request, so allow a few minutes after pushing tags.

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

- [ ] All tests passing (`make test`)
- [ ] Lint and type checking clean (`make test-lint`)
- [ ] CHANGELOG.md updated
- [ ] Version set via `scripts/version.py set X.Y.Z` (never hand-edit a manifest)
- [ ] All 19 version declarations agree (`make check-version`)
- [ ] Examples tested manually
- [ ] Documentation reviewed
- [ ] **Release notes prepared** (REQUIRED)
- [ ] Breaking changes documented (if MAJOR)
- [ ] Migration guide provided (if breaking changes)
- [ ] No build artifacts tracked (`make check-artifacts`)

## Post-Release Checklist

After creating release:

- [ ] Release appears on GitHub
- [ ] Tag pushed successfully (one bare `vX.Y.Z` tag — see step 4)
- [ ] Mirror tagged by CI: `go list -m github.com/scttfrdmn/agenkit-go@vX.Y.Z`
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
- Every release needs exactly **one** tag: a bare `vX.Y.Z`. Never
  `agenkit-go/vX.Y.Z` (step 4)
- The version comes from the root `VERSION` file, never from a hand-edited manifest
- Follow Keep a Changelog format strictly
- Test everything before releasing
- Be conservative with MAJOR version bumps
- Document breaking changes thoroughly
