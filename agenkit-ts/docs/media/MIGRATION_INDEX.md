# Agenkit Migration Guide Index

**Complete reference for migrating Agenkit code between all 6 supported languages**

---

## Quick Navigation

### By Source Language

- [**From Python**](#migrating-from-python) → Go, TypeScript, Rust, C++, Zig
- [**From Go**](#migrating-from-go) → Python, TypeScript, Rust, C++, Zig
- [**From TypeScript**](#migrating-from-typescript) → Python, Go, Rust, C++, Zig
- [**From Rust**](#migrating-from-rust) → Python, Go, TypeScript, C++, Zig
- [**From C++**](#migrating-from-c) → Python, Go, TypeScript, Rust, Zig
- [**From Zig**](#migrating-from-zig) → Python, Go, TypeScript, Rust, C++

### By Use Case

- [**Prototyping → Production**](#prototyping-to-production) (Python → Go/Rust/C++)
- [**Web Deployment**](#web-deployment) (Any → TypeScript)
- [**Performance Optimization**](#performance-optimization) (Python/TypeScript → Go/Rust/C++)
- [**Memory Safety**](#memory-safety) (C++/Python → Rust)
- [**Embedded Systems**](#embedded-systems) (Any → Zig/Rust)
- [**Cross-Platform**](#cross-platform) (Any → TypeScript)

---

## Documentation Architecture

Agenkit's migration documentation uses a **DRY (Don't Repeat Yourself) hybrid approach**:

### 📚 Language Profiles (~600 lines each)

**Deep-dive reference documents** covering language idioms, type systems, error handling, concurrency, memory management, and Agenkit-specific patterns.

**When to use:** Learning a new language, understanding design decisions, deep technical reference.

### 🚀 Quick Reference Guides (~350-500 lines each)

**Concise migration guides** with side-by-side code examples, common gotchas, performance comparisons, and migration checklists.

**When to use:** Actively migrating code, quick syntax lookups, practical migration scenarios.

**Benefits:**
- ✅ **No duplication:** Idioms explained once in Language Profiles
- ✅ **Quick access:** Fast migration guides for common scenarios
- ✅ **Scalable:** O(n) documentation growth, not O(n²)
- ✅ **Maintainable:** Update profile → all references benefit

---

## Language Profiles

**Start here to understand a language deeply:**

| Language | Profile | Key Characteristics |
|----------|---------|-------------------|
| **Python** | [LANGUAGE_PROFILE_PYTHON.md](LANGUAGE_PROFILE_PYTHON.md) | Dynamic typing, GC, asyncio, duck typing, GIL |
| **Go** | [LANGUAGE_PROFILE_GO.md](LANGUAGE_PROFILE_GO.md) | Static typing, GC, goroutines, explicit errors, interfaces |
| **TypeScript** | [LANGUAGE_PROFILE_TYPESCRIPT.md](LANGUAGE_PROFILE_TYPESCRIPT.md) | Structural typing, GC, Promises, single-threaded |
| **Rust** | [LANGUAGE_PROFILE_RUST.md](LANGUAGE_PROFILE_RUST.md) | Ownership, Result types, tokio, zero-cost abstractions |
| **C++** | [LANGUAGE_PROFILE_CPP.md](LANGUAGE_PROFILE_CPP.md) | RAII, smart pointers, templates, OS threads |
| **Zig** | [LANGUAGE_PROFILE_ZIG.md](LANGUAGE_PROFILE_ZIG.md) | Explicit allocators, defer, comptime, no GC |

Each profile includes:
- Language philosophy and design principles
- Type system features and idioms
- Error handling patterns
- Concurrency models
- Memory management approaches
- Agenkit-specific patterns
- Testing approaches
- Performance characteristics

---

## Migrating from Python

### Quick References

| Target | Guide | Performance | Primary Use Case |
|--------|-------|-------------|-----------------|
| **Go** | [MIGRATE_PYTHON_TO_GO.md](MIGRATE_PYTHON_TO_GO.md) | 5-20x faster | Backend services, deployment simplicity |
| **TypeScript** | [MIGRATE_PYTHON_TO_TYPESCRIPT.md](MIGRATE_PYTHON_TO_TYPESCRIPT.md) | ~2x faster | Web/Node.js, universal deployment |
| **Rust** | [MIGRATE_PYTHON_TO_RUST.md](MIGRATE_PYTHON_TO_RUST.md) | 20-100x faster | Performance-critical, WASM, systems |
| **C++** | [MIGRATION.md](MIGRATION.md#python--c) | 20-100x faster | Native performance, legacy integration |
| **Zig** | [MIGRATION.md](MIGRATION.md#python--zig) | 20-100x faster | Embedded, low-level control |

### Key Migration Challenges

**Python → Go:**
- Dynamic → static typing
- Exceptions → explicit error returns
- asyncio → goroutines
- GIL → true parallelism

**Python → TypeScript:**
- Runtime → compile-time type checking
- asyncio → Promises (similar async/await!)
- None → undefined/null

**Python → Rust:**
- GC → ownership system (biggest paradigm shift!)
- Exceptions → Result<T,E>
- Dynamic → static types

---

## Migrating from Go

### Quick References

| Target | Guide | Key Differences | Primary Use Case |
|--------|-------|----------------|-----------------|
| **Python** | [MIGRATE_GO_TO_PYTHON.md](MIGRATE_GO_TO_PYTHON.md) | Static → dynamic, explicit → exceptions | Prototyping, ML integration |
| **TypeScript** | [MIGRATE_GO_TO_TYPESCRIPT.md](MIGRATE_GO_TO_TYPESCRIPT.md) | Multi-threaded → single-threaded | Web frontend, universal code |
| **Rust** | [MIGRATE_GO_TO_RUST.md](MIGRATE_GO_TO_RUST.md) | GC → ownership, similar concurrency | Memory safety, WASM |
| **C++** | [MIGRATE_GO_TO_CPP.md](MIGRATE_GO_TO_CPP.md) | GC → manual memory, simpler → complex | Performance tuning, legacy systems |
| **Zig** | [MIGRATE_GO_TO_ZIG.md](MIGRATE_GO_TO_ZIG.md) | GC → explicit allocators | Embedded, minimal runtime |

### Key Migration Challenges

**Go → Python:**
- Explicit errors → exceptions
- Static → dynamic typing
- Goroutines → asyncio

**Go → TypeScript:**
- Multi-threaded → single-threaded event loop
- Explicit errors → exceptions
- Structural typing preserved

**Go → Rust:**
- GC → ownership (borrow checker!)
- Similar concurrency models (goroutines vs tokio)

---

## Migrating from TypeScript

### Quick References

| Target | Guide | Key Differences | Primary Use Case |
|--------|-------|----------------|-----------------|
| **Python** | [MIGRATE_TYPESCRIPT_TO_PYTHON.md](MIGRATE_TYPESCRIPT_TO_PYTHON.md) | Similar async, compile-time → runtime | Data science, ML, scripting |
| **Go** | [MIGRATE_TYPESCRIPT_TO_GO.md](MIGRATE_TYPESCRIPT_TO_GO.md) | Single-threaded → multi-threaded | Backend services, true parallelism |
| **Rust** | [MIGRATE_TYPESCRIPT_TO_RUST.md](MIGRATE_TYPESCRIPT_TO_RUST.md) | GC → ownership, 10-20x faster | Systems programming, WASM |
| **C++** | [MIGRATE_TYPESCRIPT_TO_CPP.md](MIGRATE_TYPESCRIPT_TO_CPP.md) | GC → manual memory | Native performance, legacy |
| **Zig** | [MIGRATE_TYPESCRIPT_TO_ZIG.md](MIGRATE_TYPESCRIPT_TO_ZIG.md) | GC → explicit allocators | Embedded, minimal dependencies |

### Key Migration Challenges

**TypeScript → Python:**
- Compile-time → runtime types
- Similar async/await patterns
- undefined/null → None

**TypeScript → Go:**
- Single-threaded → goroutines (major concurrency upgrade!)
- Structural typing preserved
- Promises → channels

**TypeScript → Rust:**
- GC → ownership (biggest challenge!)
- Event loop → tokio runtime

---

## Migrating from Rust

### Quick References

| Target | Guide | Key Differences | Primary Use Case |
|--------|-------|----------------|-----------------|
| **Python** | [MIGRATE_RUST_TO_PYTHON.md](MIGRATE_RUST_TO_PYTHON.md) | Ownership → GC, explicit → exceptions | Prototyping, ML integration |
| **Go** | [MIGRATE_RUST_TO_GO.md](MIGRATE_RUST_TO_GO.md) | Ownership → GC, similar errors | Simpler deployment, faster iteration |
| **TypeScript** | [MIGRATE_RUST_TO_TYPESCRIPT.md](MIGRATE_RUST_TO_TYPESCRIPT.md) | Multi-threaded → single-threaded | Web deployment, universal code |
| **C++** | [MIGRATE_RUST_TO_CPP.md](MIGRATE_RUST_TO_CPP.md) | Ownership → RAII, similar performance | Legacy integration, C ABI |
| **Zig** | [MIGRATE_RUST_TO_ZIG.md](MIGRATE_RUST_TO_ZIG.md) | Ownership → explicit allocators | Embedded, simpler async model |

### Key Migration Challenges

**Rust → Python:**
- Ownership → GC (major simplification!)
- Result<T,E> → exceptions
- 20-100x performance cost

**Rust → Go:**
- Ownership → GC
- Similar explicit error handling
- Comparable performance

**Rust → TypeScript:**
- Multi-threaded → single-threaded
- Ownership → GC

---

## Migrating from C++

### Quick References

| Target | Guide | Key Differences | Primary Use Case |
|--------|-------|----------------|-----------------|
| **Python** | [MIGRATE_CPP_TO_PYTHON.md](MIGRATE_CPP_TO_PYTHON.md) | Manual memory → GC, 20-100x slower | Easier maintenance, prototyping |
| **Go** | [MIGRATE_CPP_TO_GO.md](MIGRATE_CPP_TO_GO.md) | RAII → GC, exceptions → explicit | Simpler memory, better concurrency |
| **TypeScript** | [MIGRATE_CPP_TO_TYPESCRIPT.md](MIGRATE_CPP_TO_TYPESCRIPT.md) | Manual → GC, multi → single-threaded | Web deployment, cross-platform |
| **Rust** | [MIGRATE_CPP_TO_RUST.md](MIGRATE_CPP_TO_RUST.md) | Manual → ownership, similar performance | Memory safety, modern async |
| **Zig** | [MIGRATE_CPP_TO_ZIG.md](MIGRATE_CPP_TO_ZIG.md) | RAII → defer, similar performance | Simpler language, explicit control |

### Key Migration Challenges

**C++ → Python:**
- Manual memory → GC (major simplification!)
- Templates → duck typing
- OS threads → asyncio

**C++ → Go:**
- Exceptions → explicit errors (paradigm shift!)
- RAII → defer
- Similar concurrency

**C++ → Rust:**
- Manual RAII → ownership (compile-time safety!)
- Comparable performance

---

## Migrating from Zig

### Quick References

| Target | Guide | Key Differences | Primary Use Case |
|--------|-------|----------------|-----------------|
| **Python** | [MIGRATE_ZIG_TO_PYTHON.md](MIGRATE_ZIG_TO_PYTHON.md) | Explicit allocators → GC, comptime → runtime | High-level APIs, ML integration |
| **Go** | [MIGRATE_ZIG_TO_GO.md](MIGRATE_ZIG_TO_GO.md) | Explicit allocators → GC, OS threads → goroutines | Better concurrency, simpler deployment |
| **TypeScript** | [MIGRATE_ZIG_TO_TYPESCRIPT.md](MIGRATE_ZIG_TO_TYPESCRIPT.md) | Explicit allocators → GC, blocking → async | Web deployment, universal code |
| **Rust** | [MIGRATE_ZIG_TO_RUST.md](MIGRATE_ZIG_TO_RUST.md) | Manual tracking → ownership, blocking → async | Async ecosystem, memory safety |
| **C++** | [MIGRATE_ZIG_TO_CPP.md](MIGRATE_ZIG_TO_CPP.md) | defer → RAII, similar performance | Larger ecosystem, legacy integration |

### Key Migration Challenges

**Zig → Python:**
- Explicit allocators → GC (major simplification!)
- defer/errdefer → context managers
- Comptime → runtime

**Zig → Go:**
- Explicit allocators → GC
- defer preserved!
- OS threads → goroutines

**Zig → Rust:**
- Manual tracking → ownership (borrow checker!)
- defer → RAII (automatic Drop)

---

## Migration by Use Case

### Prototyping to Production

**Python → Go/Rust/C++ for production deployment:**

| From | To | Performance Gain | Migration Guide |
|------|----|-----------------|-----------------|
| Python | Go | 5-20x | [MIGRATE_PYTHON_TO_GO.md](MIGRATE_PYTHON_TO_GO.md) |
| Python | Rust | 20-100x | [MIGRATE_PYTHON_TO_RUST.md](MIGRATE_PYTHON_TO_RUST.md) |
| Python | C++ | 20-100x | [MIGRATION.md](MIGRATION.md#python--c) |

**Key benefits:** Performance, deployment simplicity (single binary), better concurrency.

### Web Deployment

**Any → TypeScript for browser/Node.js:**

| From | Migration Guide | Key Benefits |
|------|----------------|--------------|
| Python | [MIGRATE_PYTHON_TO_TYPESCRIPT.md](MIGRATE_PYTHON_TO_TYPESCRIPT.md) | Universal deployment, similar async |
| Go | [MIGRATE_GO_TO_TYPESCRIPT.md](MIGRATE_GO_TO_TYPESCRIPT.md) | Browser support, NPM ecosystem |
| Rust | [MIGRATE_RUST_TO_TYPESCRIPT.md](MIGRATE_RUST_TO_TYPESCRIPT.md) | Web deployment, easier maintenance |

**Key benefits:** Browser compatibility, universal code (frontend + backend), NPM ecosystem.

### Performance Optimization

**Move to compiled languages for speed:**

| From | To | Speed Improvement | Migration Guide |
|------|----|-----------------|-----------------|
| Python | Go | 5-20x | [MIGRATE_PYTHON_TO_GO.md](MIGRATE_PYTHON_TO_GO.md) |
| Python | Rust | 20-100x | [MIGRATE_PYTHON_TO_RUST.md](MIGRATE_PYTHON_TO_RUST.md) |
| TypeScript | Go | 5-10x | [MIGRATE_TYPESCRIPT_TO_GO.md](MIGRATE_TYPESCRIPT_TO_GO.md) |
| TypeScript | Rust | 10-20x | [MIGRATE_TYPESCRIPT_TO_RUST.md](MIGRATE_TYPESCRIPT_TO_RUST.md) |

**Key benefits:** Lower latency, higher throughput, reduced infrastructure costs.

### Memory Safety

**Move to Rust for compile-time memory safety:**

| From | Migration Guide | Safety Benefits |
|------|----------------|----------------|
| C++ | [MIGRATE_CPP_TO_RUST.md](MIGRATE_CPP_TO_RUST.md) | Eliminate use-after-free, data races |
| Python | [MIGRATE_PYTHON_TO_RUST.md](MIGRATE_PYTHON_TO_RUST.md) | Type safety, no null pointer crashes |
| Go | [MIGRATE_GO_TO_RUST.md](MIGRATE_GO_TO_RUST.md) | Stricter memory guarantees |

**Key benefits:** Prevents entire classes of bugs at compile time, fearless concurrency.

### Embedded Systems

**Move to Zig/Rust for embedded/low-level:**

| From | To | Migration Guide | Key Benefits |
|------|----|----------------|-------------|
| Python | Zig | [MIGRATION.md](MIGRATION.md#python--zig) | No GC, explicit control |
| C++ | Zig | [MIGRATE_CPP_TO_ZIG.md](MIGRATE_CPP_TO_ZIG.md) | Simpler language |
| Go | Zig | [MIGRATE_GO_TO_ZIG.md](MIGRATE_GO_TO_ZIG.md) | No GC, minimal runtime |

**Key benefits:** No garbage collector, predictable performance, minimal dependencies.

### Cross-Platform

**TypeScript for universal deployment:**

All languages → TypeScript for web + Node.js + mobile (React Native).

See [Migrating from TypeScript](#migrating-from-typescript) section for reverse migrations.

---

## Migration Quick Start

### Step 1: Read the Language Profile

Start with the **Language Profile** for your target language to understand:
- Language philosophy and idioms
- Type system features
- Error handling patterns
- Concurrency model
- Memory management

**Example:** Migrating Python → Go? Read [LANGUAGE_PROFILE_GO.md](LANGUAGE_PROFILE_GO.md) first.

### Step 2: Use the Quick Reference

Open the **Quick Reference guide** for your specific migration path:
- Side-by-side code examples
- Common gotchas
- Performance comparisons
- Migration checklist

**Example:** Migrating Python → Go? Use [MIGRATE_PYTHON_TO_GO.md](MIGRATE_PYTHON_TO_GO.md).

### Step 3: Follow the Migration Checklist

Each Quick Reference includes a migration checklist with 10-20 actionable items.

**Example checklist items:**
- [ ] Replace Python classes with Go structs
- [ ] Convert exceptions to explicit error returns
- [ ] Change asyncio to goroutines
- [ ] Update import statements
- [ ] Add context.Context parameters

### Step 4: Test and Validate

Run tests in both languages to verify behavioral equivalence.

See [Cross-Language Equivalence Testing](../tests/cross_language/README.md) for automated validation.

---

## Common Migration Patterns

### Message Creation

**All languages support the same Message structure** with minor syntax differences:

```python
# Python
msg = Message(role="user", content="Hello")
```

```go
// Go
msg := agenkit.Message{Role: agenkit.RoleUser, Content: "Hello"}
```

```typescript
// TypeScript
const msg: Message = { role: 'user', content: 'Hello' };
```

```rust
// Rust
let msg = Message { role: Role::User, content: "Hello".to_string(), ..Default::default() };
```

```cpp
// C++
Message msg{.role = "user", .content = "Hello"};
```

```zig
// Zig
var msg = try Message.init(allocator, "user", "Hello");
```

See individual Quick References for complete examples.

### Agent Implementation

**All languages implement the Agent interface** with three core methods:
1. `name` - Agent identifier
2. `capabilities` - List of capabilities
3. `process` - Message processing logic

See Language Profiles for language-specific implementation patterns.

### Error Handling

**Three main patterns across languages:**

1. **Exceptions** (Python, TypeScript, C++)
2. **Explicit returns** (Go, Rust)
3. **Error unions** (Zig)

See Quick References for conversion strategies.

### Concurrency

**Four main models:**

1. **asyncio** (Python) - Single-threaded event loop
2. **Promises** (TypeScript) - Single-threaded event loop
3. **Goroutines** (Go) - M:N green threads
4. **tokio** (Rust) - Work-stealing async runtime
5. **std::thread** (C++, Zig) - OS threads

See Language Profiles for detailed concurrency patterns.

---

## Performance Comparison Matrix

**Typical operation latencies** (lower is better):

| Operation | Python | TypeScript | Go | Rust | C++ | Zig |
|-----------|--------|------------|----|----|-----|-----|
| Message creation | 1μs | 500ns | 100ns | 50ns | 50ns | 50ns |
| Agent process | 10μs | 5μs | 1μs | 500ns | 500ns | 500ns |
| Sequential (3) | 30μs | 15μs | 3μs | 1.5μs | 1.5μs | 1.5μs |
| Parallel (3) | 20μs | 5μs | 1μs | 500ns | 500ns | 500ns |

**Throughput** (higher is better):

| Language | Messages/sec | Speedup vs Python |
|----------|-------------|-------------------|
| Python | 100K | 1x (baseline) |
| TypeScript | 200K | 2x |
| Go | 1M | 10x |
| Rust | 2M | 20x |
| C++ | 2M | 20x |
| Zig | 2M | 20x |

**Note:** Actual performance depends on workload, LLM latency, and I/O patterns.

---

## Additional Resources

### Core Documentation

- [Main Migration Guide](MIGRATION.md) - Comprehensive Python → all languages guide
- [Architecture Documentation](ARCHITECTURE.md) - Design principles and patterns
- [API Reference](API.md) - Complete API documentation
- [Testing Guide](../tests/cross_language/README.md) - Cross-language validation

### Language-Specific

- [Python README](../README.md)
- [Go README](../agenkit-go/README.md)
- [TypeScript README](../agenkit-ts/README.md)
- [Rust README](../agenkit-rust/README.md)
- [C++ README](../agenkit-cpp/README.md)
- [Zig README](../agenkit-zig/README.md)

### Examples

- [Python Examples](../examples/)
- [Go Examples](../agenkit-go/examples/)
- [TypeScript Examples](../agenkit-ts/examples/)
- [Rust Examples](../agenkit-rust/examples/)
- [C++ Examples](../agenkit-cpp/examples/)
- [Zig Examples](../agenkit-zig/examples/)

---

## Contributing

Found an issue or want to improve the migration guides?

1. **File an issue:** [GitHub Issues](https://github.com/scttfrdmn/agenkit/issues)
2. **Submit a PR:** [Contributing Guide](../.github/CONTRIBUTING.md)
3. **Verify examples:** See issue [#247](https://github.com/scttfrdmn/agenkit/issues/247)

---

## Document Version

**Version:** 1.0
**Last Updated:** January 14, 2026
**Agenkit Version:** v0.46.0+
**Coverage:** 6 Language Profiles + 28 Quick References = 100% bidirectional migration coverage

---

**Navigation:** [↑ Back to Top](#agenkit-migration-guide-index)
