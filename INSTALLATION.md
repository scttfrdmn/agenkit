# Agenkit Installation Guide

Complete guide to installing Agenkit with the right dependencies for your use case.

## Quick Start

### Core Installation (Minimal)

```bash
pip install agenkit
```

This installs the core framework with essential dependencies:
- HTTP/2 and WebSocket support
- gRPC and Protocol Buffers
- OpenTelemetry (tracing, metrics, logging)
- Scientific computing (NumPy, SciPy, scikit-learn)

**Use this when**: You only need core patterns, middleware, and observability.

---

## LLM Provider Extras

Install only the LLM providers you need:

### Individual Providers

```bash
# OpenAI (GPT-4, GPT-3.5, etc.)
pip install agenkit[openai]

# Anthropic (Claude 3.5)
pip install agenkit[anthropic]

# AWS Bedrock (Claude, Titan, etc.)
pip install agenkit[aws]

# Google AI (Gemini)
pip install agenkit[google]

# Ollama (Local models)
pip install agenkit[ollama]

# LiteLLM (100+ providers unified)
pip install agenkit[litellm]
```

### Multiple Providers

Combine providers with commas:

```bash
# OpenAI + Anthropic
pip install agenkit[openai,anthropic]

# AWS + Google
pip install agenkit[aws,google]

# Local + Cloud
pip install agenkit[ollama,openai]
```

### All Providers

```bash
pip install agenkit[all-providers]
```

Includes: OpenAI, Anthropic, AWS Bedrock, Google Gemini, Ollama, LiteLLM

---

## Memory Backends

### Redis Memory

For production-grade distributed memory:

```bash
pip install agenkit[redis]
```

**Enables**:
- `RedisMemory` - Distributed memory backend
- Multi-process agent coordination
- Persistent conversation history

### Vector Memory

Vector memory is included in core (uses NumPy/scikit-learn).

```bash
# No extra installation needed!
pip install agenkit
```

**Enables**:
- `VectorMemory` - Similarity-based memory
- `InMemory` - In-process memory
- `EndlessMemory` - Unlimited context window

---

## Common Combinations

### Production AWS Deployment

```bash
pip install agenkit[aws,redis]
```

Includes: AWS Bedrock + Redis for distributed memory

### Full-Stack Development

```bash
pip install agenkit[all-providers,redis]
```

Includes: All LLM providers + Redis

### Local Development

```bash
pip install agenkit[ollama]
```

Includes: Ollama for local model testing

### Multi-Cloud Setup

```bash
pip install agenkit[openai,aws,google]
```

Includes: OpenAI, AWS Bedrock, Google Gemini

---

## Development Installation

### For Contributing

```bash
# Clone repository
git clone https://github.com/scttfrdmn/agenkit.git
cd agenkit

# Install in editable mode with all dev tools
pip install -e ".[dev,all]"
```

**Includes**:
- All testing tools (pytest, pytest-cov, pytest-xdist, hypothesis)
- All linters (mypy, ruff, black, bandit, pylint)
- All LLM providers
- All memory backends
- All observability tools

### For Testing

```bash
pip install -e ".[test,all-providers]"
```

**Includes**:
- pytest suite
- All LLM providers (for integration tests)

### For Benchmarking

```bash
pip install -e ".[benchmarks,all-providers]"
```

**Includes**:
- pytest-benchmark
- All LLM providers

---

## Docker Installation

### Official Image

```bash
docker pull agenkit/agenkit:latest
```

### Build from Source

```bash
git clone https://github.com/scttfrdmn/agenkit.git
cd agenkit
docker build -t agenkit .
```

### Docker Compose

See `examples/deployment/docker-compose/` for production-ready configurations with:
- Prometheus metrics
- Grafana dashboards
- Jaeger tracing
- Redis memory backend

---

## Platform-Specific Notes

### macOS (Apple Silicon)

```bash
# Standard installation works
pip install agenkit

# For AWS Bedrock, ensure boto3 uses ARM wheels
pip install agenkit[aws] --platform macosx_11_0_arm64
```

### Linux

```bash
# Standard installation works
pip install agenkit

# For GPU acceleration (if using local models)
pip install agenkit[ollama]
# Then configure Ollama for GPU
```

### Windows

```bash
# Standard installation works
pip install agenkit

# Note: gRPC may require Visual C++ Build Tools
# Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
```

---

## Verification

### Verify Installation

```python
import agenkit

# Check version
print(agenkit.__version__)

# Verify core imports
from agenkit import Agent, Message
from agenkit.patterns import ReActAgent, SequentialAgent
from agenkit.middleware import RetryMiddleware, CircuitBreakerMiddleware

print("✅ Agenkit installed successfully!")
```

### Verify LLM Providers

```python
# OpenAI
try:
    from agenkit.adapters import OpenAILLM
    print("✅ OpenAI available")
except ImportError:
    print("❌ OpenAI not installed: pip install agenkit[openai]")

# Anthropic
try:
    from agenkit.adapters import AnthropicLLM
    print("✅ Anthropic available")
except ImportError:
    print("❌ Anthropic not installed: pip install agenkit[anthropic]")

# AWS Bedrock
try:
    from agenkit.adapters import BedrockLLM
    print("✅ AWS Bedrock available")
except ImportError:
    print("❌ AWS Bedrock not installed: pip install agenkit[aws]")
```

### Verify Memory Backends

```python
# Core memory (always available)
from agenkit.memory import InMemory, VectorMemory, EndlessMemory
print("✅ Core memory backends available")

# Redis (optional)
try:
    from agenkit.memory import RedisMemory
    print("✅ Redis memory available")
except ImportError:
    print("❌ Redis not installed: pip install agenkit[redis]")
```

---

## Troubleshooting

### ImportError: No module named 'boto3'

**Problem**: Trying to use AWS Bedrock without installing the extra.

**Solution**:
```bash
pip install agenkit[aws]
```

### ImportError: No module named 'anthropic'

**Problem**: Trying to use Claude without installing the extra.

**Solution**:
```bash
pip install agenkit[anthropic]
```

### ImportError: No module named 'redis'

**Problem**: Trying to use RedisMemory without installing the extra.

**Solution**:
```bash
pip install agenkit[redis]
```

### ModuleNotFoundError: No module named 'grpcio'

**Problem**: gRPC installation failed (common on Windows).

**Solution**:
```bash
# Windows: Install Visual C++ Build Tools first
# Then reinstall
pip uninstall agenkit
pip install agenkit
```

### Tests fail with "No API key found"

**Problem**: Running tests that require LLM API keys.

**Solution**:
```bash
# Skip LLM API tests
pytest -m "not llm_api"

# Or set API keys
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
pytest
```

---

## Environment Variables

### Required (for LLM usage)

```bash
# OpenAI
export OPENAI_API_KEY="sk-..."

# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# AWS (if using Bedrock)
export AWS_ACCESS_KEY_ID="..."
export AWS_SECRET_ACCESS_KEY="..."
export AWS_REGION="us-west-2"

# Google (if using Gemini)
export GOOGLE_API_KEY="..."
```

### Optional (for observability)

```bash
# Redis connection (if using RedisMemory)
export REDIS_URL="redis://localhost:6379"

# OpenTelemetry exporter endpoint
export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4317"

# Service name for tracing
export OTEL_SERVICE_NAME="my-agenkit-service"
```

`init_tracing`/`InitTracing`/`initTracing` in every language (Python, Go,
TypeScript, Rust, C++) reads these as defaults when the corresponding
parameter is not explicitly supplied. **An explicit parameter always takes
precedence over the environment** — this matches the OTel SDK convention, so
the ordering is the one a caller familiar with any other OTel SDK would
expect:

```python
# Explicit values win over the environment above; omit either kwarg to fall
# back to the corresponding env var.
init_tracing(service_name="my-agenkit-service", otlp_endpoint="http://localhost:4317")
```

C++ has no `service_name` parameter at all (a structural gap, not an env var
gap), so `OTEL_SERVICE_NAME` has no effect there yet. See
[docs/OTEL_CONVENTION.md](docs/OTEL_CONVENTION.md#collector-endpoint-and-service-name)
(#771) for the full per-language table.

---

## Upgrading

### To Latest Version

```bash
pip install --upgrade agenkit
```

### With Extras

```bash
pip install --upgrade agenkit[openai,anthropic]
```

### Check Version

```bash
pip show agenkit
```

---

## Uninstallation

```bash
pip uninstall agenkit
```

This removes Agenkit but keeps dependencies. To remove all dependencies:

```bash
pip uninstall agenkit anthropic openai boto3 redis
```

---

## Quick Reference

| Use Case | Installation Command |
|----------|---------------------|
| Core only | `pip install agenkit` |
| OpenAI | `pip install agenkit[openai]` |
| Anthropic (Claude) | `pip install agenkit[anthropic]` |
| AWS Bedrock | `pip install agenkit[aws]` |
| Google Gemini | `pip install agenkit[google]` |
| Local (Ollama) | `pip install agenkit[ollama]` |
| All providers | `pip install agenkit[all-providers]` |
| Redis memory | `pip install agenkit[redis]` |
| Development | `pip install -e ".[dev,all]"` |
| Full stack | `pip install agenkit[all]` |

---

## Next Steps

After installation:

1. **Read the Tutorial**: [Getting Started](tutorials/01-getting-started.ipynb)
2. **Try Examples**: [examples/](examples/)
3. **Explore Patterns**: [Pattern Library](docs/patterns/)
4. **Join Community**: [GitHub Discussions](https://github.com/scttfrdmn/agenkit/discussions)

---

**Need help?** [Open an issue](https://github.com/scttfrdmn/agenkit/issues) or check [Discussions](https://github.com/scttfrdmn/agenkit/discussions).
