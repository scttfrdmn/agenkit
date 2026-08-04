# API Reference

Complete API documentation for all Agenkit implementations.

## Available Languages

Agenkit maintains 100% behavioral parity across all languages. Choose the implementation that best fits your deployment needs.

### [Python API](python.md)

**Status**: ✅ Complete
**Version**: 0.43.1+
**Performance**: Baseline (reference implementation)
**Best for**: Rapid prototyping, data science, ML workflows

The reference Python implementation provides the most complete feature set with the best developer experience. Fully typed, async/await support, comprehensive docstrings.

**Key Features**:
- 11+ agent patterns
- Advanced reasoning techniques (CoT, ToT, GoT, Self-Consistency)
- Production middleware (retry, circuit breaker, timeout, rate limiting)
- LLM adapters (Anthropic, OpenAI, Bedrock, Gemini)
- OpenTelemetry observability
- Memory hierarchy (working, episodic, semantic)
- Evaluation framework (benchmarks, optimizers)

[View Python API →](python.md){ .md-button .md-button--primary }

---

### [Go API](go.md)

**Status**: ✅ Complete
**Version**: 0.43.1+
**Performance**: 18x faster than Python
**Best for**: Production services, high-throughput systems, microservices

The Go implementation provides the same patterns as Python with exceptional performance. Native concurrency with goroutines, sub-millisecond orchestration, single binary deployment.

**Key Features**:
- 100% pattern parity with Python
- True parallel execution (goroutines)
- Sub-millisecond orchestration overhead
- Single binary, no runtime dependencies
- Full OpenTelemetry integration
- Production-grade middleware

[View Go API →](go.md){ .md-button }

---

### TypeScript API

**Status**: 🚧 In Progress
**Version**: 0.30.0+
**Performance**: 5x faster than Python
**Best for**: Node.js services, web applications, serverless

TypeScript implementation with full type safety and async/await support. Perfect for Node.js backends and serverless deployments.

**Key Features**:
- Full TypeScript type definitions
- Async/await throughout
- Node.js native
- Vercel/Netlify/Cloudflare Workers compatible

[Coming Soon]{ .md-button }

---

### Rust API

**Status**: 🚧 In Progress
**Version**: 0.25.0+
**Performance**: 22x faster than Python
**Best for**: Systems programming, embedded, WASM, edge computing

Rust implementation with zero-cost abstractions, memory safety, and exceptional performance. Compiles to WASM for browser deployment.

**Key Features**:
- Zero-cost abstractions
- Memory safety without GC
- WASM compilation support
- Embedded systems ready

[Coming Soon]{ .md-button }

---

### C++ API

**Status**: 🚧 In Progress
**Version**: 0.20.0+
**Performance**: 25x faster than Python
**Best for**: High-performance computing, gaming, legacy integration

C++ implementation with modern C++17/20 features. Maximum performance for HPC workloads.

**Key Features**:
- Modern C++17/20
- Zero-overhead abstractions
- CMake build system
- Legacy system integration

[Coming Soon]{ .md-button }

---

### Zig API

**Status**: 🚧 In Progress
**Version**: 0.15.0+
**Performance**: 20x faster than Python
**Best for**: Systems programming, comptime optimization, C interop

Zig implementation with compile-time optimizations and seamless C interoperability.

**Key Features**:
- Compile-time execution (comptime)
- No hidden control flow
- Manual memory management
- C library interop

[Coming Soon]{ .md-button }

---

## Cross-Language Compatibility

All Agenkit implementations maintain 100% behavioral parity through:

1. **Shared protocol definitions** (Protocol Buffers)
2. **Comprehensive cross-language tests** (500+ test cases)
3. **Standardized message format** (JSON-compatible)
4. **HTTP/gRPC transport** (seamless interop)

### Example: Python → Go Communication

```python
# Python client
from agenkit.transport import HTTPClient

go_agent = HTTPClient("http://localhost:8080")
result = await go_agent.process(message)
```

```go
// Go server
import "github.com/scttfrdmn/agenkit-go/adapter/http"

server := http.NewHTTPAgent(agent, ":8080")
if err := server.Start(ctx); err != nil {
    log.Fatal(err)
}
defer func() { _ = server.Stop() }()
```

---

## Choosing an Implementation

### Development Phase

**Use Python** for:
- Rapid prototyping
- Experimentation with LLMs
- Data science workflows
- Jupyter notebooks

### Production Deployment

**Use Go** for:
- High-throughput APIs (100K+ req/s)
- Microservices
- Long-running services
- Cost optimization (fewer instances)

**Use Rust** for:
- Edge computing
- WASM in browser
- Embedded systems
- Maximum performance

**Use TypeScript** for:
- Node.js backends
- Serverless functions
- Web applications
- Full-stack JavaScript shops

**Use C++** for:
- HPC workloads
- Game engines
- Legacy integration
- Physics simulations

---

## API Documentation Standards

All Agenkit APIs follow these conventions:

### Naming

- **Classes**: PascalCase (`Agent`, `Message`, `ToolResult`)
- **Functions**: snake_case (Python) or camelCase (TypeScript/Go)
- **Constants**: UPPER_CASE or UpperCase (language-dependent)

### Patterns

All implementations provide:
1. **Core interfaces**: `Agent`, `Message`, `Tool`
2. **Composition patterns**: Sequential, Parallel, Conditional
3. **Agent patterns**: 11+ advanced patterns
4. **Middleware**: Retry, circuit breaker, timeout, etc.
5. **Observability**: OpenTelemetry integration

### Error Handling

- **Python**: Exceptions (`AgentError`, `TimeoutError`, etc.)
- **Go**: Error returns (`error` interface)
- **Rust**: `Result<T, E>` type
- **TypeScript**: Exceptions or `Promise` rejection

---

## Need Help?

- **[Examples](../examples/index.md)**: See complete working examples
- **[Migration Guides](../../docs/migrations/)**: Migrate from other frameworks
- **[Guides](../guides/index.md)**: Language-specific guides
- **[Discord](https://discord.gg/agenkit)**: Get help from the community

---

## Contributing

Help improve Agenkit's API documentation:

1. **Report issues**: [GitHub Issues](https://github.com/scttfrdmn/agenkit/issues)
2. **Improve docs**: [Edit on GitHub](https://github.com/scttfrdmn/agenkit/tree/main/docs-site)
3. **Add examples**: [Submit PR](https://github.com/scttfrdmn/agenkit/pulls)

---

**Last Updated**: December 2025
**Version**: 0.43.1
