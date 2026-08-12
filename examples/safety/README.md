# Agent Safety Framework Examples

This directory contains practical examples demonstrating the Agent Safety Framework capabilities.

## Examples

### 1. Input Validation (`01_input_validation.py`)
Demonstrates how to protect agents from prompt injection attacks and validate input content.

**Features:**
- Prompt injection detection with pattern matching
- Custom detection thresholds (strict vs lenient)
- Content filtering (size limits, banned words, PII detection)
- Strict vs non-strict modes (blocking vs logging)

**Run:**
```bash
python examples/safety/01_input_validation.py
```

### 2. Output Validation (`02_output_validation.py`)
Shows how to validate agent outputs and automatically redact sensitive information.

**Features:**
- Schema validation with type checking
- Automatic sensitive data redaction (API keys, passwords, emails, etc.)
- Custom field validation
- Output size limits
- Manual redaction control

**Run:**
```bash
python examples/safety/02_output_validation.py
```

### 3. Permissions & Sandboxing (`03_permissions.py`)
Demonstrates role-based access control (RBAC) and sandboxing capabilities.

**Features:**
- Predefined roles (ADMIN, USER, READONLY, RESTRICTED)
- Custom permission sets
- File path sandboxing
- Command whitelisting/blacklisting
- SQL operation restrictions
- Network domain filtering

**Run:**
```bash
python examples/safety/03_permissions.py
```

### 4. Complete Safety Stack (`04_complete_safety_stack.py`)
Shows how to combine all safety components into a comprehensive security solution.

**Features:**
- Multi-layer security architecture
- Input validation → Permissions → Output validation → Anomaly detection
- Security audit logging
- Real-world attack scenario demonstrations
- Custom anomaly handlers

**Run:**
```bash
python examples/safety/04_complete_safety_stack.py
```

## Quick Start

Install Agenkit with safety dependencies:

```bash
pip install agenkit
```

Run any example:

```bash
python examples/safety/01_input_validation.py
```

## Safety Stack Architecture

The recommended security stack (applied in order):

```python
from agenkit.safety import (
    InputValidationMiddleware,
    PermissionMiddleware,
    OutputValidationMiddleware,
    AnomalyDetectionMiddleware,
)

# Layer 1: Input validation (first line of defense)
agent = InputValidationMiddleware(base_agent, strict=True)

# Layer 2: Permissions & sandboxing
agent = PermissionMiddleware(agent, role=Role.USER, sandbox=sandbox)

# Layer 3: Output validation & redaction
agent = OutputValidationMiddleware(agent, schema=schema, auto_redact=True)

# Layer 4: Anomaly detection (monitoring)
agent = AnomalyDetectionMiddleware(agent, detector=detector, user_id="user_id")
```

## Common Use Cases

### Protecting Customer-Facing Agents
Use input validation to prevent prompt injection and output validation to prevent data leaks:

```python
agent = InputValidationMiddleware(base_agent, strict=True)
agent = OutputValidationMiddleware(agent, auto_redact=True)
```

### Internal Tool Agents
Use permissions to control what resources agents can access:

```python
sandbox = Sandbox(allowed_paths={"/app/data"}, allowed_commands={"ls", "cat", "grep"})
agent = PermissionMiddleware(base_agent, role=Role.USER, sandbox=sandbox)
```

### Production Deployments
Use the full safety stack with audit logging:

```python
from agenkit.safety.audit import SecurityAuditLogger

audit_logger = SecurityAuditLogger(log_file="security_audit.log")

# Apply all safety layers
agent = build_secure_agent(base_agent, audit_logger)
```

## Testing Safety Features

Each example includes multiple test scenarios. Run them to see:

- ✓ Normal requests that pass security checks
- ✗ Malicious requests that are blocked
- ⚠ Anomalous behavior that triggers alerts
- 🔒 Sensitive data that gets redacted

## Best Practices

1. **Always use input validation** for user-facing agents
2. **Enable auto-redaction** for agents that handle sensitive data
3. **Use appropriate roles** - start with READONLY and escalate only when needed
4. **Monitor anomalies** - set up alerts for suspicious behavior
5. **Enable audit logging** in production
6. **Test your security** - try to break your own agents
7. **Layer your defenses** - don't rely on a single safety mechanism

## Troubleshooting

### False Positives in Prompt Injection Detection
Adjust the detection threshold:

```python
detector = PromptInjectionDetector(threshold=20)  # More lenient
agent = InputValidationMiddleware(base_agent, detector=detector)
```

### Sensitive Data Not Being Redacted
Add custom patterns:

```python
redactor = SensitiveDataRedactor()
redactor.sensitive_fields.add("custom_sensitive_field")
agent = OutputValidationMiddleware(base_agent, redactor=redactor)
```

### Permission Denied Errors
Check the role permissions:

```python
middleware = PermissionMiddleware(agent, role=Role.USER)
print(middleware.has_permission(Permission.READ_FILES))
```

## Further Reading

- [Agent Safety Framework Documentation](../../docs/safety/)
- [Security Best Practices](../../docs/SECURITY.md)
- [API Reference](../../docs/api/safety.md)

## Contributing

Found a security issue? Please report it responsibly via [GitHub Security Advisories](https://github.com/scttfrdmn/agenkit/security/advisories).

Want to add more examples? Submit a pull request!
