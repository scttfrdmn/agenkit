# AgentKit Compatibility Matrix

Comprehensive compatibility information for AgentKit across languages, platforms, and dependencies.

**Last Updated**: November 2025
**Version**: v0.9.0

---

## Quick Reference

| Component | Python Support | Go Support | Status |
|-----------|---------------|------------|--------|
| **Core Framework** | ✅ Full | ✅ Full | Production Ready |
| **HTTP Transport** | ✅ Full | ✅ Full | Production Ready |
| **WebSocket Transport** | ✅ Full | ✅ Full | Production Ready |
| **gRPC Transport** | ✅ Full | ✅ Full | Production Ready |
| **Middleware** | ✅ 8 types | ✅ 8 types | 100% Parity |
| **Observability** | ✅ Full | ✅ Full | Production Ready |

---

## Language Support

### Python

| Python Version | Support Status | Notes |
|----------------|---------------|-------|
| **3.13** | ✅ **Recommended** | CI default; full suite verified |
| **3.12** | ✅ Supported | Minimum supported version (`requires-python = ">=3.12"`) |
| 3.14 | ✅ Verified | Full suite passes; not yet the CI default |
| < 3.12 | ❌ Not supported | Below `requires-python` floor |

**Key Dependencies**:
```
aiohttp >= 3.9.0
grpcio >= 1.60.0
protobuf >= 4.25.0
websockets >= 12.0
opentelemetry-api >= 1.20.0
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
| **1.22** | ✅ **Recommended** | Latest features |
| **1.21** | ✅ **Recommended** | Stable, well-tested |
| **1.20** | ✅ Supported | Minimum supported version |
| < 1.20 | ❌ Not supported | Missing generics, workspace support |

**Key Dependencies**:
```
google.golang.org/grpc v1.76.0
google.golang.org/protobuf v1.36.10
github.com/gorilla/websocket v1.5.3
go.opentelemetry.io/otel v1.32.0
```

**Go Feature Requirements**:
- ✅ Generics (Go 1.18+)
- ✅ Go modules
- ✅ Context package
- ✅ Goroutines & channels

---

## Platform Support

### Operating Systems

| Platform | Python | Go | Notes |
|----------|--------|----|----|
| **Linux** | ✅ Full | ✅ Full | Primary development platform |
| **macOS** | ✅ Full | ✅ Full | Intel & Apple Silicon (M1/M2/M3) |
| **Windows** | ✅ Full | ✅ Full | Windows 10+ (WSL2 recommended) |
| **FreeBSD** | ⚠️ Untested | ✅ Full | Should work, community support |
| **ARM64** | ✅ Full | ✅ Full | Raspberry Pi, AWS Graviton |

### Container Platforms

| Platform | Support | Notes |
|----------|---------|-------|
| **Docker** | ✅ Full | Official images available |
| **Kubernetes** | ✅ Full | Production manifests included |
| **Docker Compose** | ✅ Full | Full stack orchestration |
| **Podman** | ✅ Compatible | OCI-compliant |
| **AWS ECS/Fargate** | ✅ Compatible | Standard Docker images work |
| **Azure ACI** | ✅ Compatible | Standard Docker images work |
| **Google Cloud Run** | ✅ Compatible | HTTP/gRPC support built-in |

### Cloud Platforms

| Platform | Deployment | Notes |
|----------|-----------|-------|
| **AWS** | ✅ Full | ECS, EKS, Lambda, EC2 |
| **Google Cloud** | ✅ Full | GKE, Cloud Run, GCE |
| **Azure** | ✅ Full | AKS, Container Apps, VMs |
| **Heroku** | ✅ Compatible | Standard buildpacks |
| **Railway** | ✅ Compatible | Docker-based deployment |
| **Fly.io** | ✅ Compatible | Global edge deployment |
| **Vercel/Netlify** | ⚠️ Partial | Serverless functions only |

---

## Core Features

### Feature Parity Matrix

| Feature | Python | Go | Status |
|---------|--------|-----|--------|
| **Core Interfaces** |
| Agent ABC | ✅ | ✅ | 100% parity |
| Message | ✅ | ✅ | 100% parity |
| Tool | ✅ | ✅ | 100% parity |
| **Adapters** |
| LocalAgent | ✅ | ✅ | 100% parity |
| RemoteAgent | ✅ | ✅ | 100% parity |
| HTTPAgent | ✅ | ✅ | 100% parity |
| GRPCServer | ✅ | ✅ | 100% parity |
| **Transports** |
| HTTP/1.1 | ✅ | ✅ | 100% parity |
| HTTP/2 (h2c) | ✅ | ✅ | 100% parity |
| HTTP/3 (QUIC) | ✅ | ✅ | 100% parity |
| WebSocket | ✅ | ✅ | 100% parity |
| gRPC | ✅ | ✅ | 100% parity |
| Unix Sockets | ✅ | ✅ | 100% parity |
| **Middleware** |
| Retry | ✅ | ✅ | 100% parity |
| Circuit Breaker | ✅ | ✅ | 100% parity |
| Rate Limiter | ✅ | ✅ | 100% parity |
| Timeout | ✅ | ✅ | 100% parity |
| Caching | ✅ | ✅ | 100% parity |
| Batching | ✅ | ✅ | 100% parity |
| Metrics | ✅ | ✅ | 100% parity |
| Tracing | ✅ | ✅ | 100% parity |
| **Composition** |
| Sequential | ✅ | ✅ | 100% parity |
| Parallel | ✅ | ✅ | 100% parity |
| Fallback | ✅ | ✅ | 100% parity |
| Conditional | ✅ | ✅ | 100% parity |
| **Observability** |
| OpenTelemetry | ✅ | ✅ | 100% parity |
| Distributed Tracing | ✅ | ✅ | 100% parity |
| Prometheus Metrics | ✅ | ✅ | 100% parity |
| Structured Logging | ✅ | ✅ | 100% parity |
| W3C Trace Context | ✅ | ✅ | Cross-language support |
| **Memory & State** |
| InMemory | ✅ | ✅ | 100% parity |
| Redis | ✅ | ✅ | 100% parity |
| Vector Store | ✅ | ✅ | 100% parity |
| Checkpointing | ✅ | ✅ | 100% parity |
| **Cost Management** |
| Cost Tracking | ✅ | ✅ | 100% parity |
| Budget Limiter | ✅ | ✅ | 100% parity |
| Model Optimizer | ✅ | ⚠️ | Python recommended for LLMs |
| **LLM Adapters** |
| OpenAI | ✅ | ✅ | 100% parity |
| Anthropic | ✅ | ✅ | 100% parity |
| Custom Providers | ✅ | ✅ | Plugin system |

**Legend**:
- ✅ Full support
- ⚠️ Partial support or recommended alternative
- ❌ Not supported

---

## Transport Protocol Details

### HTTP

| Feature | Python | Go | Notes |
|---------|--------|-----|----|
| **HTTP/1.1** | ✅ | ✅ | Default, widest compatibility |
| **HTTP/2 (h2c)** | ✅ | ✅ | Cleartext, no TLS required |
| **HTTP/2 (TLS)** | ✅ | ✅ | HTTPS with connection multiplexing |
| **HTTP/3 (QUIC)** | ✅ | ✅ | UDP-based, TLS 1.3 required |
| **Streaming** | ✅ | ✅ | Server-sent events, chunked encoding |
| **Keep-Alive** | ✅ | ✅ | Connection pooling |
| **TLS 1.3** | ✅ | ✅ | Recommended |
| **TLS 1.2** | ✅ | ✅ | Minimum supported |
| **Client Certificates** | ✅ | ✅ | mTLS support |

**Performance**:
- Python: ~1.02ms avg latency (HTTP/1.1)
- Go: ~0.055ms avg latency (HTTP/1.1)
- **Go is 18.5x faster** for HTTP transport

### WebSocket

| Feature | Python | Go | Notes |
|---------|--------|-----|----|
| **RFC 6455 Compliance** | ✅ | ✅ | Full WebSocket standard |
| **Binary Frames** | ✅ | ✅ | Efficient message encoding |
| **Text Frames** | ✅ | ✅ | JSON support |
| **Ping/Pong** | ✅ | ✅ | Keepalive mechanism |
| **Compression** | ✅ | ✅ | permessage-deflate |
| **Auto-Reconnect** | ✅ | ✅ | Exponential backoff |
| **TLS (WSS)** | ✅ | ✅ | Secure WebSocket |
| **Subprotocols** | ✅ | ✅ | Custom protocols |

**Libraries**:
- Python: `websockets >= 12.0` (asyncio-native)
- Go: `github.com/gorilla/websocket v1.5.3`

### gRPC

| Feature | Python | Go | Notes |
|---------|--------|-----|----|
| **Unary RPC** | ✅ | ✅ | Single request/response |
| **Server Streaming** | ✅ | ✅ | One request, stream responses |
| **Client Streaming** | ✅ | ✅ | Stream requests, one response |
| **Bidirectional Streaming** | ✅ | ✅ | Both directions stream |
| **Protocol Buffers** | ✅ | ✅ | Efficient serialization |
| **HTTP/2 Multiplexing** | ✅ | ✅ | Multiple RPCs per connection |
| **Metadata** | ✅ | ✅ | Headers/trailers |
| **Deadlines** | ✅ | ✅ | Request timeout propagation |
| **Cancellation** | ✅ | ✅ | Context-based |
| **TLS** | ✅ | ✅ | Encrypted communication |

**Libraries**:
- Python: `grpcio >= 1.60.0`
- Go: `google.golang.org/grpc v1.76.0`

---

## Middleware Compatibility

### Retry Middleware

| Feature | Python | Go | Compatible |
|---------|--------|-----|-----------|
| Exponential Backoff | ✅ | ✅ | ✅ |
| Max Attempts | ✅ | ✅ | ✅ |
| Jitter | ✅ | ✅ | ✅ |
| Retryable Errors | ✅ | ✅ | ✅ |
| Metrics | ✅ | ✅ | ✅ |

**Test Coverage**: 10 tests (Python), 10 tests (Go) - 100% parity

### Circuit Breaker Middleware

| Feature | Python | Go | Compatible |
|---------|--------|-----|-----------|
| CLOSED/OPEN/HALF_OPEN | ✅ | ✅ | ✅ |
| Failure Threshold | ✅ | ✅ | ✅ |
| Recovery Timeout | ✅ | ✅ | ✅ |
| Success Threshold | ✅ | ✅ | ✅ |
| Metrics | ✅ | ✅ | ✅ |

**Test Coverage**: 8 tests (Python), 8 tests (Go) - 100% parity

### Rate Limiter Middleware

| Feature | Python | Go | Compatible |
|---------|--------|-----|-----------|
| Token Bucket Algorithm | ✅ | ✅ | ✅ |
| Configurable Rate | ✅ | ✅ | ✅ |
| Burst Capacity | ✅ | ✅ | ✅ |
| Wait-based Throttling | ✅ | ✅ | ✅ |
| Metrics | ✅ | ✅ | ✅ |

**Test Coverage**: 8 tests (Python), 8 tests (Go) - 100% parity

### Caching Middleware

| Feature | Python | Go | Compatible |
|---------|--------|-----|-----------|
| LRU Eviction | ✅ | ✅ | ✅ |
| TTL Expiration | ✅ | ✅ | ✅ |
| Custom Key Generator | ✅ | ✅ | ✅ |
| Cache Invalidation | ✅ | ✅ | ✅ |
| Metrics | ✅ | ✅ | ✅ |

**Test Coverage**: 17 tests (Python), 17 tests (Go) - 100% parity

### Timeout Middleware

| Feature | Python | Go | Compatible |
|---------|--------|-----|-----------|
| Request Timeout | ✅ | ✅ | ✅ |
| Configurable Duration | ✅ | ✅ | ✅ |
| Graceful Cancellation | ✅ | ✅ | ✅ |
| Metrics | ✅ | ✅ | ✅ |

**Test Coverage**: 18 tests (Python), 15 tests (Go) - Full coverage

### Batching Middleware

| Feature | Python | Go | Compatible |
|---------|--------|-----|-----------|
| Size-based Batching | ✅ | ✅ | ✅ |
| Time-based Batching | ✅ | ✅ | ✅ |
| Partial Failure Handling | ✅ | ✅ | ✅ |
| Individual Response Distribution | ✅ | ✅ | ✅ |
| Metrics | ✅ | ✅ | ✅ |

**Test Coverage**: 21 tests (Python), 15 tests (Go) - Full coverage

---

## Observability Compatibility

### OpenTelemetry Support

| Component | Python | Go | Cross-Language |
|-----------|--------|-----|----------------|
| **Tracing** |
| W3C Trace Context | ✅ | ✅ | ✅ Full propagation |
| Span Creation | ✅ | ✅ | ✅ Compatible |
| Span Attributes | ✅ | ✅ | ✅ Compatible |
| Parent-Child Relationships | ✅ | ✅ | ✅ Cross-language |
| OTLP Exporter | ✅ | ✅ | ✅ Compatible |
| Console Exporter | ✅ | ✅ | ✅ Compatible |
| **Metrics** |
| Prometheus Format | ✅ | ✅ | ✅ Compatible |
| Counters | ✅ | ✅ | ✅ Compatible |
| Histograms | ✅ | ✅ | ✅ Compatible |
| Gauges | ✅ | ✅ | ✅ Compatible |
| OTLP Metrics | ✅ | ✅ | ✅ Compatible |
| **Logging** |
| Structured Logging | ✅ | ✅ | ✅ Compatible |
| JSON Format | ✅ | ✅ | ✅ Compatible |
| Trace Correlation | ✅ | ✅ | ✅ Cross-language |
| Log Levels | ✅ | ✅ | ✅ Compatible |

**Test Coverage**:
- Python: 25 tests (tracing, metrics, logging)
- Go: 28 tests (tracing, metrics, logging)
- Cross-Language: 7 integration tests

### Monitoring Stack Compatibility

| Stack | Python | Go | Notes |
|-------|--------|-----|-------|
| **Jaeger** | ✅ | ✅ | Distributed tracing |
| **Prometheus** | ✅ | ✅ | Metrics collection |
| **Grafana** | ✅ | ✅ | Dashboards & visualization |
| **Zipkin** | ✅ | ✅ | Alternative to Jaeger |
| **New Relic** | ✅ | ✅ | OTLP exporter |
| **Datadog** | ✅ | ✅ | OTLP exporter |
| **Honeycomb** | ✅ | ✅ | OTLP exporter |
| **Elastic APM** | ✅ | ✅ | OTLP exporter |

---

## Dependencies

### Python Required Dependencies

```python
# Core
aiohttp >= 3.9.0           # HTTP client/server
typing-extensions >= 4.9.0  # Backports for older Python

# Transports
grpcio >= 1.60.0           # gRPC support
protobuf >= 4.25.0         # Protocol Buffers
websockets >= 12.0         # WebSocket support

# Observability
opentelemetry-api >= 1.20.0        # OpenTelemetry tracing
opentelemetry-sdk >= 1.20.0        # OpenTelemetry SDK
opentelemetry-exporter-otlp >= 1.20.0  # OTLP exporter

# Optional
redis >= 5.0.0             # Redis memory backend
numpy >= 1.24.0            # Vector operations
```

### Go Required Dependencies

```go
// Core
(standard library only)

// Transports
google.golang.org/grpc v1.76.0              // gRPC support
google.golang.org/protobuf v1.36.10         // Protocol Buffers
github.com/gorilla/websocket v1.5.3         // WebSocket support
github.com/quic-go/quic-go v0.42.0          // QUIC/HTTP3 support

// Observability
go.opentelemetry.io/otel v1.32.0                     // OpenTelemetry
go.opentelemetry.io/otel/exporters/prometheus v0.54.0 // Prometheus
go.opentelemetry.io/otel/exporters/otlp/otlptrace v1.32.0 // OTLP

// Optional
github.com/redis/go-redis/v9 v9.0.5         // Redis memory
```

### Dependency Version Compatibility

| Dependency | Minimum | Recommended | Maximum Tested |
|------------|---------|-------------|----------------|
| **Python** |
| Python | 3.12 | 3.13 | 3.14 |
| aiohttp | 3.9.0 | 3.9.x | 3.9.5 |
| grpcio | 1.60.0 | 1.60.x | 1.66.0 |
| websockets | 12.0 | 12.0 | 13.0 |
| opentelemetry | 1.20.0 | 1.20.x | 1.30.0 |
| **Go** |
| Go | 1.20 | 1.21-1.22 | 1.22 |
| grpc | 1.60.0 | 1.70.x | 1.76.0 |
| protobuf | 1.31.0 | 1.36.x | 1.36.10 |
| otel | 1.20.0 | 1.30.x | 1.32.0 |

---

## Performance Characteristics

### Latency by Transport (Go vs Python)

| Transport | Python Latency | Go Latency | Go Speedup |
|-----------|---------------|------------|------------|
| HTTP/1.1 | 1.02 ms | 0.055 ms | **18.5x faster** |
| HTTP/2 | 1.01 ms | 0.057 ms | **17.7x faster** |
| HTTP/3 | 3.47 ms | 0.181 ms | **19.2x faster** |
| WebSocket | ~513 ms* | ~502 ms* | Similar |
| gRPC | 0.95 ms | 0.048 ms | **19.8x faster** |

\* For 10 chunks @ 50ms delay (streaming scenario)

### Middleware Overhead

| Middleware | Python Overhead | Go Overhead |
|------------|----------------|-------------|
| Retry | 0.7µs | 0.08µs |
| Circuit Breaker | 14.5µs | 0.74µs |
| Rate Limiter | 6.1µs | 0.56µs |
| Timeout | 2.1µs | 1.5µs |
| Caching (miss) | 5.8µs | 0.89µs |
| Batching | 12µs | 1.3µs |

**Note**: In production with LLM calls (100-1000ms), middleware overhead is <0.01% of total time.

### Concurrent Performance

| Scenario | Python Throughput | Go Throughput | Go Advantage |
|----------|------------------|---------------|--------------|
| 1 concurrent | ~980 req/s | ~18,200 req/s | 18.6x |
| 10 concurrent | ~2,450 req/s | ~45,000 req/s | 18.4x |
| 50 concurrent | ~3,200 req/s | ~58,000 req/s | 18.1x |
| 100 concurrent | ~3,400 req/s | ~62,000 req/s | 18.2x |

---

## Breaking Changes & Migration

### v0.9.0 → v1.0.0 (Planned)

**Breaking Changes**:
- None expected. v1.0.0 will be backward compatible with v0.9.x

**Deprecations**:
- Python 3.9 support (end of life Oct 2025)

**New Requirements**:
- Go 1.21+ (for workspace support)
- Python 3.10+ (for match statements, improved typing)

### Upgrade Path

```bash
# Python
pip install --upgrade agenkit>=1.0.0

# Go
go get github.com/scttfrdmn/agenkit-go@v1.0.0
```

---

## Known Limitations

### Platform-Specific Issues

**Windows**:
- Unix sockets not supported (Windows-specific implementation planned)
- QUIC/HTTP3 requires Windows 10 1809+ or Windows Server 2019+

**macOS ARM (M1/M2/M3)**:
- All features fully supported
- Native ARM64 builds available

**Linux**:
- No known limitations
- Recommended for production deployments

### Feature-Specific Limitations

**HTTP/3 (QUIC)**:
- Requires UDP port access (may be blocked by some firewalls)
- TLS 1.3 is mandatory (no plaintext QUIC)
- Certificate validation more strict than HTTP/1.1

**gRPC**:
- Binary protocol (not browser-compatible without grpc-web)
- Requires protobuf schema generation

**WebSocket**:
- Stateful connections (requires connection management)
- Some proxies/load balancers may not support

---

## Testing Compatibility

### Test Coverage

| Category | Python Tests | Go Tests | Total |
|----------|-------------|----------|-------|
| **Core** | 45 | 38 | 83 |
| **Transports** | 62 | 53 | 115 |
| **Middleware** | 90 | 81 | 171 |
| **Composition** | 32 | 10 | 42 |
| **Observability** | 25 | 28 | 53 |
| **Integration** | 47 | 0 | 47 |
| **Chaos Engineering** | 53 | 0 | 53 |
| **Property-Based** | 37 | 0 | 37 |
| **Total** | **391** | **210** | **601** |

### CI/CD Testing Matrix

**GitHub Actions** (single configuration, not a matrix — local `make test` is the
primary gate and CI is a safety net; see CLAUDE.md):
- Python: 3.13
- Go: 1.25
- OS: Ubuntu (`ubuntu-latest` for pull requests, self-hosted Linux for push/schedule)

**Test Execution**:
- Average runtime: ~5-8 minutes
- Parallel execution across matrix
- Automatic test parity checking (warns if >30% divergence)

---

## Support & Maintenance

### Version Support Policy

| Version Type | Support Duration | Updates |
|-------------|-----------------|---------|
| **Latest Stable** | Ongoing | Bug fixes, security, features |
| **Previous Major** | 6 months | Critical security only |
| **Beta (0.9.x)** | Until v1.0.0 | Bug fixes, security |
| **Pre-release (<0.9)** | No support | Upgrade recommended |

### Release Cadence

- **Major releases** (x.0.0): Annual, with breaking changes
- **Minor releases** (0.x.0): Quarterly, new features
- **Patch releases** (0.0.x): As needed, bug fixes & security

### Deprecation Policy

Features marked for deprecation:
1. Announced 6 months before removal
2. Warnings added to documentation and logs
3. Migration guide provided
4. Removed in next major version

---

## Getting Help

### Compatibility Issues

If you encounter compatibility problems:

1. **Check this document** for known limitations
2. **Search GitHub Issues**: https://github.com/scttfrdmn/agenkit/issues
3. **Ask in Discussions**: https://github.com/scttfrdmn/agenkit/discussions
4. **Report a bug**: Include OS, versions, and error details

### Version-Specific Information

```bash
# Check installed versions
python -c "import agenkit; print(agenkit.__version__)"
go list -m github.com/scttfrdmn/agenkit-go

# Check Python/Go versions
python --version
go version

# Check dependency versions
pip show agenkit grpcio aiohttp
go list -m all | grep -E "grpc|otel|websocket"
```

---

**Need more information?**
See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup or [SECURITY.md](SECURITY.md) for security considerations.

**Last Updated**: November 2025
**Maintainers**: AgentKit Core Team
