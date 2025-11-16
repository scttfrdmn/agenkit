# Multi-Language Distribution Strategy

## Overview

Agenkit is a cross-language framework with implementations in multiple languages. Each language has its own distribution channel and package management system.

## Current Status (v0.9.0)

| Language   | Registry       | Status | Package Name | Installation |
|------------|----------------|--------|--------------|--------------|
| Python     | PyPI           | 🔄 Ready to publish | `agenkit` | `pip install agenkit` |
| Go         | Go Modules     | 🔄 Setup needed | `github.com/scttfrdmn/agenkit/agenkit-go` | `go get github.com/scttfrdmn/agenkit/agenkit-go` |
| TypeScript | npm            | 📅 Planned | `@agenkit/core` | `npm install @agenkit/core` |
| Rust       | crates.io      | 📅 Planned | `agenkit` | `cargo add agenkit` |

---

## 1. Python → PyPI

### Current Status: 🔄 **Ready to Publish**

**Package:** `agenkit`
**Registry:** https://pypi.org

### Build & Publish:

```bash
# Build (already done)
uv run python -m build

# Publish
uv run python -m twine upload dist/*
```

**Documentation:** See `PYPI_PUBLICATION_GUIDE.md`

### Features:
- ✅ Source distribution (sdist)
- ✅ Binary wheel
- ✅ All dependencies specified
- ✅ Python 3.10+ support

---

## 2. Go → Go Modules

### Current Status: 🔄 **Setup Needed**

**Current Path:** `github.com/scttfrdmn/agenkit/agenkit-go` (monorepo subdirectory)
**Registry:** Go Modules (via GitHub)

### Current Situation:

The Go implementation lives in the monorepo at `/agenkit-go`. For Go modules to work cleanly, we have two options:

#### Option A: Separate Repository (Recommended)

Create a dedicated `agenkit-go` repository:

**Pros:**
- Clean Go module path: `github.com/scttfrdmn/agenkit-go`
- Better Go ecosystem integration
- Independent versioning
- Cleaner `pkg.go.dev` documentation
- Standard Go community practice

**Cons:**
- Maintain two repositories
- Cross-repo version synchronization needed

**Setup:**
```bash
# Create new repo
gh repo create scttfrdmn/agenkit-go --public --description "Agenkit - Go implementation"

# Copy Go code
cp -r agenkit-go/ /tmp/agenkit-go/
cd /tmp/agenkit-go

# Initialize
git init
git add .
git commit -m "Initial commit: Agenkit Go v0.9.0"
git tag v0.9.0
git remote add origin https://github.com/scttfrdmn/agenkit-go.git
git push -u origin main --tags
```

**Then users can:**
```bash
go get github.com/scttfrdmn/agenkit-go@v0.9.0
```

#### Option B: Monorepo with Go Workspace (Alternative)

Keep in monorepo but set up properly:

**Add go.mod to /agenkit-go:**
```go
module github.com/scttfrdmn/agenkit/agenkit-go

go 1.21

require (
    google.golang.org/grpc v1.60.0
    google.golang.org/protobuf v1.32.0
    github.com/gorilla/websocket v1.5.1
)
```

**Then users can:**
```bash
go get github.com/scttfrdmn/agenkit/agenkit-go@v0.9.0
```

**Pros:**
- Single repository
- Easier cross-language versioning

**Cons:**
- Longer import path
- Less idiomatic for Go users
- More complex for Go tooling

### Recommendation:

**For v0.9.0:** Use Option B (monorepo) for simplicity
**For v1.0.0:** Consider Option A (separate repo) for better Go ecosystem integration

### Setup Steps for Option B (Immediate):

1. Create `go.mod` in `/agenkit-go`:
```bash
cd /Users/scttfrdmn/src/agenkit/agenkit-go
go mod init github.com/scttfrdmn/agenkit/agenkit-go
go mod tidy
```

2. Commit and push:
```bash
git add agenkit-go/go.mod agenkit-go/go.sum
git commit -m "feat(go): Add go.mod for Go modules support"
git push
```

3. Test installation:
```bash
go get github.com/scttfrdmn/agenkit/agenkit-go@v0.9.0
```

### Verification (After Setup):

```bash
go list -m github.com/scttfrdmn/agenkit/agenkit-go@v0.9.0
# Should show: github.com/scttfrdmn/agenkit/agenkit-go v0.9.0
```

---

## 3. TypeScript → npm

### Current Status: 📅 **Planned (Phase: TypeScript Implementation)**

**Package:** `@agenkit/core`
**Registry:** https://npmjs.com

### Planned Structure:

```
agenkit-ts/
├── packages/
│   ├── core/           # @agenkit/core
│   ├── wasm/           # @agenkit/wasm
│   └── adapters/       # @agenkit/adapters
├── package.json
└── tsconfig.json
```

### Setup Steps (When Ready):

1. **Create npm account:**
   ```bash
   npm adduser
   ```

2. **Create scoped package:**
   ```bash
   npm init --scope=@agenkit
   ```

3. **package.json example:**
   ```json
   {
     "name": "@agenkit/core",
     "version": "0.9.0",
     "description": "The foundation layer for AI agents - TypeScript",
     "main": "dist/index.js",
     "types": "dist/index.d.ts",
     "repository": {
       "type": "git",
       "url": "https://github.com/scttfrdmn/agenkit-ts"
     },
     "keywords": ["ai", "agents", "typescript", "llm"],
     "license": "Apache-2.0"
   }
   ```

4. **Publish:**
   ```bash
   npm publish --access=public
   ```

### Multi-Package Strategy:

```bash
# Core framework
npm install @agenkit/core

# WASM runtime
npm install @agenkit/wasm

# All adapters
npm install @agenkit/adapters
```

### Distribution Targets:
- ✅ Node.js
- ✅ Deno (via npm: imports)
- ✅ Bun (compatible with npm)
- ✅ Browser (via bundlers)

---

## 4. Rust → crates.io

### Current Status: 📅 **Planned (Phase: Rust Implementation)**

**Package:** `agenkit`
**Registry:** https://crates.io

### Setup Steps (When Ready):

1. **Create crates.io account:**
   - Link GitHub account at https://crates.io
   - Generate API token

2. **Cargo.toml example:**
   ```toml
   [package]
   name = "agenkit"
   version = "0.9.0"
   edition = "2021"
   authors = ["Scott Friedman <scttfrdmn@users.noreply.github.com>"]
   description = "The foundation layer for AI agents"
   repository = "https://github.com/scttfrdmn/agenkit-rs"
   license = "Apache-2.0"
   keywords = ["ai", "agents", "llm", "framework"]
   categories = ["asynchronous", "web-programming", "wasm"]

   [dependencies]
   tokio = { version = "1.35", features = ["full"] }
   serde = { version = "1.0", features = ["derive"] }
   # ... other dependencies
   ```

3. **Login to crates.io:**
   ```bash
   cargo login
   ```

4. **Publish:**
   ```bash
   cargo publish
   ```

### WASM Compilation:

```bash
# Build for WASM
cargo build --target wasm32-unknown-unknown --release

# Package with wasm-pack
wasm-pack build --target web
```

### Multi-Crate Workspace:

```
agenkit-rs/
├── agenkit/          # Core crate
├── agenkit-wasm/     # WASM bindings
├── agenkit-macro/    # Procedural macros
└── Cargo.toml        # Workspace config
```

---

## Cross-Language Version Synchronization

### Versioning Strategy:

**Approach:** **Independent but synchronized** versions

- All languages start at v0.9.0
- Major versions kept in sync (0.x, 1.x)
- Minor versions can diverge (language-specific features)
- Patch versions independent (bug fixes)

### Example Timeline:

```
v0.9.0  - Initial release (Python, Go)
v0.9.1  - Python bug fix
v0.9.2  - Go performance improvement
v0.10.0 - TypeScript implementation added (Python v0.10.0, Go v0.10.0, TS v0.10.0)
v0.11.0 - Rust implementation added
v1.0.0  - All languages stabilized together
```

### Release Checklist:

When releasing a new version:

- [ ] Update version in all language packages
- [ ] Update CHANGELOG.md (cross-language)
- [ ] Create git tag: `v0.X.Y`
- [ ] Publish Python to PyPI
- [ ] Push Go tag (automatic via git)
- [ ] Publish TypeScript to npm (when ready)
- [ ] Publish Rust to crates.io (when ready)
- [ ] Update documentation site
- [ ] Announce on GitHub Discussions

---

## Package Naming Conventions

### Python
- **Main package:** `agenkit`
- **Optional extras:** `agenkit[llm]`, `agenkit[benchmarks]`

### Go
- **Module path:** `github.com/scttfrdmn/agenkit-go`
- **Import path:** `github.com/scttfrdmn/agenkit-go/adapter`

### TypeScript
- **Scoped packages:** `@agenkit/*`
- **Main:** `@agenkit/core`
- **WASM:** `@agenkit/wasm`

### Rust
- **Main crate:** `agenkit`
- **WASM:** `agenkit-wasm`
- **Features:** `agenkit = { version = "0.9", features = ["full"] }`

---

## Installation Quick Reference

```bash
# Python
pip install agenkit

# Go
go get github.com/scttfrdmn/agenkit-go@v0.9.0

# TypeScript (future)
npm install @agenkit/core

# Rust (future)
cargo add agenkit
```

---

## Monitoring & Analytics

### Download Statistics:

- **Python:** https://pypistats.org/packages/agenkit
- **Go:** https://pkg.go.dev/github.com/scttfrdmn/agenkit-go
- **TypeScript:** https://www.npmjs.com/package/@agenkit/core
- **Rust:** https://crates.io/crates/agenkit

### Goals (First 6 Months):

| Language   | Weekly Downloads Target |
|------------|------------------------|
| Python     | 500+                   |
| Go         | 200+                   |
| TypeScript | 300+ (when released)   |
| Rust       | 100+ (when released)   |

---

## Next Actions

### Immediate (v0.9.0):
1. ✅ Go - Already live via git tag
2. 🔄 Python - Publish to PyPI (see PYPI_PUBLICATION_GUIDE.md)

### Short-term (v0.10.0 - Week 2-4):
3. 📅 TypeScript - Implement core package
4. 📅 TypeScript - Publish `@agenkit/core` to npm

### Medium-term (v0.11.0 - Week 5-8):
5. 📅 Rust - Implement core crate
6. 📅 Rust - Publish to crates.io
7. 📅 Rust - WASM compilation and distribution

---

## Security & Trust

### Package Verification:

All packages should be verifiable through:
- **Source:** GitHub repository
- **Signatures:** GPG-signed git tags
- **Checksums:** Provided in releases
- **Security Policy:** SECURITY.md in each repo

### Two-Factor Authentication:

Enable 2FA on all distribution accounts:
- ✅ GitHub (already enabled)
- 🔄 PyPI (enable after account creation)
- 📅 npm (enable when setting up)
- 📅 crates.io (automatic via GitHub 2FA)

---

## Questions?

See language-specific guides:
- **Python:** `PYPI_PUBLICATION_GUIDE.md`
- **Go:** Works automatically via git tags
- **TypeScript:** TBD (create when implementing)
- **Rust:** TBD (create when implementing)
