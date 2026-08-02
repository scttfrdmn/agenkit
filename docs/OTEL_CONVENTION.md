# Agenkit OpenTelemetry Convention

**Status:** normative for span names, attribute keys, resource attributes, and
trace propagation. Consumers may rely on everything in the [Stable](#stability)
sections; [Planned](#stability) sections are not yet emitted by any language.

This is the contract for producing traces that agenkit tooling — and AWS
AgentCore Observability, CloudWatch, and Jaeger — consume without a
consumer-specific adapter. If you are emitting spans from a workload that
orchestrates agenkit agents (a decomposition tree, a map-reduce, a multi-agent
fan-out), follow this document rather than inventing keys.

Agenkit adopts the **OpenTelemetry GenAI semantic conventions** (`gen_ai.*`) as
its baseline and adds a small `agenkit.*` namespace for concepts GenAI semconv
does not cover. Where a GenAI attribute exists, agenkit uses it verbatim rather
than defining a synonym.

---

## Stability

| Section | Status | Meaning |
|---|---|---|
| [Span naming](#span-naming) | **Stable in Python/Go/TS/Rust** | C++ defaults to a different name; Zig hand-rolls spans — see the caveats |
| [Trace propagation](#trace-propagation) | **Stable in Python/Go/TS/Rust/C++** | The cross-language primitive, and the most reliable part of the current implementation. Zig does not participate. |
| [Resource attributes](#resource-attributes) | **Stable in Python/Go/Rust** | C++ sets none — see the caveats |
| [Agent span attributes](#agent-span-attributes) | **Stable** | Emitted today |
| [Span status](#span-status) | **Stable in Python/Go/TS/Rust/C++** | Ok / Error set by every implementation. The error *event* is Python/Go/TS only. |
| [GenAI attributes](#genai-attributes) | **Planned** | Not emitted by any language yet — see [Gaps](#known-gaps) |
| [Tree-node spans](#tree-node-spans) | **Planned** | No helper exists in any language yet |

"Planned" means the key is reserved and specified here so that consumers and
agenkit converge on the same name when it lands. Do not read a Planned key
expecting a value.

---

## Span naming

An agent invocation produces one span:

```
agent.{agent_name}.process
```

`{agent_name}` is the agent's own `Name()`/`name`. Emitted by
`TracingMiddleware` in Python, Go, TypeScript, and Rust; overridable via the
middleware's `span_name` option.

**C++ diverges:** its `TracingMiddleware` defaults to the literal
`agent.process` with no agent name interpolated
(`agenkit-cpp/include/agenkit/observability/tracing.hpp:183`), so C++ spans are
not distinguishable by agent without reading the `agent.name` attribute. Pass
`span_name` explicitly to match the convention.

**Zig is not comparable:** `agenkit-zig/src/observability/tracing.zig`
implements spans by hand (`SpanContext` with `root()`/`child()` and
traceparent encode/decode) rather than using an OTel SDK, and does not name
spans by this convention.

The tracer (instrumentation scope) name is:

```
agenkit.observability
```

…in Python, Go, and Rust. **TypeScript diverges:** it uses `@agenkit/core`
(version `0.2.0`) at `agenkit-ts/src/observability/tracing.ts:114`, and the
string `agenkit.observability` appears nowhere in `agenkit-ts/src/`. A consumer
filtering spans by instrumentation scope must match both names until that is
reconciled.

Consumers creating their own spans should use their own instrumentation scope
name, not agenkit's — the scope identifies who produced the span, and
mislabelling it makes agenkit-emitted and consumer-emitted spans
indistinguishable.

## Trace propagation

Agenkit propagates trace context **in-band, through message metadata**, because
agent-to-agent calls are not necessarily in-process or same-language.

- Metadata key: `trace_context`
- Format: W3C Trace Context (`traceparent`, plus `tracestate`/baggage when present)
- Injected on egress, extracted on ingress, by `TracingMiddleware`

```python
# Python — the wire form
message.metadata["trace_context"] = {"traceparent": "00-<trace-id>-<span-id>-01"}
```

A consumer that receives an agenkit `Message` and wants its spans parented
correctly must extract from `metadata["trace_context"]`; a consumer that calls
into agenkit should inject into it. This is the single most important part of
this document for cross-process and cross-language cases — the ambient
in-process OTel context does **not** cross an agent boundary on its own.

Implemented in Python, Go, TypeScript, Rust, and C++. **Zig does not
participate:** `agenkit-zig/src/observability/tracing.zig` contains no
`trace_context` handling, so a trace does not survive a hop through a Zig
agent. Zig can encode/decode a traceparent (`SpanContext.toTraceparent` /
`fromTraceparent`) but nothing wires that to message metadata.

`trace_context` is excluded from the `agenkit.message.metadata.*` attribute
promotion described below, so it never appears as a span attribute.

## Resource attributes

| Attribute | Source | Notes |
|---|---|---|
| `service.name` | caller-supplied | Set it to **your** service name, not `agenkit` |

Python (`init_tracing(service_name=...)`), Go (`InitTracing(serviceName, ...)`),
and Rust (`init_tracing_with_config(exporter, endpoint, service_name, sample_rate)`)
accept it.

Rust's two-argument `init_tracing` does **not** set `service.name`, which leaves
the SDK's own `OTEL_SERVICE_NAME` / `OTEL_RESOURCE_ATTRIBUTES` detection in
place. That is deliberate: the previous behaviour hardcoded
`service.name = "agenkit"`, which silently defeated the environment variable a
deployment had already set. Use `init_tracing_with_config` to set it in code
(#768).

> **Known gap — C++.** `agenkit-cpp/src/observability/tracing.cpp` sets no
> resource attributes at all, so `service.name` falls back to whatever the SDK
> default is. C++ consumers should configure the resource themselves.

## Agent span attributes

Emitted today on every `agent.{name}.process` span:

| Attribute | Type | Meaning |
|---|---|---|
| `agent.name` | string | The agent's name. An agenkit extension — GenAI semconv has no equivalent for a named in-process agent. |
| `message.role` | string | `user` / `assistant` / `system` |
| `message.content_length` | int | Character length of the rendered content. Not a token count. **Not emitted by C++.** |
| `message.metadata.{key}` | string/int/int64/float/bool | Scalar entries from `Message.metadata`, promoted individually. Non-scalar values are skipped; `trace_context` is always excluded. |

Note `message.content_length` is a character count and is **not** a substitute
for token usage. See [Gaps](#known-gaps).

### Span status

Every implementation sets the span status: `Ok` when the agent returns
successfully, `Error` with the error message as the description when it does not.
Consumers should filter failures on **span status**, not on an attribute.

Python (`record_exception`), Go (`RecordError`), and TypeScript
(`recordException`) also record the error as a span event. Rust and C++ do not;
Rust instead sets an `error=true` attribute. Do not rely on either the event or
the attribute cross-language — the status is the portable signal.

**A failed verification is not an error status.** These are different claims and
must map to different signals:

| Situation | Span status | Rationale |
|---|---|---|
| The operation did not complete (exception, timeout, truncated/unreturnable node) | `Error` | Nothing produced a result. This is what OTel's error status means. |
| The operation completed and returned an unfavourable verdict (`agenkit.verifier.verdict = failed`) | `Ok` | The check ran and worked. The *answer* was bad, not the *run*. |

Setting `Error` on a failed verification makes a functioning verifier
indistinguishable from a broken pipeline, and inflates every error-rate alert in
proportion to how well the verifier is doing its job. Record the verdict in
`agenkit.verifier.verdict` and leave the status `Ok`.

## GenAI attributes

**Planned — not emitted by any language today.** Reserved names, so that
consumers emitting them now will match agenkit when it starts emitting them.
Use the OTel GenAI semconv key verbatim:

| Attribute | Type | Meaning |
|---|---|---|
| `gen_ai.system` | string | Provider, e.g. `anthropic`, `aws.bedrock`, `openai` |
| `gen_ai.request.model` | string | Model id **as requested** — may be an alias |
| `gen_ai.response.model` | string | Model id **as served**, resolved to an explicit version. Record both: charting cost against an alias silently mixes model versions. |
| `gen_ai.usage.input_tokens` | int | |
| `gen_ai.usage.output_tokens` | int | |
| `gen_ai.operation.name` | string | e.g. `chat` |

Agenkit extensions, for concepts GenAI semconv does not cover:

| Attribute | Type | Meaning |
|---|---|---|
| `agenkit.usage.cache_read_tokens` | int | Prompt-cache tokens read (see #665) |
| `agenkit.usage.cache_creation_tokens` | int | Prompt-cache tokens written |
| `agenkit.cost.micro_units` | int64 | Integer micro-units, **not** a float. Float currency accumulates rounding error across a large span tree. State the currency out of band. |
| `agenkit.retry.count` | int | **Transport** retries — a call failed and was reissued. |
| `agenkit.verify.retries` | int | **Quality** retries — a call succeeded, its output was rejected by a verifier, and it was reissued. |

Those last two are deliberately separate keys. Both cost money and latency, but
they mean opposite things about the system: transport retries indicate an
unreliable dependency, quality retries indicate a model that is not meeting the
bar. Summing them into one counter makes neither diagnosable.

## Tree-node spans

**Planned — no helper exists in any language today.** A consumer with a
tree-shaped workload must currently call `tracer.Start` directly. Until an
agenkit helper lands, emit the following so the eventual helper is
drop-in-compatible.

The rule: **the span tree *is* the workload tree.** One span per node, each
node's span parented to its parent node's span. Do not flatten a tree into
sibling spans and reconstruct it from attributes — the parent/child linkage is
what makes the trace readable in Jaeger without a custom view.

### Live, not post-hoc

The helper should start the span when the node *starts*, while the parent context
is in hand — not build the tree after the run from buffered nodes. Buffering is
tempting when a workload's completion callback fires child-before-parent (so the
nesting does not exist yet at emission time), but it costs two things worth more
than the convenience: nothing appears in the trace backend until the whole run
ends, and the spans carry no measured durations, only fabricated or absent ones.
A consumer cannot tell an invented duration from a measured one.

The API shape that supports both orders:

```
StartNode(ctx, parentSpanCtx, nodeID) (ctx, span)
```

Taking the parent explicitly, rather than only implicitly from `ctx`, lets a
caller whose completion order is inverted still produce correct parentage without
buffering the whole tree.

| Attribute | Type | Meaning |
|---|---|---|
| `agenkit.node.id` | string | Stable id for this node |
| `agenkit.node.parent_id` | string | Parent's node id. Redundant with span parentage, and worth emitting anyway: it survives sampling that drops the parent span. |
| `agenkit.node.depth` | int | 0 at the root |
| `agenkit.node.state` | string | Node lifecycle state |
| `agenkit.node.base_case_reason` | string | Why recursion stopped at this node. Absent on non-terminal nodes. |
| `agenkit.node.gap` | string | Why this node produced no usable result (truncated, unreturnable). A node with a gap **also** sets span status `Error` — unlike a failed verification. |

### Flush obligation

Any tree helper that buffers spans must make the final flush impossible to
forget, or make forgetting it loud. A buffering exporter whose flush is never
called is total silent failure: every span is held, nothing is exported, and no
error is raised anywhere. Prefer a live-wrapped design that holds the parent
context and needs no buffer at all; where buffering is unavoidable, the flush
belongs in a guard type whose `Drop` runs it, not in a method the caller is
trusted to remember.

### Verifier outcome

`agenkit.verifier.verdict` is a **string enum with three values**, not a
boolean:

| Value | Meaning |
|---|---|
| `passed` | Verified and correct |
| `failed` | Verified and incorrect |
| `not_assessed` | **No verification was attempted** |

`not_assessed` is a genuine third state and must not be collapsed into
`failed`. "We did not check" and "we checked and it was wrong" support opposite
decisions: the first says spend more budget, the second says stop. A boolean
here destroys that distinction irrecoverably — the value is already lost by the
time it reaches the collector.

> **Agenkit's own `Verifier` cannot currently express this.**
> `agenkit/reasoning/verifier.py:27` defines
> `VerificationResult.passed: bool` — two states, with `score: float` and
> `reason: str` alongside; Go matches it exactly at
> `agenkit-go/agenkit/interfaces.go:257`. There is no representation for "not
> assessed", and both docstrings describe verification as "exact and binary". So a
> consumer that has a three-state verdict (quarry does) cannot round-trip it
> through agenkit's verifier types, and an unverified artifact is
> indistinguishable from a failed one.
>
> This attribute is specified with three states anyway, because the span is
> where the distinction matters most and because widening
> `VerificationResult` later is source-compatible for readers of `passed`.
> Consumers should emit `agenkit.verifier.verdict` directly rather than deriving
> it from a `VerificationResult`. Tracked in #769.

## Collector endpoint

Agenkit **should** honour the spec-named environment variable:

```
OTEL_EXPORTER_OTLP_ENDPOINT
```

**Rust honours it.** Passing `None` as the endpoint defers to the OTLP exporter's
own resolution: `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`, then
`OTEL_EXPORTER_OTLP_ENDPOINT`, then the spec default `http://localhost:4317`. An
explicitly passed endpoint overrides all three.

> **Python, Go, TypeScript, and C++ do not.** In those languages the endpoint is
> a positional/config parameter, and if it is absent no OTLP exporter is
> constructed at all — no environment variable is consulted. **Pass it
> explicitly there.**
>
> Several doc sites claim otherwise and disagree on the name:
> `docs/observability.md:480` and `INSTALLATION.md:386` use the spec name
> `OTEL_EXPORTER_OTLP_ENDPOINT` (and `INSTALLATION.md:389` adds
> `OTEL_SERVICE_NAME`), while `agenkit-cpp/docs/OBSERVABILITY.md:628` uses a
> non-spec `OTLP_ENDPOINT`. Tracked in #771.

## Known gaps

Documented so consumers do not plan around capabilities that do not exist:

1. **No token, cost, or model attribute is emitted on any span, in any
   language.** Usage data exists only as untyped `Message.metadata["usage"]`,
   set by some adapters, and is never promoted onto a span. Typed usage is #664;
   Bedrock cache counts are #665; promotion onto spans is #715.
2. **No tree/DAG span helper exists.** `TracingMiddleware` wraps a single
   `Agent.Process` and derives the span name from the agent name; there is no
   "start a span for node N parented to node P" API.
3. **Go's semconv pin is `v1.17.0`** (`agenkit-go/observability/tracing.go`),
   predating the GenAI conventions.
4. **`init_metrics` exports nothing in Rust**, for any exporter type, while
   returning success (#772).

## Cross-references

- #711 — the consumer request this document answers
- #715 — the remaining implementation work: GenAI attributes on spans, tree-node helper, Go semconv bump
- #771 — documented env vars that no implementation reads
- #769 — `VerificationResult.passed` cannot express `not_assessed`
- #768 — Rust OTLP export, `service.name`, and span status (fixed)
- #772 — Rust `init_metrics` installs no exporter
- #664 — typed `Usage` (prerequisite for emitting token attributes)
- #665 — Bedrock prompt-cache token counts
