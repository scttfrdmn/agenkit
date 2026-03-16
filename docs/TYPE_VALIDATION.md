# Type Validation Across Languages

This document describes how agenkit validates types in each language implementation
and explains why idiomatic differences between languages produce equivalent behavior.

## Overview

Type validation in agenkit is concentrated in the safety layer (`output_validation.*`)
and is used to verify that agent outputs conform to expected schemas before being
returned to callers. Each language uses its native type introspection facilities.

## Per-Language Patterns

### String validation

| Language | Pattern | Source |
|---|---|---|
| Python | `isinstance(value, str)` | `agenkit/safety/output_validation.py:59` |
| Go | `_, ok := value.(string)` type assertion | `agenkit-go/safety/output_validation.go` |
| TypeScript | `typeof value === 'string'` | `agenkit-ts/src/safety/output-validation.ts` |
| Rust | `value.is_string()` (serde_json) | `agenkit-rust/src/safety/output_validation.rs` |
| C++ | `std::holds_alternative<std::string>(value)` | `agenkit-cpp/src/safety/output_validation.cpp` |
| Zig | `value == .string` (tagged union) | `agenkit-zig/src/safety/output_validation.zig` |

### Integer / float validation

| Language | Pattern |
|---|---|
| Python | `isinstance(value, (int, float))` |
| Go | `_, ok := value.(float64)` (JSON numbers decode as float64) |
| TypeScript | `typeof value === 'number'` |
| Rust | `value.is_number()` |
| C++ | `std::holds_alternative<double>(value)` |
| Zig | `value == .integer or value == .float` |

### Boolean validation

| Language | Pattern |
|---|---|
| Python | `isinstance(value, bool)` |
| Go | `_, ok := value.(bool)` |
| TypeScript | `typeof value === 'boolean'` |
| Rust | `value.is_boolean()` |
| C++ | `std::holds_alternative<bool>(value)` |
| Zig | `value == .bool` |

### Object / map validation

| Language | Pattern | Source |
|---|---|---|
| Python | `isinstance(value, dict)` | `agenkit/safety/output_validation.py` |
| Go | `_, ok := value.(map[string]interface{})` | `agenkit-go/safety/output_validation.go:94` |
| TypeScript | `typeof output !== 'object' \|\| Array.isArray(output)` | `agenkit-ts/src/safety/output-validation.ts:70` |
| Rust | `value.is_object()` | |
| C++ | `std::holds_alternative<std::map<...>>(value)` | |
| Zig | `value == .object` | |

### Array / list validation

| Language | Pattern |
|---|---|
| Python | `isinstance(value, list)` |
| Go | `_, ok := value.([]interface{})` |
| TypeScript | `Array.isArray(value)` |
| Rust | `value.is_array()` |
| C++ | `std::holds_alternative<std::vector<...>>(value)` |
| Zig | `value == .array` |

### Null / nil / None validation

| Language | Pattern |
|---|---|
| Python | `value is None` |
| Go | `value == nil` |
| TypeScript | `value === null \|\| value === undefined` |
| Rust | `value.is_null()` |
| C++ | `std::holds_alternative<std::nullptr_t>(value)` |
| Zig | `value == .null` |

## Why Differences Are OK

These patterns look different because each language has a different type system:

1. **Python** uses runtime duck typing — `isinstance` checks the object's class hierarchy.
   Importantly, `bool` is a subclass of `int` in Python, so boolean values pass an
   `isinstance(value, int)` check. Validation code must check `bool` before `int` when
   distinguishing them.

2. **Go** has static types but uses `interface{}` (or `any`) to represent JSON-decoded
   values. JSON numbers always decode as `float64` regardless of whether they look like
   integers — this is a Go JSON stdlib behavior, not an agenkit quirk.

3. **TypeScript** uses `typeof` for primitives and `instanceof` / `Array.isArray` for
   compound types. `typeof null === 'object'` is a well-known JS quirk; TypeScript code
   checks `value !== null` explicitly to distinguish null from objects.

4. **Rust** uses the `serde_json::Value` enum, which provides `.is_string()`, `.is_number()`,
   etc. as convenience methods. These are direct enum variant checks.

5. **C++** uses `std::variant` with `std::holds_alternative<T>()` — the closest equivalent
   to Rust's enum pattern in modern C++.

6. **Zig** uses tagged unions — the `.tag` field comparison is idiomatic and exhaustively
   checked by the compiler.

**All six patterns produce semantically equivalent results** for the types agenkit works
with (string, number, boolean, object, array, null). The behavioral differences (Go's
float64-for-all-numbers, Python's bool-is-int inheritance) are either handled explicitly
or do not affect agenkit's validation use cases.

## Schema Validation

Beyond individual type checks, agenkit validates structured agent output against schemas
using the same idiomatic approach:

| Language | Schema library |
|---|---|
| Python | `pydantic` (v2) |
| Go | Manual struct validation + `encoding/json` |
| TypeScript | `zod` |
| Rust | `serde` + `serde_json` |
| C++ | Custom validators |
| Zig | Compile-time struct reflection |

## Related Documentation

- [DEFAULTS.md](DEFAULTS.md) — canonical default configuration values
- [ARCHITECTURE.md](../ARCHITECTURE.md) — design principles
- [Safety modules](../agenkit/safety/) — Python reference implementation
