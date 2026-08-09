# Agenkit Compatibility Matrix

Comprehensive compatibility information for Agenkit across languages, platforms, and dependencies.

**Last Updated**: August 2026
**Version**: v0.89.0 (see the root [`VERSION`](VERSION) file for the current
value — this document is not the source of truth for it)

> **Scope note**: Agenkit ships **nine** language implementations —
> Python, Go, TypeScript, Rust, C++, Zig, C#, Java, and Scala — at near-full
> pattern parity (see [`spec-conformance.json`](spec-conformance.json); C#/Java/Scala
> are missing exactly one of 18 patterns, `AgentsAsTools`) and full
> middleware/adapter parity (see [`feature-manifest.json`](feature-manifest.json)
> for the class-level inventory). This document historically
> covered only Python and Go; it has been updated to reflect all nine, but the
> per-feature detail below is necessarily uneven because that's where the
> richest cross-language detail (transport protocol variants, dependency
> pinning) already existed. For day-to-day "what's implemented where"
> lookups, [`spec-conformance.json`](spec-conformance.json) (per-pattern),
> [`feature-manifest.json`](feature-manifest.json) (per-class), and the
> [Test Parity](README.md#test-parity) table in `README.md` are kept current
> by tooling and are more likely to be accurate than a hand-maintained
> narrative doc like this one — treat this file as platform/runtime
> compatibility guidance, not the parity source of truth.

---

## Quick Reference

| Component | Status Across All 9 Languages |
|-----------|-------------------------------|
| **Core interfaces** (Agent, Message, Tool) | ✅ Full parity |
| **Patterns** (18 named) | 17/18 in all languages — C#/Java/Scala missing `AgentsAsTools` |
| **Middleware** (8 types) | ✅ Full parity |
| **Memory & checkpointing** | ✅ Full parity |
| **Safety & evaluation** | ✅ Full parity |
| **Observability (OpenTelemetry)** | ✅ Full parity |
| **HTTP/WebSocket/gRPC transports** | ✅ Python, Go, TypeScript, Rust, C++, Zig — see [Transport Protocol Details](#transport-protocol-details) for exact per-language coverage (C#/Java/Scala do not ship these standalone transports; they expose MCP HTTP clients instead) |

For the authoritative, tooling-generated per-pattern conformance breakdown
(does language X implement pattern Y, per `specs/patterns/*.yaml`), see
[`spec-conformance.json`](spec-conformance.json). For the class-level
inventory of middleware, adapter, memory, and technique classes per
language, see [`feature-manifest.json`](feature-manifest.json) — a
secondary, diagnostic signal for patterns specifically, since it counts
classes rather than checking conformance (#913).

---

## Language Support

### Python

| Python Version | Support Status | Notes |
|----------------|---------------|-------|
| **3.13** | ✅ **CI default** | `uv python install 3.13` in `.github/workflows/test.yml` |
| **3.12** | ✅ Supported | Minimum supported version (`requires-python = ">=3.12"` in `pyproject.toml`) |
| 3.14 | ✅ Supported | Listed in `pyproject.toml` classifiers |
| < 3.12 | ❌ Not supported | Below `requires-python` floor |

**Key Dependencies** (from `pyproject.toml`):
```
httpx[http2] >= 0.27.0
aiohttp >= 3.9.0
aioquic >= 1.0.0
websockets >= 12.0
grpcio >= 1.60.0
protobuf >= 4.25.0
opentelemetry-api >= 1.20.0
opentelemetry-sdk >= 1.20.0
opentelemetry-exporter-otlp >= 1.20.0
redis >= 4.5.0   (optional, [redis] extra)
numpy >= 1.24.0
scipy >= 1.11.0
scikit-learn >= 1.3.0
```

**Python Feature Requirements**:
- ✅ Type hints (PEP 484)
- ✅ Async/await (PEP 492)
- ✅ Dataclasses (PEP 557)
- ✅ Context managers (PEP 343)
- ✅ Typing generics (PEP 585)

### Go

| Go Version | Support Status | Notes |
|------------|---------------|-------|
| **1.25.12** | ✅ **Required** | `go` directive in `agenkit-go/go.mod`; also the CI toolchain version |
| < 1.25.12 | ❌ Not supported | Below the declared module floor |

Note: `agenkit-go` is a nested module inside this monorepo
(`github.com/scttfrdmn/agenkit/agenkit-go`), not a separately tagged
submodule — see `docs/RELEASING_AGENKIT_GO.md` and issue #660 before assuming
`agenkit-go/vX.Y.Z` tags exist.

**Key Dependencies** (from `agenkit-go/go.mod`, abridged — see the file for
the full indirect-dependency list):
```
google.golang.org/grpc v1.82.1
google.golang.org/protobuf v1.36.11
github.com/gorilla/websocket v1.5.3
github.com/quic-go/quic-go v0.61.0        // HTTP/3 (h3://) support
go.opentelemetry.io/otel v1.44.0
go.opentelemetry.io/otel/exporters/prometheus v0.66.0
github.com/redis/go-redis/v9 v9.21.0
```

**Go Feature Requirements**:
- ✅ Generics (Go 1.18+)
- ✅ Go modules
- ✅ Context package
- ✅ Goroutines & channels

### TypeScript

| Node Version | Support Status | Notes |
|---------------|---------------|-------|
| **22** | ✅ CI default | Used in `.github/workflows/test.yml` smoke jobs |
| **18+** | ✅ Supported | `"engines": {"node": ">=18.0.0"}` in `agenkit-ts/package.json` |
| < 18 | ❌ Not supported | Below the declared `engines` floor |

Package: `@agenkit/core`. Key dependencies include `@grpc/grpc-js`,
`@opentelemetry/*`, `chromadb`, and per-provider SDKs (`@anthropic-ai/sdk`,
`@aws-sdk/client-bedrock-runtime`, `@google/generative-ai`) — see
`agenkit-ts/package.json` for exact pinned ranges.

### Rust

| Rust Toolchain | Support Status | Notes |
|-----------------|---------------|-------|
| **stable** | ✅ Required | CI uses `dtolnay/rust-toolchain@stable`; `agenkit-rust/Cargo.toml` does not pin a `rust-version` (MSRV) field, so "stable at release time" is the only documented floor |

Edition 2021 (`agenkit-rust/Cargo.toml`). The crate uses feature flags for
optional transports (`tokio`, `reqwest`/`axum` for HTTP, `tokio-tungstenite`
for WebSocket) — see `Cargo.toml` for the full dependency/feature matrix.
`native` and `wasm` features are mutually exclusive; do not enable both.

### C++

| Standard | Support Status | Notes |
|----------|---------------|-------|
| **C++17** | ✅ Required | `set(CMAKE_CXX_STANDARD 17)` / `CMAKE_CXX_STANDARD_REQUIRED ON` in `agenkit-cpp/CMakeLists.txt` |

Requires CMake and `nlohmann-json3-dev` (see CI install step). Verified to
build under both Apple Clang and GCC/libstdc++ (Ubuntu 24.04 container) as of
issue #742/#744 — see the C++ leg of `.github/workflows/test.yml` for the
exact gate.

### Zig

| Zig Version | Support Status | Notes |
|--------------|---------------|-------|
| **0.16.0** | ✅ CI toolchain | Pinned in `.github/workflows/test.yml` (`mlugg/setup-zig@v2`) |
| **0.15.2** | Declared floor | `.minimum_zig_version` in `agenkit-zig/build.zig.zon` — this predates the 0.16.0 migration (#646); the CI-verified version is 0.16.0, not 0.15.2 |

Treat 0.16.0 as the version to actually use; the `build.zig.zon` floor has
not been bumped to match the CI toolchain.

### C#/.NET

| Target Framework | Support Status | Notes |
|-------------------|---------------|-------|
| **net10.0** | ✅ Required | `<TargetFramework>net10.0</TargetFramework>` in `agenkit-cs/src/Agenkit/Agenkit.csproj` |

Package: `Agenkit` (NuGet). CI uses `.NET 10.0.x` (`actions/setup-dotnet@v6`).

### Java

| Java Version | Support Status | Notes |
|---------------|---------------|-------|
| **17** | ✅ Required | `maven.compiler.source`/`maven.compiler.target` in `agenkit-java/pom.xml`; CI uses Temurin 17 |

Maven artifact: `io.agenkit:agenkit`.

### Scala

| Scala Version | Support Status | Notes |
|-----------------|---------------|-------|
| **3.4.2** | ✅ Required | `scala3Version` in `agenkit-scala/build.sbt` |

sbt artifact: `io.agenkit:agenkit-scala_3`. Built on a JDK 17 toolchain in CI
(same JDK setup as the Java leg).

---

## Platform Support

### Operating Systems

Agenkit's CI matrix runs exclusively on `ubuntu-latest` (see
`.github/workflows/test.yml`) — self-hosted macOS/Linux runners are
temporarily suspended (see `CLAUDE.md`, issues #892/#374). The claims below
about macOS/Windows/FreeBSD/ARM64 are **not independently CI-verified**;
they reflect what the underlying toolchains (Python, Go, Node, cargo, cmake,
zig, dotnet, mvn, sbt) support on those platforms, not an Agenkit-specific
test run.

| Platform | Expected support | Basis |
|----------|-------------------|-------|
| **Linux** | ✅ Full | CI-verified (all 9 languages) |
| **macOS** | ✅ Full (Intel & Apple Silicon) | Not CI-verified; all toolchains used support macOS natively |
| **Windows** | ⚠️ Likely, untested | Not CI-verified; Unix-socket-based code paths would need WSL2 or Windows-specific handling |
| **FreeBSD** | ⚠️ Untested | Community support only |
| **ARM64** | ✅ Likely | Not CI-verified; all underlying toolchains ship ARM64 builds |

### Container Platforms

`deploy/` contains Docker and Kubernetes manifests. These are maintained but
not part of the automated CI gate described above — treat container-platform
compatibility (Docker, Kubernetes, ECS/Fargate, Cloud Run, etc.) as
best-effort rather than CI-verified.

### Cloud Platforms

No cloud-platform-specific CI exists in this repository. AWS Bedrock, Google
Gemini, and OpenAI-compatible adapters are implemented and tested at the
library level (see `agenkit-*/adapters` or `agenkit-*/src/adapter`), but
full end-to-end deployment onto AWS/GCP/Azure/Heroku/Railway/Fly.io is not
exercised by CI.

---

## Core Features

Feature parity across all nine languages (patterns, middleware, transports,
composition, observability, memory, cost management, LLM adapters) is
tracked programmatically in [`spec-conformance.json`](spec-conformance.json)
(per-pattern) and [`feature-manifest.json`](feature-manifest.json)
(per-class), and summarized in `README.md`'s language support table and
[Test Parity](README.md#test-parity) section, all regenerated by tooling
(`scripts/parity/spec_conformance.py`, `scripts/test-parity.sh`, the Parity
Validation CI workflow) rather than hand-maintained. Rather than duplicate
an enumeration here that will drift, this document defers to those sources
for the current feature matrix.

At a high level, as of v0.89.0:
- 17 of 18 patterns ship in all 9 languages; C#/Java/Scala are missing
  `AgentsAsTools` (see [`spec-conformance.json`](spec-conformance.json)).
- All 8 middleware types ship in all 9 languages.
- Memory, safety, observability, budget, evaluation, and checkpointing
  subsystems ship in all 9 languages.
- Standalone HTTP/WebSocket/gRPC **transport** implementations (for building
  a remote agent server) exist in Python, Go, TypeScript, Rust, C++, and Zig.
  C#, Java, and Scala currently expose MCP (Model Context Protocol) HTTP
  clients/servers rather than the general-purpose transport layer the other
  six languages have — see [Transport Protocol Details](#transport-protocol-details).
- Reasoning **techniques** (Chain-of-Thought, Tree-of-Thought, etc., beyond
  the core patterns) exist in Python, Go, TypeScript, Rust, C++, and Zig;
  C#, Java, and Scala do not yet have a techniques subsystem.

---

## Transport Protocol Details

This section covers the six languages that ship standalone HTTP/WebSocket/gRPC
transports: Python, Go, TypeScript, Rust, C++, Zig.

### HTTP

| Feature | Python | Go | TypeScript | Rust | C++ | Zig |
|---------|--------|-----|-----|------|-----|-----|
| HTTP/1.1 | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| HTTP/2 | ✅ (via `httpx[http2]`) | ✅ | ✅ (`http2` option) | — | — | — |
| HTTP/3 (QUIC) | ✅ (`aioquic`, falls back to HTTP/2 since `httpx` lacks native HTTP/3) | ✅ (`quic-go/quic-go/http3`) | — | — | — | — |

Zig does not currently have a standalone HTTP transport module under
`agenkit-zig/src/transports/` (only gRPC and WebSocket exist there); C++ has
an HTTP agent/server (`agenkit-cpp/src/transports/http_agent.cpp`,
`http_server.cpp`) without documented HTTP/2 or HTTP/3 support. Rust's HTTP
transport (`agenkit-rust/src/transports/http.rs`) is HTTP/1.1 via
`reqwest`/`axum`; no HTTP/2 or HTTP/3-specific code was found in that file.

Treat the previous version of this table (claiming full HTTP/1.1 through
HTTP/3 parity between "Python and Go" alone) as inaccurate — it also omitted
the other seven languages entirely.

### WebSocket

Python, Go, TypeScript, Rust, and C++ all have WebSocket transport modules
(`websocket_transport.py`, `websocket_transport.go`, `websocket.ts`,
`websocket.rs`, `websocket_agent.cpp`). Zig has one
(`agenkit-zig/src/transports/websocket.zig`). Exact feature coverage
(compression, subprotocols, auto-reconnect) is not independently verified
per language here — consult each language's transport source/tests.

### gRPC

Python, Go, TypeScript, Rust, C++, and Zig all have gRPC transport modules
generated against the shared `proto/` definitions
(`agenkit-go/proto/agentpb`, etc.). C#, Java, and Scala do not.

---

## Dependency Version Compatibility

The dependency facts below are extracted directly from each language's
manifest at the time this file was last verified (commands shown so a
reviewer can re-run them):

| Language | Command | Result |
|----------|---------|--------|
| Python | `grep requires-python pyproject.toml` | `>=3.12` |
| Go | `grep '^go ' agenkit-go/go.mod` | `go 1.25.12` |
| TypeScript | `grep -A2 '"engines"' agenkit-ts/package.json` | `"node": ">=18.0.0"` |
| Rust | `grep '^edition' agenkit-rust/Cargo.toml` | `edition = "2021"` (no pinned MSRV) |
| C++ | `grep CXX_STANDARD agenkit-cpp/CMakeLists.txt` | `CMAKE_CXX_STANDARD 17` |
| Zig | `grep minimum_zig_version agenkit-zig/build.zig.zon` | `"0.15.2"` (CI actually uses 0.16.0) |
| C# | `grep TargetFramework agenkit-cs/src/Agenkit/Agenkit.csproj` | `net10.0` |
| Java | `grep maven.compiler.target agenkit-java/pom.xml` | `17` |
| Scala | `grep scala3Version agenkit-scala/build.sbt` | `"3.4.2"` |

For the full pinned dependency list of any language, read that language's
manifest directly (`pyproject.toml`, `agenkit-go/go.mod`,
`agenkit-ts/package.json`, `agenkit-rust/Cargo.toml`,
`agenkit-cpp/CMakeLists.txt`, `agenkit-zig/build.zig.zon`,
`agenkit-cs/src/Agenkit/Agenkit.csproj`, `agenkit-java/pom.xml`,
`agenkit-scala/build.sbt`) rather than this document — dependency pins
change frequently (Dependabot keeps them current) and a static table here
goes stale quickly.

---

## Performance Characteristics

The specific latency/throughput numbers that previously lived in this
section (e.g. "Go is 18.5x faster than Python for HTTP transport") were
measured in November 2025 against Python 3.14.0 / Go 1.21–1.22 on Apple
Silicon, as recorded in `benchmarks/BASELINES.md`. Both the Go toolchain
version and several dependency versions have since moved (see the
[Dependency Version Compatibility](#dependency-version-compatibility)
section above), so those exact figures should not be read as current.

For current, regenerable performance data:
- Run the benchmark suites directly: `benchmarks/test_middleware_overhead.py`,
  `benchmarks/test_transport_overhead.py`, `benchmarks/test_composition_overhead.py`,
  `benchmarks/adapter_overhead.py`.
- See `benchmarks/BASELINES.md` for the methodology and the most recent
  point-in-time measurements, each dated.

The qualitative conclusion that has held across every measurement to date —
that framework/middleware overhead is a small fraction (well under 1%) of a
typical LLM call's 100–1000ms latency — is still the right way to think
about this, independent of the exact multiplier on any given day.

---

## Known Limitations

### Platform-Specific Issues

**Windows**: Not CI-verified (see [Platform Support](#platform-support)).
Unix-socket-based transports would need Windows-specific handling or WSL2.

**macOS / Linux**: No known Agenkit-specific limitations; Linux is the only
CI-verified platform (`ubuntu-latest`).

### Feature-Specific Limitations

**HTTP/3 (QUIC)**: Only implemented in Python (`aioquic`, with a fallback to
HTTP/2 since `httpx` has no native HTTP/3 client) and Go
(`quic-go/quic-go/http3`). Requires UDP port access and TLS 1.3.

**gRPC**: Binary protocol (not browser-compatible without grpc-web). Not
implemented in C#, Java, or Scala.

**Techniques subsystem** (Chain-of-Thought, Tree-of-Thought, etc., beyond the
15+3 core patterns): Not implemented in C#, Java, or Scala as of v0.89.0.

---

## Testing Compatibility

### Test Counts

Test counts vary significantly by language and change every release; a
fixed table here goes stale immediately. Current counts are regenerated by
`scripts/test-parity.sh` into `test-parity-report.json` and summarized in
`README.md`'s [Test Parity](README.md#test-parity) table. Run
`./scripts/test-parity.sh` (or read `test-parity-report.json`'s
`generated_at` timestamp) for the current, dated numbers rather than trusting
any number reproduced in this file.

Per-language pattern/middleware/composition **parity** (does the feature
exist at all in this language) is full across all 9 languages as of
v0.89.0 for the core pattern/middleware/composition/memory/safety/
observability/budget/evaluation/checkpointing subsystems — see
[Core Features](#core-features) above for the caveats on transports and
techniques.

### CI

CI runs on GitHub-hosted `ubuntu-latest` runners for all workflows
(self-hosted routing is temporarily suspended — see `CLAUDE.md` and issues
#892/#374). Toolchain versions pinned in CI:

| Language | CI Toolchain Version |
|----------|----------------------|
| Python | 3.13 (`uv python install 3.13`) |
| Go | 1.25.12 |
| TypeScript/Node | 22 |
| Rust | `stable` (rolling) |
| Zig | 0.16.0 |
| C#/.NET | 10.0.x |
| Java | 17 (Temurin) |
| Scala | Scala 3.4.2 on JDK 17 |

**Local testing is primary, not CI** — see `CLAUDE.md`'s Testing Policy
section. Run `make test` before committing; CI is a safety net, not the
gate.

---

## Support & Maintenance

### Versioning

Agenkit follows [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html)
(see `RELEASING.md`). The project has never shipped a v1.0.0 — it moved
directly from the v0.9.0 era into the current v0.x release train without a
1.0 milestone (see `ROADMAP.md`'s note on milestones #52/#53, both closed
2026-03-16 with zero issues ever tracked against them). Breaking changes are
documented per release in `CHANGELOG.md` (search for "BREAKING").

For the current version, always read the root [`VERSION`](VERSION) file —
`make check-version` asserts all version declarations across the repo agree
with it.

---

## Getting Help

### Compatibility Issues

If you encounter compatibility problems:

1. **Check this document** for known limitations
2. **Check `spec-conformance.json`** for exact per-language pattern coverage, or
   `feature-manifest.json` for middleware/adapter class-level coverage
3. **Search GitHub Issues**: https://github.com/scttfrdmn/agenkit/issues
4. **Ask in Discussions**: https://github.com/scttfrdmn/agenkit/discussions
5. **Report a bug**: Include OS, language toolchain version, and error details

### Version-Specific Information

```bash
# Check installed versions
python -c "import agenkit; print(agenkit.__version__)"
go list -m github.com/scttfrdmn/agenkit/agenkit-go

# Check language toolchain versions
python --version
go version
node --version
cargo --version
zig version
dotnet --version
java -version
scala --version

# Check the repo's declared version (single source of truth)
cat VERSION
```

---

**Need more information?**
See [.github/CONTRIBUTING.md](.github/CONTRIBUTING.md) for development setup or [SECURITY.md](SECURITY.md) for security considerations.

**Last Updated**: August 2026
**Maintainers**: Agenkit Core Team
