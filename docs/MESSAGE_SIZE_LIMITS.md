# Message Size Limits

**Status**: Standardization in progress (Issue #423)
**Version**: v0.51.0+
**Last Updated**: February 3, 2026

---

## Overview

This document defines recommended message size limits for Agenkit implementations across all languages. Proper size validation protects against:

- **Memory exhaustion** - Large messages can consume excessive memory
- **Performance degradation** - Oversized payloads slow down serialization/transport
- **Network timeouts** - Large messages may exceed network timeout limits
- **Storage issues** - Persistent memory systems have size constraints

---

## Current State (v0.50.0)

| Language | Content Limit | Metadata Value Limit | Metadata Keys | Validation |
|----------|--------------|---------------------|---------------|------------|
| **Python** | 16MB | 16MB | 100 keys | ✅ Validated in `__post_init__` |
| **Go** | 1MB | 10KB | 100 keys | ✅ Validated in `Validate()` |
| **TypeScript** | None | None | None | ❌ No validation |
| **Rust** | None | None | None | ❌ No validation |
| **C++** | None | None | None | ❌ No validation |
| **Zig** | None | None | None | ❌ No validation |

### Issues with Current State

1. **Inconsistency**: Python allows 16x larger messages than Go (16MB vs 1MB)
2. **Gap**: 4 languages have no size validation at all
3. **Risk**: Unvalidated languages vulnerable to memory/performance issues
4. **Migration pain**: Configs don't port between languages

---

## Recommended Limits (v0.52.0+)

### Standard Configuration

```yaml
# Recommended defaults for all languages
message:
  max_content_size: 16777216      # 16MB (16 * 1024 * 1024)
  max_metadata_keys: 100          # Prevent metadata abuse
  max_metadata_key_length: 50     # Characters
  max_metadata_value_size: 16777216  # 16MB (match content limit)

# For resource-constrained environments
message_compact:
  max_content_size: 1048576       # 1MB (1024 * 1024)
  max_metadata_keys: 50
  max_metadata_key_length: 50
  max_metadata_value_size: 10240  # 10KB
```

### Rationale

**Why 16MB for content?**
- Supports large LLM context windows (GPT-4: ~128K tokens ≈ 512KB text, but structured data can be larger)
- Allows for embedded base64 images or documents
- Matches Python's current production-tested limit
- Common HTTP server default limits (e.g., nginx: 1-100MB)

**Why 16MB for metadata values?**
- Consistency with content limit
- Supports embedding trace context, logs, or debugging info
- Prevents artificial distinction between "content" and "metadata"

**Why 100 metadata keys?**
- Reasonable upper bound for structured metadata
- Prevents abuse while allowing rich context
- Current limit in Python and Go

**Why 50-character key length?**
- Long enough for descriptive names (e.g., "opentelemetry_trace_parent")
- Short enough to prevent abuse
- Current limit in Python and Go

### When to Use Compact Limits

Use compact limits (1MB/10KB) for:
- **Embedded systems** with limited memory
- **Edge computing** scenarios
- **High-throughput services** processing many small messages
- **Mobile applications** with bandwidth constraints

---

## Implementation Guidelines

### Python (Already Implemented ✅)

**File**: `agenkit/interfaces.py` (lines 71-109)

```python
@dataclass(frozen=True)
class Message:
    role: str
    content: Any
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Validate message after initialization."""
        # Content validation - max 16MB
        if self.content is not None:
            content_str = str(self.content)
            content_size = len(content_str.encode("utf-8"))
            max_content_size = 16 * 1024 * 1024  # 16MB
            if content_size > max_content_size:
                raise ValueError(
                    f"Message content exceeds maximum size of {max_content_size} bytes "
                    f"(got {content_size} bytes)"
                )

        # Metadata validation
        if self.metadata:
            # Max 100 keys
            if len(self.metadata) > 100:
                raise ValueError(
                    f"Message metadata exceeds maximum of 100 keys (got {len(self.metadata)})"
                )

            # Validate each key and value
            max_key_length = 50
            max_value_size = 16 * 1024 * 1024  # 16MB

            for key, value in self.metadata.items():
                if len(key) > max_key_length:
                    raise ValueError(
                        f"Metadata key '{key[:20]}...' exceeds maximum length of {max_key_length} "
                        f"characters (got {len(key)})"
                    )

                value_str = str(value)
                value_size = len(value_str.encode("utf-8"))
                if value_size > max_value_size:
                    raise ValueError(
                        f"Metadata value for key '{key}' exceeds maximum size of {max_value_size} bytes "
                        f"(got {value_size} bytes)"
                    )
```

**Status**: ✅ Complete - Already uses recommended 16MB limits

---

### Go (Needs Update ⚠️)

**File**: `agenkit-go/agenkit/interfaces.go` (lines 69-102)

**Current Implementation** (1MB/10KB):
```go
// Validate validates the message according to security constraints.
func (m *Message) Validate() error {
    // Content validation - max 1MB
    contentSize := len(m.Content)
    maxContentSize := 1024 * 1024 // 1MB
    if contentSize > maxContentSize {
        return fmt.Errorf("message content exceeds maximum size of %d bytes (got %d bytes)", maxContentSize, contentSize)
    }

    // Metadata validation
    if m.Metadata != nil {
        // Max 100 keys
        if len(m.Metadata) > 100 {
            return fmt.Errorf("message metadata exceeds maximum of 100 keys (got %d)", len(m.Metadata))
        }

        // Validate each key and value
        maxKeyLength := 50
        maxValueSize := 10 * 1024 // 10KB

        for key, value := range m.Metadata {
            if len(key) > maxKeyLength {
                return fmt.Errorf("metadata key '%s...' exceeds maximum length of %d characters (got %d)",
                    key[:min(20, len(key))], maxKeyLength, len(key))
            }

            valueStr := fmt.Sprintf("%v", value)
            valueSize := len(valueStr)
            if valueSize > maxValueSize {
                return fmt.Errorf("metadata value for key '%s' exceeds maximum size of %d bytes (got %d bytes)",
                    key, maxValueSize, valueSize)
            }
        }
    }

    return nil
}
```

**Recommended Update** (16MB/16MB):
```go
func (m *Message) Validate() error {
    // Content validation - max 16MB (align with other languages)
    contentSize := len(m.Content)
    maxContentSize := 16 * 1024 * 1024 // 16MB
    if contentSize > maxContentSize {
        return fmt.Errorf("message content exceeds maximum size of %d bytes (got %d bytes)", maxContentSize, contentSize)
    }

    // Metadata validation
    if m.Metadata != nil {
        // Max 100 keys
        if len(m.Metadata) > 100 {
            return fmt.Errorf("message metadata exceeds maximum of 100 keys (got %d)", len(m.Metadata))
        }

        // Validate each key and value
        maxKeyLength := 50
        maxValueSize := 16 * 1024 * 1024 // 16MB (align with content limit)

        for key, value := range m.Metadata {
            if len(key) > maxKeyLength {
                return fmt.Errorf("metadata key '%s...' exceeds maximum length of %d characters (got %d)",
                    key[:min(20, len(key))], maxKeyLength, len(key))
            }

            valueStr := fmt.Sprintf("%v", value)
            valueSize := len(valueStr)
            if valueSize > maxValueSize {
                return fmt.Errorf("metadata value for key '%s' exceeds maximum size of %d bytes (got %d bytes)",
                    key, maxValueSize, valueSize)
            }
        }
    }

    return nil
}
```

**Migration**: Non-breaking change (expands limits)

---

### TypeScript (Needs Implementation 🔧)

**File**: `agenkit-ts/src/core/interfaces.ts`

**Recommended Addition**:

```typescript
/**
 * Validate message size and structure.
 *
 * @param message Message to validate
 * @throws {Error} if message exceeds size limits
 */
export function validateMessage(message: Message): void {
  // Role validation
  if (!message.role || message.role.length === 0) {
    throw new Error('Message role cannot be empty');
  }
  if (message.role.length > 20) {
    throw new Error(`Message role exceeds maximum length of 20 characters (got ${message.role.length})`);
  }

  // Validate role is one of the allowed values
  const allowedRoles = new Set(['user', 'assistant', 'system', 'tool', 'agent']);
  if (!allowedRoles.has(message.role)) {
    throw new Error(`Invalid message role: ${message.role}. Must be one of: ${Array.from(allowedRoles).join(', ')}`);
  }

  // Content validation - max 16MB
  if (message.content !== undefined && message.content !== null) {
    const contentStr = typeof message.content === 'string'
      ? message.content
      : JSON.stringify(message.content);
    const contentSize = new TextEncoder().encode(contentStr).length;
    const maxContentSize = 16 * 1024 * 1024; // 16MB

    if (contentSize > maxContentSize) {
      throw new Error(
        `Message content exceeds maximum size of ${maxContentSize} bytes (got ${contentSize} bytes)`
      );
    }
  }

  // Metadata validation
  if (message.metadata) {
    const metadataKeys = Object.keys(message.metadata);

    // Max 100 keys
    if (metadataKeys.length > 100) {
      throw new Error(
        `Message metadata exceeds maximum of 100 keys (got ${metadataKeys.length})`
      );
    }

    // Validate each key and value
    const maxKeyLength = 50;
    const maxValueSize = 16 * 1024 * 1024; // 16MB

    for (const [key, value] of Object.entries(message.metadata)) {
      // Key length validation
      if (key.length > maxKeyLength) {
        throw new Error(
          `Metadata key '${key.substring(0, 20)}...' exceeds maximum length of ${maxKeyLength} characters (got ${key.length})`
        );
      }

      // Value size validation
      const valueStr = typeof value === 'string' ? value : JSON.stringify(value);
      const valueSize = new TextEncoder().encode(valueStr).length;

      if (valueSize > maxValueSize) {
        throw new Error(
          `Metadata value for key '${key}' exceeds maximum size of ${maxValueSize} bytes (got ${valueSize} bytes)`
        );
      }
    }
  }
}

/**
 * Helper to create a validated message.
 *
 * @param role Message role
 * @param content Message content
 * @param metadata Optional metadata
 * @returns Validated message
 * @throws {Error} if message is invalid
 */
export function createValidatedMessage(
  role: string,
  content: unknown,
  metadata?: Record<string, unknown>
): Message {
  const message: Message = {
    role,
    content,
    metadata,
    timestamp: new Date().toISOString(),
  };

  validateMessage(message);
  return message;
}
```

**Usage**:
```typescript
import { validateMessage, createValidatedMessage } from './core/interfaces';

// Option 1: Validate existing message
const msg: Message = { role: 'user', content: 'Hello' };
validateMessage(msg); // Throws if invalid

// Option 2: Create validated message
const msg2 = createValidatedMessage('user', 'Hello', { sessionId: '123' });
```

---

### Rust (Needs Implementation 🔧)

**File**: `agenkit-rust/src/core/message.rs`

**Current Implementation** (lines 120-130):
```rust
/// Validate the message according to security constraints.
///
/// Checks:
/// - Role is non-empty
/// - Content is not null
///
/// # Errors
/// Returns MessageError if validation fails.
pub fn validate(&self) -> Result<(), MessageError> {
    if self.role.is_empty() {
        return Err(MessageError::EmptyRole);
    }

    if self.content.is_null() {
        return Err(MessageError::NullContent);
    }

    Ok(())
}
```

**Recommended Update**:

```rust
/// Error types for message operations.
#[derive(Error, Debug)]
pub enum MessageError {
    #[error("message role must be a non-empty string")]
    EmptyRole,

    #[error("message role exceeds maximum length of 20 characters (got {0})")]
    RoleTooLong(usize),

    #[error("invalid message role: {0}. Must be one of: user, assistant, system, tool, agent")]
    InvalidRole(String),

    #[error("message content cannot be null")]
    NullContent,

    #[error("message content exceeds maximum size of {max} bytes (got {actual} bytes)")]
    ContentTooLarge { max: usize, actual: usize },

    #[error("message metadata exceeds maximum of {max} keys (got {actual})")]
    TooManyMetadataKeys { max: usize, actual: usize },

    #[error("metadata key '{key}' exceeds maximum length of {max} characters (got {actual})")]
    MetadataKeyTooLong { key: String, max: usize, actual: usize },

    #[error("metadata value for key '{key}' exceeds maximum size of {max} bytes (got {actual} bytes)")]
    MetadataValueTooLarge { key: String, max: usize, actual: usize },

    #[error("invalid message format: {0}")]
    InvalidFormat(String),

    #[error("serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
}

impl Message {
    /// Validate the message according to security constraints.
    ///
    /// Checks:
    /// - Role is non-empty and <= 20 characters
    /// - Role is one of: user, assistant, system, tool, agent
    /// - Content is not null
    /// - Content size <= 16MB
    /// - Metadata has <= 100 keys
    /// - Each metadata key <= 50 characters
    /// - Each metadata value <= 16MB
    ///
    /// # Errors
    /// Returns MessageError if validation fails.
    pub fn validate(&self) -> Result<(), MessageError> {
        // Role validation
        if self.role.is_empty() {
            return Err(MessageError::EmptyRole);
        }

        if self.role.len() > 20 {
            return Err(MessageError::RoleTooLong(self.role.len()));
        }

        // Validate role is one of the allowed values
        let allowed_roles = ["user", "assistant", "system", "tool", "agent"];
        if !allowed_roles.contains(&self.role.as_str()) {
            return Err(MessageError::InvalidRole(self.role.clone()));
        }

        // Content validation
        if self.content.is_null() {
            return Err(MessageError::NullContent);
        }

        // Content size validation - max 16MB
        let content_str = self.content.to_string();
        let content_size = content_str.as_bytes().len();
        let max_content_size = 16 * 1024 * 1024; // 16MB

        if content_size > max_content_size {
            return Err(MessageError::ContentTooLarge {
                max: max_content_size,
                actual: content_size,
            });
        }

        // Metadata validation
        if !self.metadata.is_empty() {
            // Max 100 keys
            if self.metadata.len() > 100 {
                return Err(MessageError::TooManyMetadataKeys {
                    max: 100,
                    actual: self.metadata.len(),
                });
            }

            // Validate each key and value
            let max_key_length = 50;
            let max_value_size = 16 * 1024 * 1024; // 16MB

            for (key, value) in &self.metadata {
                // Key length validation
                if key.len() > max_key_length {
                    return Err(MessageError::MetadataKeyTooLong {
                        key: key.clone(),
                        max: max_key_length,
                        actual: key.len(),
                    });
                }

                // Value size validation
                let value_str = value.to_string();
                let value_size = value_str.as_bytes().len();

                if value_size > max_value_size {
                    return Err(MessageError::MetadataValueTooLarge {
                        key: key.clone(),
                        max: max_value_size,
                        actual: value_size,
                    });
                }
            }
        }

        Ok(())
    }
}
```

**Usage**:
```rust
use agenkit::core::Message;
use serde_json::json;

// Create and validate message
let msg = Message::new("user", json!("Hello, agent!"));
msg.validate()?; // Returns Result<(), MessageError>

// Or create with automatic validation
let msg = Message::new("user", json!("Hello"))
    .with_metadata("session_id", json!("abc123"));
msg.validate()?;
```

---

### C++ (Needs Implementation 🔧)

**File**: `agenkit-cpp/include/agenkit/core/message.hpp`

**Recommended Addition**:

```cpp
namespace agenkit {
namespace core {

/**
 * @brief Exception thrown when message validation fails
 */
class MessageValidationError : public std::runtime_error {
public:
    explicit MessageValidationError(const std::string& message)
        : std::runtime_error(message) {}
};

class Message {
public:
    // ... existing methods ...

    /**
     * @brief Validate message according to security constraints
     *
     * Checks:
     * - Role is non-empty and <= 20 characters
     * - Role is one of: user, assistant, system, tool, agent
     * - Content size <= 16MB
     * - Metadata has <= 100 keys
     * - Each metadata key <= 50 characters
     * - Each metadata value <= 16MB
     *
     * @throws MessageValidationError if validation fails
     */
    void validate() const {
        // Role validation
        if (role_.empty()) {
            throw MessageValidationError("Message role cannot be empty");
        }

        if (role_.length() > 20) {
            throw MessageValidationError(
                "Message role exceeds maximum length of 20 characters (got " +
                std::to_string(role_.length()) + ")"
            );
        }

        // Validate role is one of the allowed values
        static const std::set<std::string> allowed_roles = {
            "user", "assistant", "system", "tool", "agent"
        };
        if (allowed_roles.find(role_) == allowed_roles.end()) {
            throw MessageValidationError(
                "Invalid message role: " + role_ +
                ". Must be one of: user, assistant, system, tool, agent"
            );
        }

        // Content size validation - max 16MB
        std::string content_str = content_.dump();
        size_t content_size = content_str.size();
        constexpr size_t max_content_size = 16 * 1024 * 1024; // 16MB

        if (content_size > max_content_size) {
            throw MessageValidationError(
                "Message content exceeds maximum size of " +
                std::to_string(max_content_size) + " bytes (got " +
                std::to_string(content_size) + " bytes)"
            );
        }

        // Metadata validation
        if (!metadata_.is_null() && metadata_.is_object()) {
            // Max 100 keys
            if (metadata_.size() > 100) {
                throw MessageValidationError(
                    "Message metadata exceeds maximum of 100 keys (got " +
                    std::to_string(metadata_.size()) + ")"
                );
            }

            // Validate each key and value
            constexpr size_t max_key_length = 50;
            constexpr size_t max_value_size = 16 * 1024 * 1024; // 16MB

            for (auto& [key, value] : metadata_.items()) {
                // Key length validation
                if (key.length() > max_key_length) {
                    std::string short_key = key.substr(0, 20) + "...";
                    throw MessageValidationError(
                        "Metadata key '" + short_key +
                        "' exceeds maximum length of " +
                        std::to_string(max_key_length) +
                        " characters (got " +
                        std::to_string(key.length()) + ")"
                    );
                }

                // Value size validation
                std::string value_str = value.dump();
                size_t value_size = value_str.size();

                if (value_size > max_value_size) {
                    throw MessageValidationError(
                        "Metadata value for key '" + key +
                        "' exceeds maximum size of " +
                        std::to_string(max_value_size) +
                        " bytes (got " + std::to_string(value_size) + " bytes)"
                    );
                }
            }
        }
    }

private:
    std::string role_;
    nlohmann::json content_;
    nlohmann::json metadata_;
    std::chrono::system_clock::time_point timestamp_;
};

} // namespace core
} // namespace agenkit
```

**Usage**:
```cpp
#include <agenkit/core/message.hpp>

using namespace agenkit::core;

// Create and validate message
auto msg = Message::with_text("user", "Hello, agent!");
msg.validate(); // Throws MessageValidationError if invalid

// Add metadata and validate
msg.with_metadata("session_id", "abc123");
msg.validate();
```

---

### Zig (Needs Implementation 🔧)

**File**: `agenkit-zig/src/message.zig`

**Recommended Addition**:

```zig
/// Message validation errors
pub const ValidationError = error{
    EmptyRole,
    RoleTooLong,
    InvalidRole,
    ContentTooLarge,
    TooManyMetadataKeys,
    MetadataKeyTooLong,
    MetadataValueTooLarge,
};

pub const Message = struct {
    role: Role,
    content: Content,
    metadata: json.Value,
    allocator: Allocator,

    // ... existing methods ...

    /// Validate message according to security constraints
    ///
    /// Checks:
    /// - Role is valid enum value
    /// - Content size <= 16MB
    /// - Metadata has <= 100 keys
    /// - Each metadata key <= 50 characters
    /// - Each metadata value <= 16MB
    ///
    /// Returns ValidationError if validation fails
    pub fn validate(self: *const Message) !void {
        // Role validation (already enforced by enum type)

        // Content size validation - max 16MB
        const content_size = switch (self.content) {
            .text => |t| t.len,
            .structured => |v| {
                // Approximate size by converting to string
                const json_str = try std.json.stringifyAlloc(
                    self.allocator,
                    v,
                    .{}
                );
                defer self.allocator.free(json_str);
                return json_str.len;
            },
        };

        const max_content_size = 16 * 1024 * 1024; // 16MB
        if (content_size > max_content_size) {
            std.log.err(
                "Message content exceeds maximum size of {d} bytes (got {d} bytes)",
                .{ max_content_size, content_size }
            );
            return ValidationError.ContentTooLarge;
        }

        // Metadata validation
        if (self.metadata == .object) {
            const metadata_obj = self.metadata.object;

            // Max 100 keys
            if (metadata_obj.count() > 100) {
                std.log.err(
                    "Message metadata exceeds maximum of 100 keys (got {d})",
                    .{metadata_obj.count()}
                );
                return ValidationError.TooManyMetadataKeys;
            }

            // Validate each key and value
            const max_key_length = 50;
            const max_value_size = 16 * 1024 * 1024; // 16MB

            var it = metadata_obj.iterator();
            while (it.next()) |entry| {
                // Key length validation
                if (entry.key_ptr.*.len > max_key_length) {
                    std.log.err(
                        "Metadata key exceeds maximum length of {d} characters (got {d})",
                        .{ max_key_length, entry.key_ptr.*.len }
                    );
                    return ValidationError.MetadataKeyTooLong;
                }

                // Value size validation
                const value_str = try std.json.stringifyAlloc(
                    self.allocator,
                    entry.value_ptr.*,
                    .{}
                );
                defer self.allocator.free(value_str);

                if (value_str.len > max_value_size) {
                    std.log.err(
                        "Metadata value for key '{s}' exceeds maximum size of {d} bytes (got {d} bytes)",
                        .{ entry.key_ptr.*, max_value_size, value_str.len }
                    );
                    return ValidationError.MetadataValueTooLarge;
                }
            }
        }
    }
};
```

**Usage**:
```zig
const std = @import("std");
const Message = @import("message.zig").Message;
const Role = @import("message.zig").Role;

// Create and validate message
var msg = try Message.withText(allocator, .user, "Hello, agent!");
defer msg.deinit();

try msg.validate(); // Returns ValidationError if invalid
```

---

## Testing Strategy

### Unit Tests

Each language should include tests for:

1. **Valid messages** at each limit boundary:
   - Exactly 16MB content (passes)
   - Exactly 16MB + 1 byte content (fails)
   - Exactly 100 metadata keys (passes)
   - 101 metadata keys (fails)
   - Exactly 50-character key (passes)
   - 51-character key (fails)
   - Exactly 16MB metadata value (passes)
   - 16MB + 1 byte metadata value (fails)

2. **Edge cases**:
   - Empty content (allowed in some contexts)
   - Null content (behavior depends on language)
   - Unicode content (multi-byte characters)
   - Nested metadata structures

3. **Error messages**:
   - Clear indication of which limit was exceeded
   - Actual vs maximum values reported
   - Helpful context (key name for metadata errors)

### Integration Tests

Cross-language tests should verify:

1. **Serialization compatibility**: Messages at size limits serialize/deserialize correctly between languages
2. **Transport compatibility**: Large messages transport correctly via HTTP/gRPC/WebSocket
3. **Performance**: Validation overhead is < 1% for typical message sizes

---

## Migration Path

### Phase 1: Documentation (v0.51.0) ✅

- ✅ Create this document
- ✅ Document current state
- ✅ Define recommended limits

### Phase 2: Implementation (v0.52.0)

**Non-breaking changes**:
1. Go: Increase limits from 1MB/10KB to 16MB/16MB (expands, doesn't restrict)
2. TypeScript, Rust, C++, Zig: Add validation (new feature, doesn't break existing code)

**Implementation order**:
1. Add validation functions (without enforcing)
2. Add tests
3. Enable validation with clear error messages
4. Document in language-specific READMEs

### Phase 3: Testing & Validation (v0.52.0)

1. Add cross-language size limit tests
2. Verify serialization/transport at limits
3. Benchmark validation performance
4. Update examples with validation patterns

### Phase 4: Future (v0.53.0+)

Optional features:
- **Configurable limits**: Allow users to set custom limits
- **Compact mode**: Easy way to enable 1MB/10KB limits
- **Streaming validation**: Validate during streaming for early failure detection
- **Compressed transport**: Automatic compression for large messages

---

## Configuration Examples

### Python

```python
from agenkit.interfaces import Message

# Validation happens automatically in __post_init__
try:
    msg = Message(
        role="user",
        content="Large content...",  # Will validate size
        metadata={"key": "value"}
    )
except ValueError as e:
    print(f"Validation failed: {e}")
```

### Go

```go
import "github.com/scttfrdmn/agenkit-go/agenkit"

// Explicit validation required
msg := agenkit.NewMessage("user", "Large content...")
if err := msg.Validate(); err != nil {
    return fmt.Errorf("validation failed: %w", err)
}
```

### TypeScript

```typescript
import { createValidatedMessage } from 'agenkit';

try {
  const msg = createValidatedMessage('user', 'Large content...', {
    key: 'value'
  });
} catch (error) {
  console.error('Validation failed:', error.message);
}
```

### Rust

```rust
use agenkit::core::Message;
use serde_json::json;

let msg = Message::new("user", json!("Large content..."));
msg.validate()?; // Returns Result<(), MessageError>
```

### C++

```cpp
#include <agenkit/core/message.hpp>

try {
    auto msg = Message::with_text("user", "Large content...");
    msg.validate(); // Throws MessageValidationError if invalid
} catch (const MessageValidationError& e) {
    std::cerr << "Validation failed: " << e.what() << std::endl;
}
```

### Zig

```zig
const msg = try Message.withText(allocator, .user, "Large content...");
defer msg.deinit();

try msg.validate(); // Returns ValidationError if invalid
```

---

## Performance Considerations

### Validation Overhead

Estimated overhead for validation:

| Message Size | Validation Time | Overhead |
|--------------|----------------|----------|
| 1KB | ~5μs | <0.1% |
| 100KB | ~50μs | <0.1% |
| 1MB | ~500μs | ~0.5% |
| 16MB | ~8ms | ~5% |

For most use cases (messages < 1MB), validation overhead is negligible.

### Optimization Strategies

1. **Lazy validation**: Only validate when needed (e.g., before serialization/transport)
2. **Cached results**: Cache validation results by content/metadata snapshot, not by object identity - `Message` is only shallow-frozen (field reassignment is blocked, but `metadata` is a mutable `dict` that patterns may modify in place), so a cache keyed on "this message object hasn't changed" can go stale
3. **Streaming validation**: Validate during construction for early failure
4. **Skip trusted sources**: Allow bypassing validation for trusted internal messages

---

## Security Considerations

### Why Size Limits Matter

1. **DoS Prevention**: Unlimited message sizes enable denial-of-service attacks
2. **Memory Safety**: Prevents OOM conditions in production
3. **Performance**: Large messages slow down serialization, networking, and processing
4. **Storage**: Persistent memory systems have finite capacity

### Best Practices

1. **Validate early**: Check message sizes before expensive operations
2. **Clear errors**: Provide actionable error messages when limits exceeded
3. **Configurable limits**: Allow operators to tune limits for their environment
4. **Monitor sizes**: Track message size distribution in production
5. **Gradual degradation**: Large messages should fail gracefully, not crash

---

## References

- Issue #423: Standardize message size limits across languages
- Issue #412: Cross-Language API Alignment
- Python implementation: `agenkit/interfaces.py` (lines 71-109)
- Go implementation: `agenkit-go/agenkit/interfaces.go` (lines 69-102)

---

**Status**: Awaiting implementation in TypeScript, Rust, C++, Zig (tracked in #423)
