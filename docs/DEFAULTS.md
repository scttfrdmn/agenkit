# Canonical Default Configuration Values

This document is the authoritative reference for default configuration values across
all agenkit language implementations. When adding a new language or pattern, consult
this table to ensure consistency.

## Default Values by Setting

| Setting | Python | Go | TypeScript | Rust | C++ | Zig |
|---|---|---|---|---|---|---|
| `max_history` | `10` | `10` | `10` | `10` | `10` | `10` |
| `max_steps` | `10` | `10` | `10` | `10` | `10` | `10` |
| `verbose` | `False` | `false` | `false` | `false` | `false` | `false` |
| `include_system` | `True` | `true` | `true` | `true` | `true` | `true` |
| `checkpoint max_depth` | `10` | `10` | `10` | `10` | `10` | `10` |
| `default_key` / `route` | `None` | `nil` | `undefined` | `None` | `nullptr` | `null` |

## Equivalent Initialization Patterns

The following examples show how to configure the same settings in each language.

### ConversationalAgent with max_history=20

**Python (recommended)**
```python
from agenkit.patterns import ConversationalAgent, ConversationalAgentConfig

config = ConversationalAgentConfig(llm_client=llm, max_history=20)
agent = ConversationalAgent(config)
```

**Go**
```go
agent, err := patterns.NewConversationalAgent(&patterns.ConversationalConfig{
    Agent:      llmAgent,
    MaxHistory: 20,
})
```

**TypeScript**
```typescript
const agent = new ConversationalAgent({
  llmClient: llm,
  maxHistory: 20,
});
```

**Rust**
```rust
let agent = ConversationalAgent::new(ConversationalConfig {
    llm_client: llm,
    max_history: 20,
    ..Default::default()
});
```

### ReActAgent with verbose=true, max_steps=15

**Python**
```python
from agenkit.patterns import ReActAgent, ReActConfig

config = ReActConfig(agent=llm_agent, tools=tools, verbose=True, max_steps=15)
agent = ReActAgent(config)
```

**Go**
```go
agent, err := patterns.NewReActAgent(&patterns.ReActConfig{
    Agent:    llmAgent,
    Tools:    tools,
    Verbose:  true,
    MaxSteps: 15,
})
```

**TypeScript**
```typescript
const agent = new ReActAgent({
  agent: llmAgent,
  tools,
  verbose: true,
  maxSteps: 15,
});
```

### RouterAgent with defaultKey

**Python**
```python
from agenkit.patterns import RouterAgent, RouterConfig

config = RouterConfig(agents=agents, default_key="fallback")
agent = RouterAgent(config)
```

**Go**
```go
agent, err := patterns.NewRouterAgent(&patterns.RouterConfig{
    Agents:     agents,
    DefaultKey: "fallback",
})
```

## Notes on Specific Defaults

### `verbose` (default: `false`)

In all languages, `verbose` defaults to `false`. When `verbose=true`, the agent
includes full step-by-step reasoning traces in its final output — useful for
debugging but noisy in production.

> **Go change (v0.69.0):** Prior to v0.69.0, Go's `ReActAgent` incorrectly
> defaulted `Verbose` to `true` when no config fields were set. This was a bug
> — the zero value of `bool` in Go is `false`, which is the correct canonical
> default. Code that relied on the old implicit `verbose=true` behavior should
> now set `Verbose: true` explicitly.

### `max_history` / `max_steps` (default: `10`)

Both settings cap the amount of state an agent accumulates. The default of `10`
is a reasonable balance for most workloads. Increase for long-running agents that
need more context; decrease to reduce token usage.

### `include_system` (default: `true`)

When `true`, the system prompt is stored as the first message in the conversation
history and is included in every LLM call. Set to `false` only if the underlying
LLM client handles system prompts through a separate API parameter.

### `default_key` / `default_route` (default: `None`/`nil`)

The router's fallback destination when no routing rule matches. If `None`/`nil`,
unmatched messages raise an error. Set to a valid agent key to enable graceful
fallback routing.

## TTL Expiration Semantics

All languages implement TTL-based cache expiration with equivalent semantics:
**keep an entry if its age is strictly less than the configured TTL**.

### Per-language expiration checks

**Python** (`agenkit/memory/memory.py:314`):
```python
# Keep entry if age < ttl
if now - e.timestamp < self.ttl:
    valid_entries.append(e)
```

**Go** (`agenkit-go/memory/memory.go:311`):
```go
// Keep entry if age < ttl
if now.Sub(entry.Timestamp) < s.ttl {
    valid = append(valid, entry)
}
```

**TypeScript** (`agenkit-ts/src/memory/memory.ts`):
```typescript
// Keep entry if age < ttl
if (Date.now() - entry.timestamp < this.ttlMs) {
  valid.push(entry);
}
```

**Rust** (`agenkit-rust/src/memory/entry.rs:62`):
```rust
// Note: inverted boolean — is_expired returns true when age >= ttl
pub fn is_expired(&self, ttl_seconds: i64) -> bool {
    let age = Utc::now() - self.timestamp;
    age.num_seconds() >= ttl_seconds
}
// Caller: keep entry if !entry.is_expired(ttl)
```

**C++** (`agenkit-cpp/src/memory/memory.cpp`):
```cpp
// Keep entry if age < ttl
auto age = std::chrono::steady_clock::now() - entry.timestamp;
if (age < ttl_) {
    valid.push_back(entry);
}
```

**Zig** (`agenkit-zig/src/memory/memory.zig`):
```zig
// Keep entry if age < ttl
const age = std.time.milliTimestamp() - entry.timestamp_ms;
if (age < self.ttl_ms) {
    try valid.append(entry);
}
```

### Equivalence note

All implementations produce the same result. The Rust `is_expired` helper uses an
**inverted boolean** (`age >= ttl` returns `true` meaning expired) while the other
languages use a direct keep-if-less-than check — both express identical semantics.
Rust callers filter with `!entry.is_expired(ttl)`.

The boundary condition (`age == ttl` exactly) is treated as expired in all languages:
Python and Go use `<` (strict), Rust uses `>=` for the expired check (equivalent).

## `TestCase.expected` Matching Semantics

When `TestCase.expected` is a **string**, it is a **fragment to find in the agent's
output**, compared **case-insensitively** — not the whole expected output.

An agent answering `"The answer is 42."` **passes** `expected = "42"`. This is
deliberate: benchmarks store the fact to look for, and agents answer in prose. The
reference implementation's own data depends on it — `agenkit/evaluation/benchmarks.py`
carries `expected="5",  # "5pm" or "5:00pm" both match`.

| Core | Site | Comparison |
|------|------|-----------|
| Python | `_check_test` / `AccuracyMetric` | `expected.lower() in actual.lower()` |
| Go | `TestCase.Validate` / `checkTest` / `AccuracyMetric` | `strings.Contains`, lowered unless `caseSensitive` |
| TypeScript | `checkTest` / `AccuracyMetric` | `actual.includes(expected)`, lowered |
| Rust | `TestCase::validate` / `check_test` / `AccuracyMetric` | `actual.contains(expected)`, lowered unless `case_sensitive` |
| C++ | `TestCase::validate` / `AccuracyMetric` | `actual.find(expected) != npos`, lowered |
| Zig | `TestCase.validate` / `AccuracyMetric` | case-insensitive `indexOf` |

Where a core has both a `TestCase` method and a runner-side check, the runner
**delegates** to the method rather than reimplementing the comparison. Two
independent implementations of "case-insensitive substring" is precisely how the
three-way divergence in #820 and the ASCII-vs-Unicode split in #823 arose.

### Notes

- **An empty `expected` matches everything.** `"" in x`, `strings.Contains(x, "")`,
  `x.includes("")` are all true, so the contract follows suit rather than special-casing.
  C++'s `TestCase::from_json` therefore substitutes an always-false validator for a
  function-variant `expected` it cannot deserialize — leaving the empty string it used
  to leave would make every round-tripped case pass unconditionally.
- **Need exact or case-sensitive matching?** Use the validator-function variant
  (`initFunctional` in Zig, the `std::function` alternative in C++, a callable
  `expected` in Python/TypeScript, `validator` in Go/Rust).
- `AccuracyMetric` exposes a `case_sensitive` flag (default `false`) in every core. It
  controls **case only** — it does not restore whole-string comparison.
- C++ and Zig previously compared with `==` / `mem.eql` at the `TestCase::validate`
  site. C++ thereby contradicted its own `AccuracyMetric`, and Zig's `SimpleQABenchmark`
  — whose expected values are `"42"`, `"Paris"`, `"Not necessarily"` — scored a correct
  agent near zero. Fixed in #820.
- Go and Rust gained a `TestCase.Validate()` / `TestCase::validate()` in #823, so all
  six cores now expose the contract on the test case itself. Two runner-side bugs were
  fixed with it:
  - **Rust's `Evaluator` never consulted `expected` at all.** `passed_tests` was
    incremented for any `Ok(process())`, so `success_rate()` measured "the agent did not
    error" and a wrong answer scored `1.0`. Its own test asserted that as correct.
  - **Go's `checkTest` lowered ASCII `A-Z` only**, via a hand-rolled helper, while
    `AccuracyMetric` used `strings.ToLower`. A Greek, Cyrillic or umlauted `expected`
    therefore failed the pass count and scored `1.0` on the metric in the same run.
- C++ has no `Evaluator`, so it has no runner-side check to align; Zig validates
  directly via `TestCase.validate`.

### A/B testing scores by the same contract

`ABTest` is a third scoring site, and it is bound by the table above: `expected` is
a fragment, matched case-insensitively. Go and Rust now delegate to
`TestCase.Validate` / a `Metric` rather than open-coding a comparison (#822).

| Core | A/B accuracy | Notes |
|------|--------------|-------|
| Python | `expected.lower() in actual.lower()` | inline |
| Go | `TestCase.Validate` | delegates (#822) |
| TypeScript | `actual.toLowerCase().includes(expected.toLowerCase())` | inline |
| Rust | `AccuracyMetric` via `metric_for(metric_name)` | delegates (#822) |
| C++ | reads response **metadata**, never `expected` | divergent — #829 |

- **Rust's `ab_testing.rs` used trimmed, case-sensitive, whole-string equality** — a
  third semantics, distinct from both the table above and this core's own
  `AccuracyMetric`. Since `expected` holds a fragment, a correct agent answering in
  prose scored `0.0` — for *both* arms, reporting `winner = "inconclusive"` with a
  p-value and effect size attached, so nothing indicated the scoring never worked. It
  also ignored its `metric_name` argument outright. Fixed in #822.
- **Go's A/B site had its own hand-rolled lowering**, distinct from the one #823
  removed from `checkTest`: it sized the rune buffer by *byte* length
  (`make([]rune, len(s))`) while ranging by byte offset, so every multi-byte rune left
  NUL padding — `"ПАРИЖ"` became `"П\x00А\x00Р\x00И\x00Ж\x00"`. That is worse than
  ASCII-only lowering, which at least leaves non-`A-Z` input intact. Fixed in #822.
- **`metric_name` in Rust's `ABTest::run` selects the metric.** `"accuracy"`,
  `"quality"`, `"latency"` and `"context_length"` resolve to the corresponding
  `Metric`; an unrecognised name is an `AgentError::InvalidInput`, not a silent
  fallback to accuracy.
- **An absent `expected` key is not yet consistent across the A/B sites.** Python and
  Go score it `1.0` (consistent with "an empty `expected` matches everything" above);
  TypeScript's `expected && ...` short-circuits to `0.0`. Tracked in #827 along with
  the same question for `Metric` implementations generally.
- **C++'s `ABTest` reached a `TestCase` that had no `validate()` at all** — the header
  defined a second struct of that name, so `ABTest` could not honour this contract even
  in principle. Unified in #831; there is now exactly one
  `agenkit::evaluation::TestCase`, and wiring `ABTest` to score `expected` through it is
  #829.

## Related Documentation

- [Migration Guides](migrations/) — step-by-step upgrade instructions
- [Framework Comparison Matrix](framework_comparison_matrix.md) — per-framework
  defaults and feature support
- [ARCHITECTURE.md](../ARCHITECTURE.md) — design principles behind these choices
- [TYPE_VALIDATION.md](TYPE_VALIDATION.md) — per-language type checking patterns
