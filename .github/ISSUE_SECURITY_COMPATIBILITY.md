# Security Policy and Compatibility Matrix

## Problem Statement

As Agenkit moves toward v1.0 production release, we need to establish:

1. **Security Policy** - How users report vulnerabilities and security best practices
2. **Compatibility Matrix** - Clear documentation of supported versions and platforms

These are Phase 6 requirements for production readiness.

## Proposed Solution

### Part 1: Security Policy (SECURITY.md)

Create comprehensive security documentation covering:

#### Vulnerability Reporting

```markdown
## Reporting Security Vulnerabilities

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, report them via:
- Email: security@agenkit.dev (or appropriate contact)
- GitHub Security Advisories: https://github.com/scttfrdmn/agenkit/security/advisories/new

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will respond within 48 hours and provide updates every 72 hours until resolved.
```

#### Supported Versions

```markdown
## Supported Versions

| Version | Supported          | End of Support |
| ------- | ------------------ | -------------- |
| 1.0.x   | :white_check_mark: | TBD            |
| 0.4.x   | :white_check_mark: | 2026-06-30     |
| < 0.4   | :x:                | Ended          |

Security updates will be provided for:
- Current major version (1.x)
- Previous major version (0.x) for 6 months after new major release
```

#### Security Best Practices

```markdown
## Security Best Practices

### For Users

**1. API Key Management**
- Never commit API keys to version control
- Use environment variables or secret management systems
- Rotate keys regularly
- Use separate keys for development/production

**2. Input Validation**
- Always validate and sanitize user inputs
- Use parameterized queries for database operations
- Implement rate limiting to prevent abuse

**3. Transport Security**
- Use TLS/HTTPS in production
- Validate certificates
- Use mTLS for high-security deployments

**4. LLM Security**
- Implement prompt injection defenses
- Validate LLM outputs before execution
- Use code sandboxing for code generation agents
- Monitor LLM usage for anomalies

**5. Tool Security**
- Validate tool inputs and outputs
- Implement least-privilege access
- Audit tool usage
- Sandbox dangerous operations (file access, shell commands)

### For Contributors

**1. Code Review**
- All PRs require review
- Security-sensitive changes need maintainer approval
- Run security linters (bandit, gosec)

**2. Dependency Management**
- Keep dependencies updated
- Review dependency licenses
- Use Dependabot for automatic updates
- Pin dependency versions in production

**3. Testing**
- Include security tests
- Test for common vulnerabilities (OWASP Top 10)
- Fuzz testing for parsers
```

#### Known Security Considerations

```markdown
## Known Security Considerations

### LLM-Specific Risks

**Prompt Injection**
- Risk: Malicious users can manipulate LLM behavior through crafted inputs
- Mitigation: Input sanitization, output validation, system prompts with boundaries

**Code Generation**
- Risk: LLM-generated code may contain vulnerabilities
- Mitigation: Code review, static analysis, sandboxed execution

**Data Leakage**
- Risk: Sensitive data in prompts may be logged or cached
- Mitigation: PII detection, prompt filtering, secure logging practices

**Cost Attacks**
- Risk: Malicious users trigger expensive LLM calls
- Mitigation: Rate limiting, authentication, usage quotas

### Transport Security

**Man-in-the-Middle**
- Risk: Interception of agent communication
- Mitigation: TLS/mTLS, certificate validation

**Replay Attacks**
- Risk: Captured requests replayed
- Mitigation: Request signing, nonces, timestamps

### Tool Execution

**Command Injection**
- Risk: Malicious inputs executed as shell commands
- Mitigation: Input validation, parameterized commands, sandboxing

**Path Traversal**
- Risk: Unauthorized file system access
- Mitigation: Path validation, chroot, whitelisting
```

---

### Part 2: Compatibility Matrix

Create `docs-site/compatibility.md` with comprehensive compatibility information:

#### Language and Runtime Versions

```markdown
## Language Support

### Python

| Python Version | Support Status | Notes |
|----------------|----------------|-------|
| 3.12           | ✅ Supported   | Recommended |
| 3.11           | ✅ Supported   | Recommended |
| 3.10           | ✅ Supported   | Minimum version |
| 3.9            | ⚠️  Deprecated | EOL 2025-10-05 |
| < 3.9          | ❌ Not supported | |

**Dependencies:**
- asyncio (stdlib)
- aiohttp >= 3.9.0
- protobuf >= 4.25.0
- grpcio >= 1.60.0 (optional, for gRPC)

### Go

| Go Version | Support Status | Notes |
|------------|----------------|-------|
| 1.22       | ✅ Supported   | Recommended |
| 1.21       | ✅ Supported   | Minimum version |
| 1.20       | ⚠️  Deprecated | EOL 2024-08-06 |
| < 1.20     | ❌ Not supported | |

**Dependencies:**
- golang.org/x/net >= 0.20.0
- google.golang.org/grpc >= 1.60.0
- google.golang.org/protobuf >= 1.32.0
```

#### Operating Systems

```markdown
## Operating System Support

### Python

| OS | Architecture | Support Status | Notes |
|----|--------------|----------------|-------|
| **Linux** | x86_64 | ✅ Fully supported | Primary platform |
| | ARM64 | ✅ Fully supported | Including Raspberry Pi |
| **macOS** | x86_64 | ✅ Fully supported | Intel Macs |
| | ARM64 (M1/M2) | ✅ Fully supported | Apple Silicon |
| **Windows** | x86_64 | ⚠️  Best effort | WSL2 recommended |
| | ARM64 | ❌ Not tested | |

### Go

| OS | Architecture | Support Status | Notes |
|----|--------------|----------------|-------|
| **Linux** | x86_64 | ✅ Fully supported | Primary platform |
| | ARM64 | ✅ Fully supported | |
| **macOS** | x86_64 | ✅ Fully supported | |
| | ARM64 (M1/M2) | ✅ Fully supported | |
| **Windows** | x86_64 | ✅ Fully supported | Native support |
| | ARM64 | ⚠️  Experimental | |
```

#### Transport Protocols

```markdown
## Transport Layer Compatibility

| Protocol | Python | Go | Cross-Language | Notes |
|----------|--------|-----|----------------|-------|
| **HTTP/1.1** | ✅ | ✅ | ✅ | Default |
| **HTTP/2** | ✅ | ✅ | ✅ | Recommended |
| **HTTP/3 (QUIC)** | ✅ | ✅ | ✅ | Experimental |
| **gRPC** | ✅ | ✅ | ✅ | Production-ready |
| **WebSocket** | ✅ | ✅ | ✅ | Production-ready |

### Cross-Language Support

| Client → Server | Status | Notes |
|----------------|--------|-------|
| Python → Python | ✅ | All transports |
| Python → Go | ✅ | All transports |
| Go → Python | ✅ | All transports |
| Go → Go | ✅ | All transports |
```

#### LLM Provider Compatibility

```markdown
## LLM Provider Support

| Provider | Python | Go | Notes |
|----------|--------|-----|-------|
| **Anthropic (Claude)** | ✅ | ✅ | Requires API key |
| **OpenAI (GPT)** | ✅ | ✅ | Requires API key |
| **Google Gemini** | ✅ | ⏳ | Python only (for now) |
| **AWS Bedrock** | ✅ | ⏳ | Python only (for now) |
| **Ollama (Local)** | ✅ | ⏳ | Python only (for now) |
| **LiteLLM (100+)** | ✅ | ⏳ | Python only (for now) |

### Model Versions Tested

| Provider | Model | Last Tested | Status |
|----------|-------|-------------|--------|
| Anthropic | claude-3-5-sonnet-20241022 | 2025-11-13 | ✅ |
| Anthropic | claude-3-haiku-20240307 | 2025-11-13 | ✅ |
| OpenAI | gpt-4o | 2025-11-13 | ✅ |
| OpenAI | gpt-4o-mini | 2025-11-13 | ✅ |
| Gemini | gemini-2.0-flash-exp | 2025-11-13 | ✅ |
| Bedrock | anthropic.claude-3-5-sonnet-20241022-v2:0 | 2025-11-13 | ✅ |
| Ollama | llama2 | 2025-11-13 | ✅ |
```

#### Middleware Compatibility

```markdown
## Middleware Support

| Middleware | Python | Go | Cross-Language | Notes |
|------------|--------|-----|----------------|-------|
| **Retry** | ✅ | ✅ | ✅ | Exponential backoff |
| **Circuit Breaker** | ✅ | ✅ | ✅ | 3-state FSM |
| **Timeout** | ✅ | ✅ | ✅ | Context-based |
| **Rate Limiter** | ✅ | ✅ | ✅ | Token bucket |
| **Caching** | ✅ | ✅ | ✅ | LRU + TTL |
| **Batching** | ✅ | ✅ | ✅ | Configurable window |
| **Tracing** | ✅ | ✅ | ✅ | OpenTelemetry |
| **Metrics** | ✅ | ✅ | ✅ | Prometheus |
```

#### Container and Orchestration

```markdown
## Container Support

| Platform | Support Status | Notes |
|----------|----------------|-------|
| **Docker** | ✅ Fully supported | Multi-stage builds |
| **Docker Compose** | ✅ Fully supported | Dev and test environments |
| **Kubernetes** | ✅ Fully supported | Helm charts available |
| **Podman** | ⚠️  Community tested | Should work |
| **containerd** | ⚠️  Community tested | Direct usage |

### Kubernetes Versions

| Version | Support Status | Notes |
|---------|----------------|-------|
| 1.29 | ✅ Supported | Current |
| 1.28 | ✅ Supported | |
| 1.27 | ✅ Supported | |
| < 1.27 | ⚠️  May work | Not tested |
```

#### Observability Stack

```markdown
## Observability Compatibility

### Tracing

| Backend | Protocol | Status | Notes |
|---------|----------|--------|-------|
| **Jaeger** | OTLP/gRPC | ✅ | Recommended |
| **Zipkin** | OTLP/HTTP | ✅ | |
| **Tempo** | OTLP/gRPC | ✅ | Grafana |
| **Datadog** | OTLP/gRPC | ✅ | Via agent |
| **New Relic** | OTLP/gRPC | ✅ | |

### Metrics

| Backend | Protocol | Status | Notes |
|---------|----------|--------|-------|
| **Prometheus** | /metrics | ✅ | Native |
| **Grafana** | PromQL | ✅ | Dashboards |
| **Datadog** | StatsD | ⚠️ | Via agent |
| **CloudWatch** | API | ⚠️ | Via exporter |

### Logging

| Format | Status | Notes |
|--------|--------|-------|
| **JSON** | ✅ | Structured logging |
| **Text** | ✅ | Human-readable |
| **OTLP** | ⚠️ | Experimental |
```

---

## Implementation Considerations

**Scope:**
- [ ] Python compatibility
- [ ] Go compatibility
- [ ] Documentation only (no code changes)
- [ ] Backward compatible

**Affected Components:**
- [ ] Security policy document
- [ ] Compatibility matrix
- [ ] CI/CD (test matrix)

**Complexity Estimate:**
- [x] Small (< 1 day)
- [ ] Medium (1-3 days)
- [ ] Large (> 3 days)

## Acceptance Criteria

### Security Policy
- [ ] SECURITY.md created
- [ ] Vulnerability reporting process defined
- [ ] Supported versions documented
- [ ] Security best practices for users
- [ ] Security guidelines for contributors
- [ ] Known security considerations listed
- [ ] Linked from README.md
- [ ] Linked from CONTRIBUTING.md

### Compatibility Matrix
- [ ] docs-site/compatibility.md created
- [ ] Python version support table
- [ ] Go version support table
- [ ] Operating system compatibility
- [ ] Transport protocol compatibility
- [ ] LLM provider compatibility
- [ ] Middleware compatibility
- [ ] Container/K8s compatibility
- [ ] Observability stack compatibility
- [ ] Regular update schedule defined
- [ ] Linked from documentation site nav

### Additional
- [ ] Update CI/CD to test compatibility matrix
- [ ] Add Dependabot configuration
- [ ] Set up security scanning (bandit, gosec)
- [ ] Configure GitHub Security Advisories

## Related

- Phase 6: Community & Polish
- Part of v1.0 production readiness

## Priority

**Medium** - Required for v1.0 but not blocking current development

## Labels

`documentation`, `security`, `phase-6`, `help-wanted`
