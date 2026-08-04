# Installation Profiles

**Version**: v0.46.0
**Last Updated**: January 15, 2026

This document describes optional dependencies and installation profiles for Agenkit across all 6 supported languages.

---

## Table of Contents

1. [Python Installation Profiles](#python-installation-profiles)
2. [TypeScript Installation Profiles](#typescript-installation-profiles)
3. [Go Installation Profiles](#go-installation-profiles)
4. [Rust Installation Profiles](#rust-installation-profiles)
5. [C++ Installation Profiles](#cpp-installation-profiles)
6. [Zig Installation Profiles](#zig-installation-profiles)
7. [Quick Reference Table](#quick-reference-table)

---

## Python Installation Profiles

### Base Installation

```bash
pip install agenkit
```

Includes:
- Core agent interfaces
- Basic patterns (Sequential, React, Router)
- In-memory storage
- Standard middleware

### Available Extras

#### 1. AWS Integration (`aws`)

```bash
pip install agenkit[aws]
# or
pip install 'agenkit[aws]'  # Bash/Zsh shell escaping
```

**Includes**:
- `boto3` - AWS SDK
- `botocore` - AWS core library
- AWS Bedrock adapter (Claude, Llama, Titan models)
- AWS credentials handling

**Use Cases**:
- Deploy agents on AWS Lambda
- Use AWS Bedrock LLMs
- Store checkpoints in S3
- Use DynamoDB for state management

#### 2. Redis Integration (`redis`)

```bash
pip install agenkit[redis]
```

**Includes**:
- `redis` - Redis client
- `redis-py` - Async Redis support
- Redis-backed memory
- Redis-backed checkpoint storage
- Distributed rate limiting

**Use Cases**:
- Distributed agent deployments
- Shared memory across instances
- High-performance caching
- Session management

#### 3. Vector Store Integration (`vector`)

```bash
pip install agenkit[vector]
```

**Includes**:
- `chromadb` - Local vector database
- `sentence-transformers` - Embedding models
- `numpy` - Numerical operations
- Vector memory implementation

**Use Cases**:
- RAG (Retrieval-Augmented Generation)
- Semantic search
- Long-term memory with embeddings
- Knowledge base integration

#### 4. All Optional Dependencies (`all`)

```bash
pip install agenkit[all]
```

**Includes**: All of the above extras (aws, redis, vector)

**Use Cases**:
- Full-featured development environment
- Production deployments with all integrations
- Exploration and prototyping

### Combining Extras

Install multiple extras together:

```bash
pip install agenkit[aws,redis]
pip install agenkit[vector,redis]
```

### Development Installation

For contributors:

```bash
# Clone repository
git clone https://github.com/scttfrdmn/agenkit.git
cd agenkit

# Install with dev dependencies
pip install -e '.[all,dev]'
```

**Dev extras include**:
- `pytest` - Testing framework
- `pytest-asyncio` - Async test support
- `pytest-cov` - Coverage reporting
- `ruff` - Linting and formatting
- `mypy` - Type checking
- `black` - Code formatting

### Minimal Installation (No Dependencies)

For environments with strict dependency constraints:

```bash
# Core only (no LLM adapters, no external integrations)
pip install agenkit --no-deps
pip install typing-extensions  # Minimal requirement
```

**Note**: You'll need to manually install LLM client libraries as needed.

---

## TypeScript Installation Profiles

### Base Installation

```bash
npm install @agenkit/core
# or
yarn add @agenkit/core
# or
pnpm add @agenkit/core
```

**Includes**:
- Core agent interfaces
- Basic patterns
- All LLM adapters (OpenAI, Anthropic, Google, AWS Bedrock)
- Standard middleware
- gRPC transport

### Optional Dependencies

TypeScript uses `optionalDependencies` in `package.json` for runtime-optional features.

#### 1. AWS Bedrock (`@aws-sdk/client-bedrock-runtime`)

```bash
npm install @aws-sdk/client-bedrock-runtime
```

**Use Cases**:
- Use AWS Bedrock models
- Deploy on AWS Lambda
- AWS infrastructure integration

#### 2. Google Generative AI (`@google/generative-ai`)

```bash
npm install @google/generative-ai
```

**Use Cases**:
- Use Google Gemini models
- Google Cloud deployment

#### 3. OpenTelemetry (`@opentelemetry/*`)

```bash
npm install @opentelemetry/api @opentelemetry/sdk-node @opentelemetry/exporter-otlp
```

**Use Cases**:
- Production observability
- Distributed tracing
- Metrics collection
- Integration with monitoring platforms

#### 4. Redis (`redis`)

```bash
npm install redis
```

**Use Cases**:
- Distributed memory
- Checkpoint storage
- Rate limiting across instances

### All Dependencies

```bash
npm install @agenkit/core \
  @aws-sdk/client-bedrock-runtime \
  @google/generative-ai \
  @opentelemetry/api \
  @opentelemetry/sdk-node \
  redis
```

### Development Installation

```bash
# Clone repository
git clone https://github.com/scttfrdmn/agenkit.git
cd agenkit-ts

# Install all dependencies
npm install

# Run tests
npm test

# Build
npm run build
```

### Minimal Installation

The base `@agenkit/core` package includes all necessary dependencies. For minimal installs, exclude optional peer dependencies:

```bash
npm install @agenkit/core --no-optional
```

---

## Go Installation Profiles

### Base Installation

```bash
go get github.com/scttfrdmn/agenkit-go
```

**Includes**:
- Core agent interfaces
- All patterns
- LLM adapters (detected via build tags)
- Standard middleware
- In-memory storage

### Build Tags

Go uses build tags for optional features. Include/exclude features at compile time:

#### 1. AWS Bedrock (`aws`)

```bash
# Build with AWS support
go build -tags aws

# Or in code
//go:build aws
```

**Requires**:
```bash
go get github.com/aws/aws-sdk-go-v2
go get github.com/aws/aws-sdk-go-v2/service/bedrockruntime
```

**Use Cases**:
- AWS Bedrock LLMs
- AWS deployment

#### 2. OpenTelemetry (`otel`)

```bash
# Build with OpenTelemetry support
go build -tags otel

# Or in code
//go:build otel
```

**Requires**:
```bash
go get go.opentelemetry.io/otel
go get go.opentelemetry.io/otel/exporters/otlp
go get go.opentelemetry.io/otel/sdk
```

**Use Cases**:
- Production observability
- Distributed tracing
- Metrics collection

#### 3. Redis (`redis`)

```bash
# Build with Redis support
go build -tags redis

# Or in code
//go:build redis
```

**Requires**:
```bash
go get github.com/redis/go-redis/v9
```

**Use Cases**:
- Distributed memory
- Redis-backed checkpoints
- Distributed rate limiting

### Combining Build Tags

```bash
# Multiple features
go build -tags "aws,otel,redis"

# All features
go build -tags "aws,otel,redis"
```

### Production Build

Optimized binary with all features:

```bash
go build -tags "aws,otel,redis" \
  -ldflags="-s -w" \
  -trimpath \
  -o agent-server \
  ./cmd/server
```

**Flags explained**:
- `-tags`: Enable optional features
- `-ldflags="-s -w"`: Strip debug info (smaller binary)
- `-trimpath`: Remove absolute paths (reproducible builds)
- `-o`: Output binary name

### Development Setup

```bash
# Clone repository
git clone https://github.com/scttfrdmn/agenkit.git
cd agenkit-go

# Install all dependencies
go mod download

# Run tests
go test ./...

# Run tests with all build tags
go test -tags "aws,otel,redis" ./...
```

### Minimal Installation

Default installation excludes optional features:

```bash
# Core only (no AWS, no OpenTelemetry, no Redis)
go build ./...
```

Dependencies are fetched only when imported.

---

## Rust Installation Profiles

### Base Installation

```bash
cargo add agenkit
```

Or in `Cargo.toml`:

```toml
[dependencies]
agenkit = "0.46"
```

**Includes** (default features):
- Core agent traits
- Basic patterns
- Standard middleware
- In-memory storage

### Feature Flags

Rust uses Cargo feature flags for optional dependencies:

#### 1. AWS Bedrock (`aws`)

```toml
[dependencies]
agenkit = { version = "0.46", features = ["aws"] }
```

```bash
# Or via cargo add
cargo add agenkit --features aws
```

**Includes**:
- `aws-sdk-bedrockruntime`
- `aws-config`
- AWS Bedrock adapter

**Use Cases**:
- AWS Bedrock LLMs
- AWS Lambda deployment

#### 2. OpenTelemetry (`otel`)

```toml
[dependencies]
agenkit = { version = "0.46", features = ["otel"] }
```

**Includes**:
- `opentelemetry`
- `opentelemetry-otlp`
- `opentelemetry_sdk`
- `tracing-opentelemetry`

**Use Cases**:
- Production observability
- Distributed tracing
- Metrics collection

#### 3. Redis (`redis`)

```toml
[dependencies]
agenkit = { version = "0.46", features = ["redis"] }
```

**Includes**:
- `redis`
- Redis-backed memory
- Redis checkpoint storage

**Use Cases**:
- Distributed deployments
- Shared memory
- High-performance caching

#### 4. Async Runtime (`tokio` or `async-std`)

```toml
[dependencies]
agenkit = { version = "0.46", features = ["tokio"] }
# or
agenkit = { version = "0.46", features = ["async-std"] }
```

**Default**: `tokio`

**Use Cases**:
- Choose your preferred async runtime
- Integrate with existing runtime

### All Features

```toml
[dependencies]
agenkit = { version = "0.46", features = ["full"] }
```

**Includes**: `aws`, `otel`, `redis`, `tokio`

### Combining Features

```toml
[dependencies]
agenkit = { version = "0.46", features = ["aws", "otel"] }
```

### Development Setup

```bash
# Clone repository
git clone https://github.com/scttfrdmn/agenkit.git
cd agenkit-rust

# Build with all features
cargo build --all-features

# Test with all features
cargo test --all-features

# Run examples
cargo run --example reflection --features full
```

### Minimal Installation

```toml
[dependencies]
agenkit = { version = "0.46", default-features = false }
```

**Note**: Disables all optional features. You'll need to manually add LLM client libraries.

### Production Build

```bash
# Optimized release build with selected features
cargo build --release --features "aws,otel"

# Binary is in target/release/
```

---

## C++ Installation Profiles

### Base Installation

#### Using CMake (Recommended)

```cmake
# CMakeLists.txt
find_package(agenkit REQUIRED)
target_link_libraries(your_target PRIVATE agenkit::core)
```

#### Using vcpkg

```bash
vcpkg install agenkit
```

#### From Source

```bash
git clone https://github.com/scttfrdmn/agenkit.git
cd agenkit-cpp
mkdir build && cd build
cmake ..
make install
```

**Base installation includes**:
- Core agent interfaces
- Basic patterns
- Standard middleware
- In-memory storage

### CMake Options

Enable optional features at build time:

#### 1. AWS Bedrock Support

```bash
cmake -DAGENKIT_BUILD_AWS=ON ..
```

**Requires**: AWS SDK for C++

**Use Cases**:
- AWS Bedrock LLMs
- AWS deployment

#### 2. OpenTelemetry Support

```bash
cmake -DAGENKIT_BUILD_OTEL=ON ..
```

**Requires**: `opentelemetry-cpp`

**Use Cases**:
- Production observability
- Distributed tracing

#### 3. Redis Support

```bash
cmake -DAGENKIT_BUILD_REDIS=ON ..
```

**Requires**: `redis-plus-plus` or `hiredis`

**Use Cases**:
- Distributed memory
- Redis checkpoints

#### 4. Examples and Tests

```bash
# Build examples
cmake -DAGENKIT_BUILD_EXAMPLES=ON ..

# Build tests
cmake -DAGENKIT_BUILD_TESTS=ON ..

# Build documentation
cmake -DAGENKIT_BUILD_DOCS=ON ..
```

### All Features

```bash
cmake \
  -DAGENKIT_BUILD_AWS=ON \
  -DAGENKIT_BUILD_OTEL=ON \
  -DAGENKIT_BUILD_REDIS=ON \
  -DAGENKIT_BUILD_EXAMPLES=ON \
  -DAGENKIT_BUILD_TESTS=ON \
  ..
make -j$(nproc)
```

### Minimal Installation

```bash
# Core only (no optional dependencies)
cmake \
  -DAGENKIT_BUILD_AWS=OFF \
  -DAGENKIT_BUILD_OTEL=OFF \
  -DAGENKIT_BUILD_REDIS=OFF \
  ..
make install
```

### Production Build

```bash
# Optimized release build
cmake \
  -DCMAKE_BUILD_TYPE=Release \
  -DAGENKIT_BUILD_AWS=ON \
  -DAGENKIT_BUILD_OTEL=ON \
  -DCMAKE_CXX_FLAGS="-O3 -march=native" \
  ..
make -j$(nproc)
```

### Development Setup

```bash
# Clone and build with all features
git clone https://github.com/scttfrdmn/agenkit.git
cd agenkit-cpp
mkdir build && cd build

# Debug build with tests and examples
cmake \
  -DCMAKE_BUILD_TYPE=Debug \
  -DAGENKIT_BUILD_TESTS=ON \
  -DAGENKIT_BUILD_EXAMPLES=ON \
  -DAGENKIT_BUILD_DOCS=ON \
  ..
make -j$(nproc)

# Run tests
ctest --output-on-failure

# Run examples
./examples/patterns/reflection_example
```

---

## Zig Installation Profiles

### Base Installation

#### Using Zig Package Manager

```zig
// build.zig.zon
.{
    .name = "my-project",
    .version = "0.1.0",
    .dependencies = .{
        .agenkit = .{
            .url = "https://github.com/scttfrdmn/agenkit/releases/download/v0.46.0/agenkit-zig-0.46.0.tar.gz",
            .hash = "1220...", // SHA256 hash
        },
    },
}
```

#### From Source

```bash
git clone https://github.com/scttfrdmn/agenkit.git
cd agenkit-zig
zig build
```

**Base installation includes**:
- Core agent interfaces
- Basic patterns
- Standard middleware
- In-memory storage

### Build Options

Zig uses build options (passed via `-D` flags):

#### 1. AWS Bedrock Support

```bash
zig build -Daws=true
```

**Requires**: AWS SDK for Zig (automatically fetched)

**Use Cases**:
- AWS Bedrock LLMs
- AWS deployment

#### 2. OpenTelemetry Support

```bash
zig build -Dotel=true
```

**Requires**: OpenTelemetry Zig bindings (in development)

**Status**: ⚠️ Planned for v0.49.0

#### 3. Redis Support

```bash
zig build -Dredis=true
```

**Requires**: Redis Zig client (automatically fetched)

**Use Cases**:
- Distributed memory
- Redis checkpoints

#### 4. Optimization Level

```bash
# Debug (default)
zig build

# ReleaseSafe (optimized with safety checks)
zig build -Doptimize=ReleaseSafe

# ReleaseFast (maximum performance)
zig build -Doptimize=ReleaseFast

# ReleaseSmall (smallest binary size)
zig build -Doptimize=ReleaseSmall
```

### All Features

```bash
zig build \
  -Daws=true \
  -Dredis=true \
  -Doptimize=ReleaseFast
```

### Minimal Installation

```bash
# Core only (no optional features, debug mode)
zig build
```

### Production Build

```bash
# Optimized release with selected features
zig build \
  -Daws=true \
  -Dredis=true \
  -Doptimize=ReleaseFast \
  -Dtarget=x86_64-linux

# Binary is in zig-out/bin/
```

### Cross-Compilation

Zig's standout feature: effortless cross-compilation

```bash
# Linux to macOS
zig build -Dtarget=aarch64-macos

# Linux to Windows
zig build -Dtarget=x86_64-windows

# Linux to WASM
zig build -Dtarget=wasm32-wasi
```

### Development Setup

```bash
# Clone repository
git clone https://github.com/scttfrdmn/agenkit.git
cd agenkit-zig

# Build and test
zig build test

# Run examples
zig build run-example -- patterns/reflection

# Generate documentation
zig build docs
```

---

## Quick Reference Table

### Installation Commands

| Language | Base Install | All Features |
|----------|--------------|--------------|
| **Python** | `pip install agenkit` | `pip install agenkit[all]` |
| **TypeScript** | `npm install @agenkit/core` | All included in base |
| **Go** | `go get github.com/.../agenkit-go` | `go build -tags "aws,otel,redis"` |
| **Rust** | `cargo add agenkit` | `cargo add agenkit --features full` |
| **C++** | `cmake .. && make install` | `cmake -DAGENKIT_BUILD_AWS=ON ...` |
| **Zig** | `zig build` | `zig build -Daws=true -Dredis=true` |

### Optional Features Availability

| Feature | Python | TypeScript | Go | Rust | C++ | Zig |
|---------|--------|------------|----|----|-----|-----|
| **AWS Bedrock** | ✅ `[aws]` | ✅ Optional | ✅ `aws` tag | ✅ `aws` feature | ✅ CMake option | ✅ `-Daws` |
| **OpenTelemetry** | ✅ Built-in | ✅ Optional | ✅ `otel` tag | ✅ `otel` feature | ✅ CMake option | ⚠️ Planned |
| **Redis** | ✅ `[redis]` | ✅ Optional | ✅ `redis` tag | ✅ `redis` feature | ✅ CMake option | ✅ `-Dredis` |
| **Vector Store** | ✅ `[vector]` | ❌ Manual | ❌ Manual | ❌ Manual | ❌ Manual | ❌ Manual |
| **All Features** | ✅ `[all]` | ✅ Install all | ✅ All tags | ✅ `full` feature | ✅ All options | ✅ All flags |

### Build Performance

Typical build times on modern hardware (4-core, 16GB RAM):

| Language | Debug | Release | Size (stripped) |
|----------|-------|---------|-----------------|
| **Python** | N/A | N/A | ~2 MB (bytecode) |
| **TypeScript** | 5s | 8s | ~500 KB |
| **Go** | 8s | 12s | ~8 MB |
| **Rust** | 45s | 2m 30s | ~3 MB |
| **C++** | 1m | 2m | ~2 MB |
| **Zig** | 15s | 25s | ~1.5 MB |

**Note**: Times include all features. Minimal builds are faster.

---

## Best Practices

### 1. Choose the Right Profile for Your Use Case

**Development**:
- Use `[all]` (Python) or all features to avoid dependency surprises
- Enable tests and examples
- Use debug builds for better error messages

**Production**:
- Only include features you actually use
- Use release builds with optimizations
- Strip debug symbols for smaller binaries

**CI/CD**:
- Test with minimal profile to catch missing dependencies
- Test with all features to ensure integrations work
- Cache dependencies for faster builds

### 2. Document Your Dependencies

In your project's README, clearly state which Agenkit features you use:

```markdown
## Requirements

- Agenkit v0.46.0+ with AWS and Redis support:
  ```bash
  pip install agenkit[aws,redis]  # Python
  go build -tags "aws,redis"       # Go
  cargo build --features "aws,redis"  # Rust
  ```
```

### 3. Pin Versions in Production

```bash
# Python
pip install agenkit[aws]==0.46.0

# TypeScript
npm install @agenkit/core@0.46.0

# Go
go get github.com/scttfrdmn/agenkit-go@v0.46.0

# Rust
[dependencies]
agenkit = { version = "=0.46.0", features = ["aws"] }
```

### 4. Test Across Profiles

Ensure your code works with minimal dependencies:

```bash
# Python: test without extras
pip install agenkit  # No extras
python -m pytest

# Go: test without build tags
go test ./...  # No tags
```

### 5. Use Docker for Reproducible Builds

```dockerfile
# Python example
FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir agenkit[aws,otel,redis]
COPY . .
CMD ["python", "agent_server.py"]
```

---

## Troubleshooting

### Common Issues

#### 1. Missing Optional Dependency

**Error**: `ModuleNotFoundError: No module named 'boto3'`

**Solution**:
```bash
pip install agenkit[aws]  # Install AWS extra
```

#### 2. Build Tag Not Recognized (Go)

**Error**: `undefined: BedrockAdapter`

**Solution**:
```bash
go build -tags aws  # Enable AWS build tag
```

#### 3. Feature Not Enabled (Rust)

**Error**: `unresolved import 'agenkit::aws'`

**Solution**:
```toml
[dependencies]
agenkit = { version = "0.46", features = ["aws"] }
```

#### 4. CMake Can't Find Dependency (C++)

**Error**: `Could not find a package configuration file provided by "opentelemetry-cpp"`

**Solution**:
```bash
# Install dependency first
sudo apt-get install libopentelemetry-dev
# Or use vcpkg
vcpkg install opentelemetry-cpp
```

---

## Support

- **Documentation**: https://agenkit.dev
- **GitHub Issues**: https://github.com/scttfrdmn/agenkit/issues
- **Discussions**: https://github.com/scttfrdmn/agenkit/discussions

---

**Last Updated**: January 15, 2026
**Version**: v0.46.0
