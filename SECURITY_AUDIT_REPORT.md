# Agenkit Security Hardening Review

**Date:** November 16, 2024  
**Scope:** Python (agenkit/) and Go (agenkit-go/) implementations  
**Assessment Level:** Comprehensive

---

## Executive Summary

This security audit examined the Agenkit codebase across 8 critical security areas. The framework demonstrates **generally good security practices** with some notable strengths and areas requiring attention before production deployment.

**Overall Risk Assessment:** **MEDIUM** - Requires hardening before production use

---

## 1. INPUT VALIDATION

### Files Examined
- `/Users/scttfrdmn/src/agenkit/agenkit/safety/input_validation.py`
- `/Users/scttfrdmn/src/agenkit/agenkit/adapters/python/http_server.py`
- `/Users/scttfrdmn/src/agenkit/agenkit/adapters/python/grpc_server.py`
- `/Users/scttfrdmn/src/agenkit/agenkit-go/adapter/http/http_server.go`
- `/Users/scttfrdmn/src/agenkit/agenkit-go/adapter/grpc/grpc_server.go`

### Current State: **GOOD with Gaps**

### Findings

#### Strengths:
1. **Prompt Injection Detection** - Python includes comprehensive `PromptInjectionDetector`
   - File: `/Users/scttfrdmn/src/agenkit/agenkit/safety/input_validation.py` (lines 26-76)
   - Pattern-based detection with 15+ dangerous patterns
   - Weighted keyword scoring (threshold: 10)
   - Covers common jailbreak attempts

2. **Message Size Limits**
   - Go WebSocket: 10 MB limit enforced (line 120, websocket_transport.go)
   - Python HTTP: 10 MB client max size (line 38, http_server.py)
   - Go HTTP: Message size validation (lines 220-300, http_transport.go)

3. **Type Validation**
   - JSON schema enforcement for messages
   - Role/content field validation

#### Gaps/Weaknesses:
1. **No Input Length Validation on Message Content**
   - Risk: DoS via extremely large message content
   - Example: 9.9 MB valid JSON but malicious content
   - Missing: Per-field character limits
   - Recommendation: Add content length limits (e.g., 100KB-1MB per message)

2. **Insufficient Content Sanitization**
   - Python: `decode_message()` accepts any content type without sanitization (http_server.py:96)
   - Go: Similar acceptance of content without pre-validation (grpc_server.go:218)
   - Missing: HTML entity encoding, SQL escaping (for database tools)

3. **Metadata Not Validated**
   - Metadata dictionaries accepted without validation
   - No key name filtering
   - Risk: Injection through metadata keys
   - Files affected: All transport implementations

4. **No Rate Limiting on Invalid Requests**
   - Invalid messages don't consume rate limit tokens
   - Enables brute-force attacks on validation logic
   - Example: Attacker sends malformed JSON at high rate

### Risk Level: **MEDIUM**

### Recommendations
1. **Implement per-field size limits:**
   ```
   - content: 100KB max
   - metadata keys: 50 chars max
   - metadata values: 10KB max
   - role: 20 chars max
   ```

2. **Add content type validation:**
   - Restrict to string/JSON/structured types only
   - Block binary data except where explicitly needed

3. **Sanitize metadata:**
   - Whitelist allowed metadata keys
   - Validate metadata value types

4. **Rate limit invalid requests:**
   - Count failed validation attempts
   - Block clients after N consecutive failures

---

## 2. AUTHENTICATION/AUTHORIZATION

### Files Examined
- `/Users/scttfrdmn/src/agenkit/agenkit-go/adapter/http/http_server.go`
- `/Users/scttfrdmn/src/agenkit/agenkit-go/adapter/grpc/grpc_server.go`
- `/Users/scttfrdmn/src/agenkit/agenkit/adapters/python/http_server.py`
- `/Users/scttfrdmn/src/agenkit/agenkit/adapters/python/grpc_transport.py`

### Current State: **MISSING - CRITICAL**

### Findings

#### No Authentication Implemented
1. **HTTP Server** (Go)
   - File: `/Users/scttfrdmn/src/agenkit/agenkit-go/adapter/http/http_server.go`
   - No authentication checks on any endpoints (lines 199-205, 208-272)
   - CORS allows all origins (line 76): `CheckOrigin: func(r *http.Request) bool { return true }`
   - Health, process, and stream endpoints accept all requests

2. **gRPC Server** (Go)
   - File: `/Users/scttfrdmn/src/agenkit/agenkit-go/adapter/grpc/grpc_server.go`
   - No authentication interceptors
   - Process/ProcessStream RPCs unauthenticated (lines 85-202)
   - No request signing/verification

3. **Python Implementations**
   - HTTP server: No auth middleware (http_server.py)
   - gRPC transport: Uses `insecure_channel` (line 73, grpc_transport.py)

#### Authorization Gaps
- No access control on agent operations
- No audit logging of who/what accessed agents
- No agent-level permissions

#### CORS Issue
- Go HTTP server: Allows all origins (http_server.go:76)
- Python HTTP server: Not restricted (http_server.py)
- Risk: Cross-site request forgery attacks

### Risk Level: **CRITICAL**

### Recommendations

1. **Implement Authentication:**
   - Go HTTP: Add middleware for Bearer token validation
   - Go gRPC: Add auth interceptor
   - Python: Add middleware for API key/JWT validation

   ```go
   // Example: Protect HTTP endpoints
   func (h *HTTPAgent) requireAuth(next http.HandlerFunc) http.HandlerFunc {
       return func(w http.ResponseWriter, r *http.Request) {
           token := r.Header.Get("Authorization")
           if !h.validateToken(token) {
               http.Error(w, "Unauthorized", http.StatusUnauthorized)
               return
           }
           next(w, r)
       }
   }
   ```

2. **Fix CORS:**
   ```go
   CheckOrigin: func(r *http.Request) bool {
       allowed := []string{"https://trusted-domain.com"}
       for _, domain := range allowed {
           if r.Header.Get("Origin") == domain {
               return true
           }
       }
       return false
   }
   ```

3. **Add Authorization checks:**
   - Before Process RPC: Check if user can access agent
   - Before tool execution: Check if user can use tool
   - Add audit logging for all access

4. **Use secure gRPC:**
   - Replace `insecure_channel` with `WithTransportCredentials`
   - Enable mTLS for Go-to-Go communication

---

## 3. NETWORK SECURITY

### Files Examined
- `/Users/scttfrdmn/src/agenkit/agenkit-go/adapter/transport/http_transport.go`
- `/Users/scttfrdmn/src/agenkit/agenkit-go/adapter/transport/websocket_transport.go`
- `/Users/scttfrdmn/src/agenkit/agenkit-go/adapter/transport/grpc_transport.go`
- `/Users/scttfrdmn/src/agenkit/agenkit/adapters/python/http_transport.py`
- `/Users/scttfrdmn/src/agenkit/agenkit/adapters/python/grpc_transport.py`

### Current State: **PARTIALLY SECURE with Critical Issue**

### Findings

#### HTTP/3 TLS Verification Issue - CRITICAL
1. **Go HTTP Transport**
   - File: `/Users/scttfrdmn/src/agenkit/agenkit-go/adapter/transport/http_transport.go` (line 98)
   - HTTP/3 client: `InsecureSkipVerify: true` for benchmarks
   - Risk: Man-in-the-middle attacks on HTTP/3
   - Status: **Documented as for testing only**, but could be left in production

2. **Go gRPC Transport**
   - File: `/Users/scttfrdmn/src/agenkit/agenkit-go/adapter/transport/grpc_transport.go` (line 75)
   - Uses `insecure.NewCredentials()` for all connections
   - Risk: Unencrypted communication, no authentication
   - Should use TLS for production

#### WebSocket Security
1. **WebSocket TLS** (Go)
   - File: `/Users/scttfrdmn/src/agenkit/agenkit-go/adapter/transport/websocket_transport.go` (line 73-75)
   - Correctly sets `InsecureSkipVerify: false` for wss://
   - Good: Certificate validation enabled

2. **WebSocket Message Size**
   - File: websocket_transport.go (line 120)
   - 10 MB limit enforced
   - Good: Prevents memory exhaustion

#### HTTP/1.1 & HTTP/2
1. **Go HTTP Transport**
   - File: http_transport.go (line 106-107)
   - HTTP/1.1: `InsecureSkipVerify: false` ✓ Good
   - HTTP/2 over TLS: Properly configured

2. **Python HTTP Transport**
   - File: `http_transport.py` (lines 71-86)
   - Relies on httpx defaults
   - httpx uses certificate verification by default ✓

#### Server TLS Configuration
- Go HTTP server: TLS optional (http_server.go:97)
- Default: Starts without TLS
- Risk: No encryption by default
- Missing: Enforced minimum TLS version (should be 1.2+)

### Risk Level: **HIGH**

### Recommendations

1. **Fix HTTP/3 Certificate Verification:**
   ```go
   // Production config
   TLSClientConfig: &tls.Config{
       InsecureSkipVerify: false,  // ALWAYS verify in production
       MinVersion:        tls.VersionTLS12,
   },
   ```

2. **Use Secure gRPC:**
   ```go
   conn, err := grpc.NewClient(target, 
       grpc.WithTransportCredentials(credentials.NewTLS(&tls.Config{
           MinVersion: tls.VersionTLS12,
       })))
   ```

3. **Enforce TLS on servers:**
   - Make TLS configuration required
   - Set minimum TLS version to 1.2
   - Disable weak ciphers

4. **Add certificate pinning:**
   - For critical connections
   - Pin server certificates to prevent MITM

---

## 4. ERROR HANDLING

### Files Examined
- All HTTP/gRPC server implementations
- `/Users/scttfrdmn/src/agenkit/agenkit/adapters/python/errors.py`
- `/Users/scttfrdmn/src/agenkit/agenkit-go/adapter/errors/errors.go`

### Current State: **MIXED**

### Findings

#### Information Disclosure Risks

1. **Error Message Exposure**
   - Go HTTP Server (http_server.go:222): `return errors.NewConnectionError(fmt.Sprintf("HTTP error %d: %s", resp.StatusCode, string(body)), nil)`
   - Returns full HTTP response body in errors
   - Risk: Exposes upstream server details

2. **Exception String Conversion**
   - Python HTTP (http_server.py:129): `str(e)` - converts all exceptions to strings
   - Go gRPC (grpc_server.go:95): `err.Error()` - returns error details
   - Risk: Internal implementation details in client responses

3. **Stack Traces Not Stripped**
   - Go: Error wrapping preserves internal context
   - Python: Uses logging but also returns error strings to clients
   - Risk: Information disclosure

#### Good Practices

1. **Error Envelopes**
   - Structured error responses (codec.CreateErrorEnvelope)
   - Separate error codes from messages
   - Example: grpc_server.go:273-286

2. **HTTP Status Mapping**
   - http_server.go:413-422 - Maps errors to appropriate HTTP codes
   - Good: INVALID_MESSAGE → 400, NOT_FOUND → 404

3. **WebSocket Error Handling**
   - Gracefully handles connection errors
   - websocket_transport.go:281-285

### Risk Level: **MEDIUM**

### Recommendations

1. **Sanitize Error Messages:**
   ```go
   // Production error handler
   func (h *HTTPAgent) sendError(w http.ResponseWriter, id, errorCode, msg string) {
       // Only send generic messages to clients
       clientMsg := "An error occurred"
       if errorCode == "INVALID_MESSAGE" {
           clientMsg = "Invalid message format"
       }
       // Log detailed error internally
       log.Printf("Error %s: %s", errorCode, msg)
       h.sendErrorResponse(w, id, errorCode, clientMsg)
   }
   ```

2. **Implement Error Logger:**
   - Log detailed errors server-side
   - Send generic messages to clients
   - Only expose necessary information

3. **Redact Sensitive Data:**
   - Never include API keys, tokens in errors
   - Never include file paths in errors
   - Never include SQL queries in errors

4. **Implement Error Tracking:**
   - Use error tracking service (Sentry, etc.)
   - Separate client-facing from internal errors

---

## 5. SECRETS MANAGEMENT

### Files Examined
- All files with "api_key", "token", "password" references
- LLM adapter implementations
- Configuration files

### Current State: **GOOD**

### Findings

#### No Hardcoded Credentials
1. **API Keys via Environment Variables**
   - Pattern: All files use `os.getenv("ANTHROPIC_API_KEY")`
   - Examples:
     - `examples/llm/anthropic_example.py:25`
     - `agenkit/adapters/llm/anthropic.py:81`
   - Good: No hardcoded keys in source

2. **LLM Adapters Accept Parameters**
   - Go: `AnthropicLLM` takes `apiKey` parameter
   - Python: `AnthropicLLM` takes `api_key` parameter
   - Default to environment variable if not provided
   - Good: Flexible, secure pattern

3. **No Credentials in Examples**
   - Examples use placeholder values: `api_key="..."`
   - Good: Clear examples don't leak secrets

#### Potential Issues

1. **No Encryption at Rest**
   - If credentials stored locally, not encrypted
   - Missing: Secure credential storage integration

2. **No Credential Rotation Support**
   - No built-in mechanism to rotate keys
   - Would need external coordination

3. **Limited Credential Isolation**
   - If LLM credentials leaked, attacker has full LLM access
   - Missing: Rate limiting on LLM calls

### Risk Level: **LOW** (for code itself, but depends on deployment)

### Recommendations

1. **Add Credential Validation:**
   ```python
   def __init__(self, api_key: str | None = None):
       if api_key is None:
           api_key = os.getenv("ANTHROPIC_API_KEY")
       if not api_key:
           raise ValueError(
               "ANTHROPIC_API_KEY not set. "
               "Set as environment variable or pass api_key parameter"
           )
       # Validate format
       if not api_key.startswith("sk-"):
           raise ValueError("Invalid API key format")
       self._api_key = api_key
   ```

2. **Implement Credential Wrapping:**
   - Add credential manager interface
   - Support HashiCorp Vault, AWS Secrets Manager

3. **Add Secrets Detection:**
   - Pre-commit hook to detect hardcoded keys
   - Use tools like: `detect-secrets`, `gitleaks`

4. **Document Credential Management:**
   - Add security guide for credential handling
   - Explain environment variable setup

---

## 6. INJECTION VULNERABILITIES

### Files Examined
- All tool execution code
- Subprocess/shell command patterns
- Database query patterns

### Current State: **GENERALLY SAFE with Examples**

### Findings

#### Code Execution

1. **eval() Usage - CRITICAL**
   - File: `examples/04_router_pattern.py:49`
   - Code: `result = eval(str(message.content))  # Don't use eval in production!`
   - Risk: CRITICAL - Remote code execution
   - Context: Example code with warning
   - Status: Has warning comment but dangerous

2. **eval() in Examples - CRITICAL**
   - File: `examples/adapters/02_agent_registry.py:32`
   - Code: `result = eval(message.content)`
   - Risk: CRITICAL - RCE
   - No warning comment

3. **eval() in Calculator - MEDIUM**
   - File: `examples/tools/calculator_example.py:244`
   - Code: `result = eval(expression, {"__builtins__": {}}, safe_funcs)`
   - Mitigation: Restricts builtins and uses safe function dict
   - Risk: MEDIUM - Better but still risky

#### Shell Commands

1. **asyncio.create_subprocess_exec** (Good Practice)
   - File: `examples/tools/os_tools_example.py:375, 838`
   - Uses exec form (not shell=True)
   - Good: Avoids shell injection
   - Note: Example only, demonstrates best practice

2. **No Direct Shell Injection in Main Code**
   - Production code doesn't use subprocess directly
   - Tools delegate to safety checks

#### Database Safety

1. **No SQL Injection in Core**
   - No direct SQL query construction in main code
   - Tools module shows awareness of injection risks
   - File: `examples/tools/database_example.py:871`
   - Comment: "Validate and sanitize all user inputs"

### Risk Level: **LOW-MEDIUM** (for production, HIGH for examples)

### Recommendations

1. **Remove eval() from Examples:**
   - Replace with: `ast.literal_eval()` for safe literals
   - Or: Safe expression parser (e.g., `simpleeval`)

2. **Mark Examples as Unsafe:**
   - Add prominent warnings
   - Create separate "secure_examples" directory
   - Example header: "⚠️ UNSAFE FOR PRODUCTION"

3. **Add Input Validation for Tool Parameters:**
   - Whitelist allowed commands
   - Validate all tool inputs against schema
   - Reject suspicious patterns

4. **Implement Safe Expression Evaluation:**
   ```python
   from simpleeval import simple_eval, safe_names
   result = simple_eval(expression, names=safe_names)
   ```

---

## 7. RATE LIMITING

### Files Examined
- `/Users/scttfrdmn/src/agenkit/agenkit-go/middleware/rate_limiter.go`
- `/Users/scttfrdmn/src/agenkit/agenkit/middleware/rate_limiter.py`
- Transport implementations

### Current State: **IMPLEMENTED but Optional**

### Findings

#### Rate Limiter Implementation - Go

1. **Token Bucket Algorithm** (rate_limiter.go:66-240)
   - Default: 10 tokens/sec, 10 capacity
   - Configurable burst capacity
   - Good: Allows burst traffic within limits

2. **Metrics Tracking**
   - Tracks: Total, allowed, rejected requests
   - Wait time metrics
   - Good: Observable behavior

3. **Configuration Options**
   - Rate (tokens/sec): Default 10.0
   - Capacity (max burst): Default 10
   - TokensPerRequest: Default 1
   - Good: Flexible configuration

#### Rate Limiter - Python

1. **Implementation**: `/Users/scttfrdmn/src/agenkit/agenkit/middleware/rate_limiter.py`
   - Token bucket similar to Go version
   - Configurable parameters
   - Metrics support

#### Critical Issues

1. **Not Enabled by Default**
   - Rate limiting is opt-in middleware
   - Must be explicitly applied to agent
   - Risk: Production deployments might skip it

2. **No Per-Agent Rate Limiting**
   - Global rate limit on agent
   - No per-user/per-API-key limiting
   - Risk: One user can consume all quota

3. **No Per-Method Rate Limiting**
   - Same limit for all operations
   - No distinction between read/write
   - Risk: Read operations could be rate-limited too aggressively

4. **Transport-Level Missing**
   - HTTP server doesn't have rate limiting
   - gRPC server doesn't have rate limiting
   - Rate limiter is agent-level only
   - Risk: Network DoS before reaching agent

### Risk Level: **MEDIUM**

### Recommendations

1. **Make Rate Limiting Default:**
   ```go
   // Instead of optional, make it default
   agent := NewAgent()
   agent = middleware.NewRateLimiterDecorator(
       agent,
       middleware.DefaultRateLimiterConfig(),
   )
   ```

2. **Add HTTP Middleware:**
   ```go
   // Add rate limiting to HTTP server
   type RateLimiterMiddleware struct {
       limiter *RateLimiter
       next    http.Handler
   }
   ```

3. **Implement Per-User Rate Limiting:**
   ```go
   type PerUserRateLimiter struct {
       limits map[string]*RateLimiter  // Per API key
   }
   ```

4. **Add Request Classification:**
   ```go
   type RateLimit struct {
       Reads:  100 / time.Minute   // Light operations
       Writes: 10 / time.Minute    // Heavy operations
   }
   ```

---

## 8. TIMEOUTS

### Files Examined
- `/Users/scttfrdmn/src/agenkit/agenkit-go/middleware/timeout.go`
- `/Users/scttfrdmn/src/agenkit/agenkit/middleware/timeout.py`
- Transport implementations

### Current State: **GOOD**

### Findings

#### Timeout Implementation - Go

1. **Timeout Decorator** (timeout.go:109-240)
   - Default: 30 seconds
   - Configurable via TimeoutConfig
   - Good: Reasonable default

2. **Goroutine Approach**
   - Runs agent in goroutine with timeout
   - Ensures timeout even for non-context-aware agents
   - Good: Robust implementation

3. **Metrics**
   - Tracks: Total, successful, timed-out, failed
   - Duration statistics (min, max, average)
   - Good: Observable

4. **Error Handling**
   - Returns `TimeoutError` on timeout
   - Can distinguish timeout from other errors
   - Good: Clear error types

#### Timeout Implementation - Python

1. **Implementation**: `/Users/scttfrdmn/src/agenkit/agenkit/middleware/timeout.py`
   - Default: 30 seconds
   - Uses asyncio timeout context manager
   - Metrics tracking
   - Similar to Go version

#### Gaps

1. **Not Enabled by Default**
   - Opt-in like rate limiting
   - Must be explicitly applied
   - Risk: Infinite-loop agents could hang

2. **No Per-Method Timeouts**
   - Single timeout for all operations
   - No distinction between operations
   - Some operations may need longer timeout

3. **Transport Timeouts**
   - Go HTTP client: No explicit timeout set
   - Go WebSocket: Has timeout constants but not enforced
   - Python httpx: Default 30s (good)

4. **Batching Timeout**
   - Batching middleware has timeout handling
   - But not always obvious

### Risk Level: **LOW**

### Recommendations

1. **Make Timeouts Default:**
   - Apply timeout to all agents by default
   - Allow explicit override for long-running operations

2. **Add Per-Method Timeout Configuration:**
   ```go
   type TimeoutConfig struct {
       Default    time.Duration
       Process    time.Duration  // Standard requests
       Stream     time.Duration  // Streaming requests
       LLMCall    time.Duration  // LLM operations (longer)
   }
   ```

3. **Enforce HTTP Client Timeouts:**
   ```go
   transport := &http.Transport{
       Timeout: 30 * time.Second,
   }
   ```

4. **Document Timeout Behavior:**
   - Guide for setting appropriate timeouts
   - Impact on different operation types
   - Examples of timeout configuration

---

## Summary Table

| Area | Status | Risk | Priority |
|------|--------|------|----------|
| **Input Validation** | Partial | MEDIUM | HIGH |
| **Authentication** | Missing | CRITICAL | CRITICAL |
| **Network Security** | Partial | HIGH | HIGH |
| **Error Handling** | Mixed | MEDIUM | MEDIUM |
| **Secrets Management** | Good | LOW | LOW |
| **Injection Vulnerabilities** | Good | LOW-MEDIUM | MEDIUM |
| **Rate Limiting** | Implemented | MEDIUM | MEDIUM |
| **Timeouts** | Implemented | LOW | LOW |

---

## Critical Issues (Must Fix Before Production)

1. **No Authentication/Authorization**
   - Servers accept all requests
   - No access control
   - High CORS permissiveness

2. **Insecure gRPC** 
   - Uses unencrypted, unauthenticated connections

3. **eval() in Examples**
   - Remote code execution risk
   - Even with warnings, dangerous to include

4. **TLS Certificate Verification**
   - HTTP/3 has InsecureSkipVerify in code
   - Could be deployed as-is

---

## High Priority Issues

1. **Input Validation Gaps**
   - No per-field size limits
   - No metadata validation
   - No rate limiting on invalid requests

2. **Error Information Disclosure**
   - Exception details returned to clients
   - Upstream server details exposed

3. **Optional Security Middleware**
   - Rate limiting not default
   - Timeouts not default
   - Could be skipped in deployment

---

## Medium Priority Issues

1. **No Per-User Rate Limiting**
2. **No Per-Method Timeout Configuration**
3. **Limited Monitoring/Logging**

---

## Recommended Implementation Order

### Phase 1 - Critical (Week 1)
1. Implement authentication/authorization
2. Fix gRPC certificate verification
3. Remove/replace eval() in examples

### Phase 2 - High Priority (Week 2)
1. Add input validation middleware
2. Sanitize error messages
3. Make rate limiting/timeout default

### Phase 3 - Medium Priority (Week 3)
1. Per-user rate limiting
2. Per-method timeout config
3. Comprehensive logging

---

## Testing Recommendations

```bash
# Test authentication bypass
curl -X POST http://localhost:8080/process -H "Content-Type: application/json"

# Test input validation
curl -X POST http://localhost:8080/process \
  -d '{"payload": {"message": {"content": "A"*1000000}}}'

# Test rate limiting
for i in {1..100}; do curl http://localhost:8080/health; done

# Test timeout
curl -X POST http://localhost:8080/process \
  --max-time 2 -d '{"long_running": true}'

# Test TLS
curl --insecure https://localhost:8080/health  # Should warn about cert
```

---

## Security Checklist for Deployment

- [ ] Authentication enabled on all endpoints
- [ ] Authorization checks implemented
- [ ] TLS certificate verification enabled
- [ ] Error messages sanitized
- [ ] Input validation enabled
- [ ] Rate limiting enabled by default
- [ ] Timeouts enabled by default
- [ ] No debug/verbose logging in production
- [ ] Security headers added (CORS, CSP, etc.)
- [ ] HTTPS enforced
- [ ] gRPC uses mTLS
- [ ] Secrets stored securely (not in code)
- [ ] Audit logging enabled
- [ ] Regular security updates applied

