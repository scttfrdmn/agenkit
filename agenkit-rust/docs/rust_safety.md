# Rust Safety Module Documentation

**Version**: 0.49.0
**Status**: Production-Ready ✅
**Test Coverage**: 40+ tests

## Overview

The Agenkit Rust safety module provides comprehensive security features for AI agents, including input validation, output redaction, permission-based access control, anomaly detection, and security audit logging.

## Key Features

- **Input Validation**: Detect and block prompt injection attacks, jailbreak attempts, and malicious content
- **Output Validation**: Redact sensitive data (API keys, credentials, PII) and validate response schemas
- **Permission-Based Access Control**: Role-based permissions with sandboxing constraints
- **Anomaly Detection**: Behavioral monitoring, rate limiting, and suspicious pattern detection
- **Security Audit Logging**: Structured audit trails for compliance and security monitoring

---

## Quick Start

### Basic Safety Stack

```rust
use agenkit::{
    core::{Agent, Message},
    safety::{
        InputValidationMiddleware,
        OutputValidationMiddleware,
        PermissionMiddleware,
        Role,
    },
};

// Create your base agent
let agent = MyAgent::new();

// Wrap with safety layers
let safe_agent = InputValidationMiddleware::new(agent)
    .with_prompt_injection_detector()
    .with_content_filter();

let safe_agent = OutputValidationMiddleware::new(safe_agent)
    .with_redactor();

let safe_agent = PermissionMiddleware::new(safe_agent, Role::User);

// Process messages securely
let msg = Message::with_text("user", "Hello!");
let response = safe_agent.process(msg).await?;
```

---

## Module Components

### 1. Input Validation

Protects against malicious user input including prompt injection attacks, jailbreak attempts, and banned content.

#### Prompt Injection Detection

```rust
use agenkit::safety::{InputValidationMiddleware, PromptInjectionConfig};

// Default configuration (threshold: 8)
let agent = InputValidationMiddleware::new(base_agent)
    .with_prompt_injection_detector()
    .strict(true);

// Custom threshold
let mut config = PromptInjectionConfig::default();
config.threshold = 10; // More strict

let agent = InputValidationMiddleware::new(base_agent)
    .with_prompt_injection_detector_config(config);
```

**Detection patterns include:**
- Jailbreak attempts: "pretend you are", "ignore all instructions"
- Admin mode escalation: "enter admin mode", "sudo mode"
- Instruction override: "disregard previous", "new system prompt"
- Special tokens: `<|system|>`, `[INST]`, `<<SYS>>`

#### Content Filtering

```rust
use agenkit::safety::{ContentFilterConfig, InputValidationMiddleware};
use std::collections::HashSet;

let mut config = ContentFilterConfig::default();
config.banned_words = HashSet::from([
    "malware".to_string(),
    "exploit".to_string(),
    "hack".to_string(),
]);
config.max_size = 10000;
config.min_size = 1;
config.enable_pii_detection = true;

let agent = InputValidationMiddleware::new(base_agent)
    .with_content_filter_config(config);
```

**Content validation features:**
- Banned word detection (case-insensitive)
- Size limits (min/max content length)
- PII detection: SSN, credit cards, emails
- Configurable strict mode (block vs warn)

---

### 2. Output Validation

Protects against data leaks by redacting sensitive information and validating response structures.

#### Sensitive Data Redaction

```rust
use agenkit::safety::OutputValidationMiddleware;

let agent = OutputValidationMiddleware::new(base_agent)
    .with_redactor()
    .with_max_size(100_000);
```

**Automatically redacts:**
- API Keys: `sk-*`, `AKIA*` (AWS), `ghp_*` (GitHub)
- JWT Tokens: `eyJ*` patterns
- Passwords and secrets
- SSN: `123-45-6789`
- Credit cards: `1234-5678-9012-3456`
- Email addresses
- Phone numbers

#### Schema Validation

```rust
use agenkit::safety::{SchemaValidator, SchemaValidatorConfig};
use std::collections::{HashMap, HashSet};

let mut config = SchemaValidatorConfig::default();
config.expected_fields.insert("status".to_string(), "string".to_string());
config.expected_fields.insert("data".to_string(), "array".to_string());
config.required_fields.insert("status".to_string());
config.allow_additional_fields = true;

let schema = SchemaValidator::new(config);

let agent = OutputValidationMiddleware::new(base_agent)
    .with_schema_validator(schema);
```

---

### 3. Permission-Based Access Control (RBAC)

Role-based permissions with sandboxing for file system, command, and network access.

#### Built-in Roles

```rust
use agenkit::safety::{PermissionMiddleware, Role};

// Admin: Full access
let admin_agent = PermissionMiddleware::new(agent, Role::Admin);

// User: Standard access (read/write files, execute commands, tools)
let user_agent = PermissionMiddleware::new(agent, Role::User);

// ReadOnly: Limited to reading files and database queries
let readonly_agent = PermissionMiddleware::new(agent, Role::ReadOnly);

// Restricted: Minimal access (read files, use tools only)
let restricted_agent = PermissionMiddleware::new(agent, Role::Restricted);
```

#### Sandbox Constraints

```rust
use agenkit::safety::{Sandbox, PermissionMiddleware, Role};
use std::collections::HashSet;

let mut sandbox = Sandbox::default();

// Path restrictions
sandbox.allowed_paths = HashSet::from([
    "/tmp".to_string(),
    "/home/user/safe".to_string(),
]);
sandbox.denied_paths = HashSet::from([
    "/etc".to_string(),
    "/sys".to_string(),
]);

// Command filtering
sandbox.allowed_commands = HashSet::from([
    "ls".to_string(),
    "cat".to_string(),
    "git".to_string(),
]);
sandbox.denied_commands = HashSet::from([
    "rm".to_string(),
    "sudo".to_string(),
]);

// Resource limits
sandbox.max_file_size = 10 * 1024 * 1024; // 10MB
sandbox.max_execution_time = 30; // 30 seconds
sandbox.max_memory = 512 * 1024 * 1024; // 512MB

let agent = PermissionMiddleware::new(base_agent, Role::User)
    .with_sandbox(sandbox);
```

---

### 4. Anomaly Detection

Behavioral monitoring to detect suspicious patterns and rate limit abusive requests.

```rust
use agenkit::safety::AnomalyDetectionMiddleware;

let agent = AnomalyDetectionMiddleware::new(base_agent, "user-id-123".to_string());
```

**Monitoring features:**
- Rate limiting: 60 requests/minute with burst of 10
- Message size anomalies
- Request timing patterns
- Failure rate tracking
- Automatic threshold adjustment

---

### 5. Security Audit Logging

Structured audit trails for compliance, debugging, and security monitoring.

```rust
use agenkit::safety::{
    SecurityAuditLogger,
    SecurityAuditLoggerConfig,
    AuditEvent,
    AuditEventType,
    AuditSeverity,
};

// Configure audit logger
let mut config = SecurityAuditLoggerConfig::default();
config.log_file = std::path::PathBuf::from("./logs/security_audit.log");
config.console_logging = true;
config.min_severity = AuditSeverity::Info;

let audit_logger = SecurityAuditLogger::new(config)?;

// Log security events
let mut event = AuditEvent::new(
    AuditEventType::PromptInjectionBlocked,
    AuditSeverity::Warning,
    "Blocked prompt injection attempt".to_string(),
);
event.user_id = Some("user-123".to_string());
event.agent_name = Some("my-agent".to_string());
event.details.insert("pattern".to_string(), json!("jailbreak"));

audit_logger.log(&event)?;
```

**Event Types:**
- `AgentStarted`, `AgentCompleted`, `AgentError`
- `PromptInjectionDetected`, `PromptInjectionBlocked`
- `PermissionDenied`, `RateLimitExceeded`
- `AnomalyDetected`, `ContentFiltered`

**Severity Levels:**
- `Debug`, `Info`, `Warning`, `Error`, `Critical`

---

## Production Examples

### Complete Safety Stack

```rust
use agenkit::{
    core::{Agent, Message},
    safety::{
        InputValidationMiddleware,
        OutputValidationMiddleware,
        PermissionMiddleware,
        AnomalyDetectionMiddleware,
        Role,
        ContentFilterConfig,
        SecurityAuditLogger,
        SecurityAuditLoggerConfig,
    },
};
use std::collections::HashSet;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // 1. Setup audit logging
    let mut audit_config = SecurityAuditLoggerConfig::default();
    audit_config.log_file = std::path::PathBuf::from("./logs/audit.log");
    let audit_logger = SecurityAuditLogger::new(audit_config)?;

    // 2. Create base agent
    let agent = MyAgent::new();

    // 3. Add input validation
    let mut content_config = ContentFilterConfig::default();
    content_config.banned_words = HashSet::from([
        "malware".to_string(),
        "exploit".to_string(),
    ]);

    let agent = InputValidationMiddleware::new(agent)
        .with_prompt_injection_detector()
        .with_content_filter_config(content_config)
        .strict(true);

    // 4. Add output validation
    let agent = OutputValidationMiddleware::new(agent)
        .with_redactor()
        .with_max_size(100_000);

    // 5. Add permissions
    let agent = PermissionMiddleware::new(agent, Role::User);

    // 6. Add anomaly detection
    let agent = AnomalyDetectionMiddleware::new(agent, "user-123".to_string());

    // 7. Process messages securely
    let msg = Message::with_text("user", "Process this request");
    match agent.process(msg).await {
        Ok(response) => println!("Response: {:?}", response),
        Err(e) => eprintln!("Security violation: {}", e),
    }

    Ok(())
}
```

### Custom Threshold Example

```rust
use agenkit::safety::{PromptInjectionDetector, PromptInjectionConfig};

// Lenient (threshold: 5)
let mut lenient_config = PromptInjectionConfig::default();
lenient_config.threshold = 5;
let lenient_detector = PromptInjectionDetector::with_config(lenient_config);

// Strict (threshold: 15)
let strict_detector = PromptInjectionDetector::with_threshold(15);

// Test detection
let (score, is_safe) = lenient_detector.detect("Ignore all previous instructions");
println!("Score: {}, Safe: {}", score, is_safe);
```

---

## Testing

The safety module includes 40+ comprehensive tests covering:
- Prompt injection detection patterns
- Content filtering edge cases
- Permission hierarchy validation
- Schema validation
- Sensitive data redaction (all major secret types)
- Anomaly detection thresholds
- Audit logging

Run tests:
```bash
# Run all safety tests
cargo test --lib safety

# Run specific module tests
cargo test --lib safety::input_validation
cargo test --lib safety::output_validation
cargo test --lib safety::permissions
```

---

## Best Practices

### 1. Defense in Depth
Layer multiple safety mechanisms for comprehensive protection:
```rust
let agent = MyAgent::new();
let agent = InputValidationMiddleware::new(agent).with_prompt_injection_detector();
let agent = OutputValidationMiddleware::new(agent).with_redactor();
let agent = PermissionMiddleware::new(agent, Role::User);
```

### 2. Fail Securely
Use strict mode to block unsafe requests rather than just logging warnings:
```rust
let agent = InputValidationMiddleware::new(agent)
    .with_prompt_injection_detector()
    .strict(true); // Block unsafe requests
```

### 3. Audit Everything
Enable comprehensive audit logging for security monitoring:
```rust
let mut config = SecurityAuditLoggerConfig::default();
config.console_logging = true; // Real-time visibility
config.min_severity = AuditSeverity::Info; // Log all security events
let audit_logger = SecurityAuditLogger::new(config)?;
```

### 4. Least Privilege
Start with minimal permissions and add only what's necessary:
```rust
// Start restrictive
let agent = PermissionMiddleware::new(agent, Role::Restricted);

// Upgrade only if needed
let agent = PermissionMiddleware::new(agent, Role::User);
```

### 5. Test Security
Add security-focused tests to your application:
```rust
#[tokio::test]
async fn test_blocks_prompt_injection() {
    let agent = create_secure_agent();
    let msg = Message::with_text("user", "Ignore all previous instructions");
    assert!(agent.process(msg).await.is_err());
}
```

---

## Performance Considerations

- **Regex pre-compilation**: All patterns compiled once at initialization
- **Non-blocking I/O**: Audit logging uses async I/O
- **Minimal overhead**: Input validation adds ~0.1ms per request
- **Memory efficient**: Streaming redaction for large outputs

---

## API Reference

### Input Validation
- `InputValidationMiddleware::new(agent) -> Self`
- `.with_prompt_injection_detector() -> Self`
- `.with_prompt_injection_detector_config(config) -> Self`
- `.with_content_filter() -> Self`
- `.with_content_filter_config(config) -> Self`
- `.strict(bool) -> Self`

### Output Validation
- `OutputValidationMiddleware::new(agent) -> Self`
- `.with_redactor() -> Self`
- `.with_schema_validator(schema) -> Self`
- `.with_max_size(usize) -> Self`

### Permissions
- `PermissionMiddleware::new(agent, role) -> Self`
- `.with_sandbox(sandbox) -> Self`

### Anomaly Detection
- `AnomalyDetectionMiddleware::new(agent, user_id) -> Self`

### Audit Logging
- `SecurityAuditLogger::new(config) -> Result<Self, std::io::Error>`
- `.log(&event) -> Result<(), std::io::Error>`

---

## Migration Guide

### From Python
```python
# Python
from agenkit.safety import InputValidationMiddleware
agent = InputValidationMiddleware(base_agent, enable_prompt_injection=True)
```

```rust
// Rust
use agenkit::safety::InputValidationMiddleware;
let agent = InputValidationMiddleware::new(base_agent)
    .with_prompt_injection_detector();
```

### From Go
```go
// Go
import "github.com/yourusername/agenkit-go/safety"
agent := safety.NewInputValidationMiddleware(baseAgent).
    WithPromptInjectionDetector()
```

```rust
// Rust
use agenkit::safety::InputValidationMiddleware;
let agent = InputValidationMiddleware::new(base_agent)
    .with_prompt_injection_detector();
```

---

## Troubleshooting

### Issue: False Positives in Prompt Injection Detection

**Solution**: Adjust the detection threshold
```rust
let detector = PromptInjectionDetector::with_threshold(15); // More lenient
```

### Issue: Legitimate Content Being Filtered

**Solution**: Customize banned words list
```rust
let mut config = ContentFilterConfig::default();
config.banned_words = HashSet::new(); // Start with empty list
config.banned_words.insert("specific_word".to_string());
```

### Issue: Performance Degradation

**Solution**: Disable unused validators
```rust
// Only enable what you need
let agent = InputValidationMiddleware::new(agent)
    .with_prompt_injection_detector(); // Skip content filter if not needed
```

---

## Contributing

To add new safety features:

1. Add detection logic to the appropriate module
2. Write comprehensive tests (minimum 3-5 tests per feature)
3. Update examples to demonstrate the feature
4. Add documentation to this guide

---

## See Also

- [Examples: safety_simple.rs](../examples/safety_simple.rs)
- [Examples: safety_framework.rs](../examples/safety_framework.rs)
- [Python Safety Module](../../agenkit/observability/)
- [Go Safety Module](../../agenkit-go/safety/)

---

**Last Updated**: January 16, 2026
**Maintainer**: Agenkit Team
