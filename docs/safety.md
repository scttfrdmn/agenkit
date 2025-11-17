# Agent Safety Framework

**Status:** ✅ Implementation Complete | ⏳ Testing In Progress

The Agent Safety Framework provides comprehensive security and operational guardrails for AI agents, protecting against malicious inputs, unauthorized actions, and anomalous behavior.

## Overview

The safety framework consists of five integrated modules:

1. **Input Validation** - Prompt injection defense and content filtering
2. **Output Validation** - Schema validation and PII redaction
3. **Permissions** - Role-based access control and sandboxing  
4. **Anomaly Detection** - Behavioral monitoring and alerting
5. **Audit Logging** - Security event tracking

## Quick Start

```python
from agenkit import Agent, Message
from agenkit.safety import (
    InputValidationMiddleware,
    OutputValidationMiddleware,
    PermissionMiddleware,
)

# Create a secure agent with multiple safety layers
agent = MyAgent()
agent = InputValidationMiddleware(agent, strict=True)
agent = OutputValidationMiddleware(agent)
agent = PermissionMiddleware(agent, allowed_actions=["read", "write"])

# Process safely
message = Message(role="user", content="What is the weather?")
result = await agent.process(message)
```

## Modules

### 1. Input Validation

Protects against prompt injection and malicious inputs.

**Features:**
- Prompt injection detection (15+ patterns)
- Suspicious keyword scoring
- Content filtering (banned words, PII)
- Size limits

**Usage:**
```python
from agenkit.safety import InputValidationMiddleware, PromptInjectionDetector

detector = PromptInjectionDetector(threshold=8)  # Lower = stricter
agent = InputValidationMiddleware(base_agent, detector=detector, strict=True)
```

**Detects:**
- "Ignore previous instructions"  
- System prompt overrides
- Jailbreak attempts
- Special token injection
- PII (SSN, credit cards, emails)

### 2. Output Validation

Ensures agent outputs meet safety and schema requirements.

**Features:**
- Schema validation (Pydantic models)
- PII redaction
- Content filtering
- Format validation

**Usage:**
```python
from agenkit.safety import OutputValidationMiddleware, SchemaValidator
from pydantic import BaseModel

class SafeResponse(BaseModel):
    message: str
    confidence: float

validator = SchemaValidator(schema=SafeResponse)
agent = OutputValidationMiddleware(base_agent, schema_validator=validator)
```

### 3. Permissions

Role-based access control for agent actions.

**Features:**
- Role-based permissions
- Action allowlists/denylists
- Sandboxing
- Resource limits

**Usage:**
```python
from agenkit.safety import PermissionMiddleware, Role, Permission

role = Role("analyst", permissions=[
    Permission("read", resource="database"),
    Permission("query", resource="api"),
])

agent = PermissionMiddleware(base_agent, role=role)
```

### 4. Anomaly Detection

Monitors for unusual agent behavior.

**Features:**
- Statistical anomaly detection
- Failure rate monitoring
- Resource usage tracking
- Security event alerts

**Usage:**
```python
from agenkit.safety import AnomalyDetectionMiddleware

agent = AnomalyDetectionMiddleware(
    base_agent,
    failure_threshold=0.2,  # Alert if >20% failures
    window_size=100,  # Monitor last 100 requests
)
```

### 5. Audit Logging

Comprehensive security event logging.

**Features:**
- Structured JSON logs
- Security event categorization
- Trace correlation
- Compliance support

**Usage:**
```python
from agenkit.safety import SecurityAuditLogger

logger = SecurityAuditLogger(log_file="security.log")
logger.log_security_event(
    event_type="prompt_injection",
    severity="high",
    details={"pattern": "ignore instructions", "score": 15}
)
```

## Complete Safety Stack

Combine all modules for maximum protection:

```python
from agenkit.safety import (
    InputValidationMiddleware,
    OutputValidationMiddleware,
    PermissionMiddleware,
    AnomalyDetectionMiddleware,
)

# Layer safety middleware
agent = MyAgent()
agent = InputValidationMiddleware(agent, strict=True)
agent = PermissionMiddleware(agent, role=analyst_role)
agent = AnomalyDetectionMiddleware(agent)
agent = OutputValidationMiddleware(agent)
```

## Configuration

### Strict vs Non-Strict Mode

**Strict Mode** (default):
- Blocks on validation failure
- Raises `ValidationError`
- Recommended for production

**Non-Strict Mode**:
- Logs warnings only
- Continues processing
- Useful for testing/debugging

```python
agent = InputValidationMiddleware(base_agent, strict=False)
```

### Threshold Tuning

Adjust sensitivity based on your use case:

```python
# More permissive (fewer false positives)
detector = PromptInjectionDetector(threshold=15)

# Stricter (more false positives, but safer)
detector = PromptInjectionDetector(threshold=5)
```

## Examples

See comprehensive examples in `examples/safety/`:

1. `01_input_validation.py` - Prompt injection defense
2. `02_output_validation.py` - Schema and PII validation
3. `03_permissions.py` - RBAC and sandboxing
4. `04_complete_safety_stack.py` - All modules together

## Testing

Run safety tests:

```bash
pytest tests/safety/
```

**Current Coverage:**
- `test_input_validation.py`: 39 tests ✅ (100%)
- Other modules: Coming soon

## Language Support

- **Python**: ✅ Complete (5 modules, 4 examples)
- **Go**: ✅ Complete (5 modules, examples in progress)

## Best Practices

1. **Layer Multiple Protections**: Use input validation + permissions + anomaly detection
2. **Tune Thresholds**: Adjust based on false positive rates
3. **Monitor Logs**: Review security audit logs regularly
4. **Test Thoroughly**: Test with known attack patterns
5. **Stay Updated**: Prompt injection techniques evolve rapidly

## Known Limitations

- Pattern-based detection (not ML-based)
- False positives possible with strict thresholds
- Performance impact (< 1ms per check)
- Limited to common attack patterns

## Future Enhancements

- ML-based injection detection
- Advanced PII detection (named entity recognition)
- Real-time threat intelligence integration
- Automated threshold tuning

## References

- [OWASP Top 10 for LLMs](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- [Prompt Injection Attacks](https://simonwillison.net/2023/Apr/14/worst-that-can-happen/)
- [AgentKit Security Policy](../SECURITY.md)

## Contributing

Help improve the safety framework:
- Add new attack patterns
- Improve detection accuracy
- Submit test cases
- Report false positives/negatives

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.
