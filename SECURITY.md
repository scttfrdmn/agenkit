# Security Policy

## Supported Versions

Agenkit is currently in beta (v0.9.x). Security updates are provided for the following versions:

| Version | Supported          | Status |
| ------- | ------------------ | ------ |
| 0.9.x   | :white_check_mark: | Beta - Active development |
| < 0.9.0 | :x:                | Pre-release - Not supported |

**Note**: Once v1.0.0 is released, we will maintain security updates for:
- Latest stable version (v1.x.x)
- Previous major version for 6 months after new major release

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security issue, please report it responsibly.

### How to Report

**DO NOT** open a public GitHub issue for security vulnerabilities.

Instead, please report security issues via:

1. **GitHub Security Advisories** (Preferred):
   - Go to https://github.com/scttfrdmn/agenkit/security/advisories
   - Click "Report a vulnerability"
   - Provide detailed information about the vulnerability

2. **Email** (Alternative):
   - Send an email to: scttfrdmn@users.noreply.github.com
   - Use subject line: `[SECURITY] Brief description`
   - Include detailed reproduction steps

### What to Include

Please provide as much information as possible:

- **Type of vulnerability** (e.g., RCE, XSS, injection, DoS)
- **Affected component(s)** (e.g., HTTP transport, gRPC adapter, specific middleware)
- **Affected version(s)**
- **Step-by-step reproduction instructions**
- **Proof of concept code** (if applicable)
- **Potential impact** (what an attacker could achieve)
- **Suggested remediation** (if you have ideas)
- **Your contact information** (for follow-up questions)

### Response Timeline

We are committed to responding promptly:

- **Initial Response**: Within 48 hours of report
- **Triage & Assessment**: Within 5 business days
- **Fix Development**: Depends on severity (see below)
- **Disclosure**: Coordinated disclosure after fix is available

#### Severity-Based Response Times

| Severity | Description | Fix Timeline | Example |
|----------|-------------|--------------|---------|
| **Critical** | Remote code execution, authentication bypass | 1-3 days | Arbitrary code execution via message deserialization |
| **High** | Privilege escalation, significant data exposure | 7-14 days | SQL injection, unauthorized data access |
| **Medium** | DoS, limited information disclosure | 30 days | Resource exhaustion, verbose error messages |
| **Low** | Minor information leaks, best practice violations | 90 days | Version disclosure, non-sensitive config exposure |

### What to Expect

1. **Acknowledgment**: We'll confirm receipt of your report
2. **Communication**: We'll keep you updated on progress
3. **Credit**: With your permission, we'll credit you in the security advisory
4. **Disclosure**: We'll coordinate the public disclosure timing with you

## Security Update Process

When a security vulnerability is confirmed:

1. **Private Fix Development**: We develop and test the fix in private
2. **Security Advisory**: We draft a GitHub Security Advisory
3. **Release**: We release a patched version
4. **Notification**: We notify users via:
   - GitHub Security Advisory
   - GitHub Releases notes
   - Repository README banner (for critical issues)
5. **Public Disclosure**: After users have had time to update (typically 7-14 days for critical issues)

### Versioning for Security Releases

- **Patch releases** (e.g., 0.9.0 → 0.9.1): Security fixes, no breaking changes
- **Emergency releases**: Tagged with `-security` suffix if needed before planned release

## Security Best Practices

### For Users of Agenkit

#### 1. Input Validation

Always validate and sanitize inputs before processing:

```python
from agenkit import Message

# ❌ BAD: Accepting untrusted input directly
message = Message(role="user", content=untrusted_input)

# ✅ GOOD: Validate and sanitize
if len(untrusted_input) > MAX_LENGTH:
    raise ValueError("Input too long")
if contains_malicious_patterns(untrusted_input):
    raise ValueError("Invalid input")
message = Message(role="user", content=sanitize(untrusted_input))
```

#### 2. Network Security

Use TLS/SSL for all network communications:

```python
# ✅ Use HTTPS for HTTP transport
from agenkit.adapter.transport import HTTPTransport
transport = HTTPTransport("https://api.example.com")  # Not http://

# ✅ Use TLS for gRPC
from agenkit.adapter.transport import GRPCTransport
transport = GRPCTransport("api.example.com:443", secure=True)
```

#### 3. Authentication & Authorization

Implement proper authentication for agent endpoints:

```python
# ✅ Add authentication middleware
from agenkit.middleware import create_middleware

@create_middleware
async def auth_middleware(agent, message, next_handler):
    # Verify token/credentials
    if not verify_auth(message.metadata.get("auth_token")):
        raise PermissionError("Unauthorized")
    return await next_handler(agent, message)
```

#### 4. Rate Limiting

Protect against DoS attacks:

```python
# ✅ Use rate limiting middleware
from agenkit.middleware import RateLimitMiddleware

rate_limiter = RateLimitMiddleware(
    max_requests=100,
    window_seconds=60
)
```

#### 5. Error Handling

Avoid leaking sensitive information in errors:

```python
# ❌ BAD: Exposing internal details
except Exception as e:
    return Message(content=f"Error: {str(e)}")

# ✅ GOOD: Generic error messages
except Exception as e:
    logger.error(f"Internal error: {e}")  # Log internally
    return Message(content="An error occurred. Please try again.")
```

#### 6. Dependency Security

Keep dependencies updated:

```bash
# Check for known vulnerabilities
pip install safety
safety check

# Update dependencies regularly
pip install --upgrade agenkit
```

#### 7. Secrets Management

Never hardcode secrets:

```python
# ❌ BAD: Hardcoded API keys
api_key = "sk-1234567890abcdef"

# ✅ GOOD: Use environment variables
import os
api_key = os.environ["API_KEY"]

# ✅ BETTER: Use secrets management
from agenkit.secrets import get_secret
api_key = get_secret("api_key")
```

#### 8. Logging & Monitoring

Implement security logging:

```python
# ✅ Log security events
from agenkit.observability import SecurityLogger

security_log = SecurityLogger()
security_log.log_auth_attempt(user_id, success=False)
security_log.log_rate_limit_exceeded(client_ip)
```

### For Contributors

#### Code Security Guidelines

1. **No Hardcoded Secrets**: Never commit API keys, passwords, or tokens
2. **Input Validation**: Validate all external inputs
3. **SQL Injection Prevention**: Use parameterized queries
4. **Command Injection Prevention**: Avoid `eval()`, `exec()`, unsafe shell execution
5. **Path Traversal Prevention**: Validate file paths
6. **Dependency Auditing**: Run `safety check` before commits
7. **Security Tests**: Add tests for security-sensitive code

#### Pre-Commit Security Checks

```bash
# Run security linting
ruff check --select S  # Bandit security rules

# Check for secrets
git diff --cached | grep -i "api_key\|password\|secret\|token"

# Run security tests
pytest tests/security/
```

## Scope

### In Scope

Security issues in:

- **Core Framework**: Agent base classes, message handling, lifecycle
- **Transports**: HTTP, WebSocket, gRPC, QUIC implementations
- **Adapters**: Local, Python, Go adapters
- **Middleware**: Authentication, rate limiting, timeout, retry, caching
- **Observability**: Tracing, metrics, logging (if they expose sensitive data)
- **Dependencies**: Known vulnerabilities in dependencies

### Out of Scope

The following are generally out of scope:

- **User-Implemented Agents**: Security of agents you build (unless framework causes the issue)
- **Third-Party LLM APIs**: Vulnerabilities in OpenAI, Anthropic, etc. APIs
- **Infrastructure**: Vulnerabilities in your hosting environment
- **Social Engineering**: Phishing, social attacks
- **Physical Security**: Physical access to systems
- **Denial of Wallet**: Excessive API costs (unless caused by framework bug)

**However**, if you're unsure whether something is in scope, please report it anyway. We'll assess and provide guidance.

## Security-Related Configuration

### Recommended Production Settings

```python
# agenkit_config.py
SECURITY_SETTINGS = {
    # Network
    "use_tls": True,
    "verify_ssl_certs": True,
    "tls_min_version": "TLSv1.3",

    # Rate Limiting
    "rate_limit_enabled": True,
    "rate_limit_requests": 1000,
    "rate_limit_window": 60,

    # Timeouts
    "request_timeout": 30,
    "connection_timeout": 10,

    # Logging
    "log_level": "INFO",
    "log_sensitive_data": False,

    # Validation
    "max_message_size": 1_000_000,  # 1MB
    "validate_schemas": True,
}
```

## Known Security Considerations

### Multi-Tenancy

If running multiple tenants on shared infrastructure:
- Implement proper tenant isolation
- Use separate authentication per tenant
- Monitor for cross-tenant data leakage
- Consider resource limits per tenant

### LLM-Specific Risks

When using LLM agents:
- **Prompt Injection**: Validate and sanitize user inputs
- **Model Jailbreaking**: Implement content filtering
- **Data Leakage**: Don't include sensitive data in prompts
- **Cost Attacks**: Implement rate limiting and quotas

### Transport Security

- **HTTP**: Always use HTTPS in production
- **WebSocket**: Use WSS (WebSocket Secure)
- **gRPC**: Enable TLS
- **QUIC**: Uses TLS 1.3 by default

## Security Disclosures

Past security advisories will be listed here once v1.0.0 is released.

Currently: No security advisories (pre-1.0.0)

## Security Roadmap

Planned security enhancements:

### v0.10.0
- [ ] Built-in authentication middleware
- [ ] Input sanitization utilities
- [ ] Security-focused examples

### v1.0.0
- [ ] Comprehensive security audit
- [ ] Penetration testing
- [ ] Security-hardened defaults
- [ ] Secrets management integration
- [ ] Security documentation expansion

### Post-v1.0.0
- [ ] Bug bounty program
- [ ] Regular third-party security audits
- [ ] SOC 2 compliance documentation
- [ ] FIPS 140-2 validated cryptography

## Resources

- **OWASP Top 10**: https://owasp.org/www-project-top-ten/
- **CWE Top 25**: https://cwe.mitre.org/top25/
- **Python Security Best Practices**: https://python.readthedocs.io/en/stable/library/security_warnings.html

## Questions?

If you have questions about this security policy, please:
- Open a GitHub Discussion: https://github.com/scttfrdmn/agenkit/discussions
- Email: scttfrdmn@users.noreply.github.com (for sensitive questions only)

## Acknowledgments

We appreciate the security researchers and users who help keep Agenkit secure. Contributors who responsibly disclose vulnerabilities will be acknowledged here (with their permission).

---

**Last Updated**: 2025-01-16
**Version**: 0.9.0
