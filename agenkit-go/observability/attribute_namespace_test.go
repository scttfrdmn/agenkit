package observability

import (
	"context"
	"os"
	"regexp"
	"strings"
	"testing"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"go.opentelemetry.io/otel/codes"
)

// This file implements #783: an attribute-namespace test that catches the
// first divergence between docs/OTEL_CONVENTION.md and what TracingMiddleware
// actually emits, per the #715 thread's own description of the idea ("an
// attribute is either gen_ai.* or quarry.*, an unlisted key is a bug" — stolen
// here as "gen_ai.* or agenkit.*, plus the grandfathered pre-GenAI keys").

// allowedExactKeys are the grandfathered pre-GenAI attribute keys
// docs/OTEL_CONVENTION.md's "Agent span attributes" table permits outside the
// gen_ai.*/agenkit.* namespaces.
var allowedExactKeys = map[string]bool{
	"agent.name":             true,
	"message.role":           true,
	"message.content_length": true,
}

// allowedKeyPrefixes covers message.metadata.{key}, which is documented as a
// prefix rather than a fixed key.
var allowedKeyPrefixes = []string{
	"message.metadata.",
}

// docKeys are every literal attribute key that appears in a `| \`key\` |
// ...` row of docs/OTEL_CONVENTION.md's tables, gathered by
// TestAllEmittedKeysAppearInDoc via docKeysFromConvention() so the two checks
// ("is it gen_ai.*/agenkit.*" and "is it actually documented") share one
// source of truth instead of two hand-maintained lists silently drifting
// apart.
var docKeyPattern = regexp.MustCompile("`([a-zA-Z0-9_.{}]+)`")

// otelConventionPath locates docs/OTEL_CONVENTION.md relative to this test
// file's package (agenkit-go/observability), independent of the working
// directory `go test` is invoked from.
const otelConventionPath = "../../docs/OTEL_CONVENTION.md"

// keysDocumentedInConvention returns the literal attribute-key cells from
// docs/OTEL_CONVENTION.md's tables (the first backtick-quoted token on any
// `| \`...\` | ... |` row). Read from disk rather than duplicated inline so
// the test fails the moment the doc and the code disagree, instead of the
// moment someone remembers to update a second copy.
func keysDocumentedInConvention(t *testing.T) map[string]bool {
	t.Helper()
	raw, err := os.ReadFile(otelConventionPath)
	if err != nil {
		t.Fatalf("reading %s: %v", otelConventionPath, err)
	}
	data := string(raw)

	keys := make(map[string]bool)
	for _, line := range strings.Split(data, "\n") {
		line = strings.TrimSpace(line)
		if !strings.HasPrefix(line, "|") {
			continue
		}
		matches := docKeyPattern.FindAllStringSubmatch(line, -1)
		if len(matches) == 0 {
			continue
		}
		// The key is always the first backtick-quoted token in a table row in
		// this doc's tables (column 1 is "Attribute" in every table this test
		// cares about).
		key := matches[0][1]
		keys[key] = true
	}
	return keys
}

// isDocumented reports whether a span attribute key matches something
// documented in docs/OTEL_CONVENTION.md, accounting for the doc's use of
// `{key}`/`{name}` placeholders for dynamic suffixes
// (message.metadata.{key}).
func isDocumented(key string, docKeys map[string]bool) bool {
	if docKeys[key] {
		return true
	}
	for docKey := range docKeys {
		if !strings.Contains(docKey, "{") {
			continue
		}
		prefix := docKey[:strings.Index(docKey, "{")]
		if prefix != "" && strings.HasPrefix(key, prefix) {
			return true
		}
	}
	return false
}

// isNamespacedOrGrandfathered reports whether key is gen_ai.*, agenkit.*, or
// one of the small set of pre-GenAI keys docs/OTEL_CONVENTION.md grandfathers.
func isNamespacedOrGrandfathered(key string) bool {
	if strings.HasPrefix(key, "gen_ai.") || strings.HasPrefix(key, "agenkit.") {
		return true
	}
	if allowedExactKeys[key] {
		return true
	}
	for _, prefix := range allowedKeyPrefixes {
		if strings.HasPrefix(key, prefix) {
			return true
		}
	}
	return false
}

// llmLikeTestAgent stands in for an agent whose Process wraps an LLM call: it
// returns a response carrying the well-known GenAI metadata keys an
// adapter/llm adapter sets (gen_ai_system, request_model, response_model,
// usage with cache tokens), plus the cost/retry counters, so the test drives
// a representative call through every promotion path #782 added.
type llmLikeTestAgent struct{}

func (a *llmLikeTestAgent) Name() string           { return "llm-agent" }
func (a *llmLikeTestAgent) Capabilities() []string { return []string{"chat"} }
func (a *llmLikeTestAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{AgentName: a.Name(), Capabilities: a.Capabilities()}
}

func (a *llmLikeTestAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	return &agenkit.Message{
		Role:    "agent",
		Content: "hello from the model",
		Metadata: map[string]interface{}{
			agenkit.MetadataKeyGenAISystem:   "aws.bedrock",
			agenkit.MetadataKeyRequestModel:  "us.anthropic.claude-sonnet-5",
			agenkit.MetadataKeyResponseModel: "us.anthropic.claude-sonnet-5",
			"usage": map[string]interface{}{
				"prompt_tokens":         int32(1000),
				"completion_tokens":     int32(50),
				"total_tokens":          int32(1050),
				"cache_read_tokens":     int32(900),
				"cache_creation_tokens": int32(100),
			},
			agenkit.MetadataKeyCostMicroUnits: int64(42),
			agenkit.MetadataKeyRetryCount:     int64(1),
			agenkit.MetadataKeyVerifyRetries:  int64(2),
			"plain_string_field":              "keep-me",
		},
	}, nil
}

func TestAttributeNamespace_EveryKeyIsGenAIOrAgenkitOrGrandfathered(t *testing.T) {
	provider, exporter := setupTestTracing(t)
	defer func() { _ = provider.Shutdown(context.Background()) }()
	exporter.Reset()

	agent := &llmLikeTestAgent{}
	traced := NewTracingMiddleware(agent, "")

	_, err := traced.Process(context.Background(), &agenkit.Message{Role: "user", Content: "hi"})
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}
	_ = provider.ForceFlush(context.Background())

	spans := exporter.GetSpans()
	if len(spans) != 1 {
		t.Fatalf("expected 1 span, got %d", len(spans))
	}

	for _, attr := range spans[0].Attributes {
		key := string(attr.Key)
		if key == "trace_context" {
			t.Errorf("trace_context must never appear as a span attribute, found: %s", key)
		}
		if !isNamespacedOrGrandfathered(key) {
			t.Errorf("attribute key %q is neither gen_ai.*, agenkit.*, nor a grandfathered pre-GenAI key", key)
		}
	}
}

func TestAttributeNamespace_EveryEmittedKeyIsDocumented(t *testing.T) {
	provider, exporter := setupTestTracing(t)
	defer func() { _ = provider.Shutdown(context.Background()) }()
	exporter.Reset()

	agent := &llmLikeTestAgent{}
	traced := NewTracingMiddleware(agent, "")

	_, err := traced.Process(context.Background(), &agenkit.Message{Role: "user", Content: "hi"})
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}
	_ = provider.ForceFlush(context.Background())

	spans := exporter.GetSpans()
	if len(spans) != 1 {
		t.Fatalf("expected 1 span, got %d", len(spans))
	}

	docKeys := keysDocumentedInConvention(t)
	if len(docKeys) == 0 {
		t.Fatal("keysDocumentedInConvention returned no keys — the doc parser or the doc path is broken, which would make this test vacuously pass")
	}

	for _, attr := range spans[0].Attributes {
		key := string(attr.Key)
		if !isDocumented(key, docKeys) {
			t.Errorf("attribute key %q was emitted but does not appear in docs/OTEL_CONVENTION.md's tables", key)
		}
	}
}

func TestAttributeNamespace_TraceContextNeverPromoted(t *testing.T) {
	provider, exporter := setupTestTracing(t)
	defer func() { _ = provider.Shutdown(context.Background()) }()
	exporter.Reset()

	agent := &SimpleTestAgent{name: "agent1", response: "response"}
	traced := NewTracingMiddleware(agent, "")

	// Message carries an inbound trace_context (as if it arrived from another
	// agent), which must never be promoted to a plain span attribute even
	// though it is a "scalar-ish" map value under generic promotion rules.
	message := &agenkit.Message{
		Role:    "user",
		Content: "test",
		Metadata: map[string]interface{}{
			"trace_context": map[string]interface{}{"traceparent": "00-abc-def-01"},
		},
	}
	_, err := traced.Process(context.Background(), message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}
	_ = provider.ForceFlush(context.Background())

	spans := exporter.GetSpans()
	if len(spans) != 1 {
		t.Fatalf("expected 1 span, got %d", len(spans))
	}
	for _, attr := range spans[0].Attributes {
		if string(attr.Key) == "trace_context" || strings.Contains(string(attr.Key), "trace_context") {
			t.Errorf("trace_context leaked onto a span attribute: %s", attr.Key)
		}
	}
}

func TestAttributeNamespace_SpanNameAndScope(t *testing.T) {
	provider, exporter := setupTestTracing(t)
	defer func() { _ = provider.Shutdown(context.Background()) }()
	exporter.Reset()

	agent := &SimpleTestAgent{name: "checkout", response: "ok"}
	traced := NewTracingMiddleware(agent, "")

	_, err := traced.Process(context.Background(), &agenkit.Message{Role: "user", Content: "hi"})
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}
	_ = provider.ForceFlush(context.Background())

	spans := exporter.GetSpans()
	if len(spans) != 1 {
		t.Fatalf("expected 1 span, got %d", len(spans))
	}

	if want := "agent.checkout.process"; spans[0].Name != want {
		t.Errorf("span name = %q, want %q", spans[0].Name, want)
	}
	if want := "agenkit.observability"; spans[0].InstrumentationScope.Name != want {
		t.Errorf("instrumentation scope = %q, want %q", spans[0].InstrumentationScope.Name, want)
	}
}

// failedVerificationTestAgent returns a response carrying a completed,
// unfavourable verification verdict, standing in for a technique that ran a
// verifier and got "failed" (not "the run broke").
type failedVerificationTestAgent struct{}

func (a *failedVerificationTestAgent) Name() string           { return "verifier-agent" }
func (a *failedVerificationTestAgent) Capabilities() []string { return []string{} }
func (a *failedVerificationTestAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{AgentName: a.Name(), Capabilities: a.Capabilities()}
}

func (a *failedVerificationTestAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	// TracingMiddleware has no built-in verifier-verdict handling — a caller
	// that ran a Verifier is expected to set the attribute itself, per
	// docs/OTEL_CONVENTION.md's own Go example
	// (span.SetAttributes(attribute.String("agenkit.verifier.verdict", ...))).
	// This agent stands in for that caller: it runs "verification", gets
	// VerdictFailed, and must still return successfully — nil error — because
	// the check completing and disliking the answer is not the same claim as
	// the operation failing to complete.
	result := agenkit.NewVerificationResult(false, 0.0, "answer did not match expected output")
	if result.Verdict != agenkit.VerdictFailed {
		return nil, nil //nolint:nilnil // unreachable; guards the test's own premise
	}
	return &agenkit.Message{Role: "agent", Content: "checked, and it was wrong"}, nil
}

// TestAttributeNamespace_FailedVerificationIsNotAnErrorStatus asserts the
// doc's normative claim: a completed check that returns an unfavourable
// verdict leaves the span status Ok. Only a gap/timeout — something that did
// not run to completion — should set Error. TracingMiddleware itself only
// looks at whether Process returned an error, so this test's real job is
// proving that a verifier-backed agent which completes its check and returns
// a "failed" verdict as a *successful* Process call gets Ok, not Error. If a
// verifier-backed pattern instead mapped a failed verdict to a returned
// error, this test would catch it: TracingMiddleware would set span status
// Error, exactly the backwards behavior the doc warns about.
func TestAttributeNamespace_FailedVerificationIsNotAnErrorStatus(t *testing.T) {
	provider, exporter := setupTestTracing(t)
	defer func() { _ = provider.Shutdown(context.Background()) }()
	exporter.Reset()

	agent := &failedVerificationTestAgent{}
	traced := NewTracingMiddleware(agent, "")

	_, err := traced.Process(context.Background(), &agenkit.Message{Role: "user", Content: "2+2?"})
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}
	_ = provider.ForceFlush(context.Background())

	spans := exporter.GetSpans()
	if len(spans) != 1 {
		t.Fatalf("expected 1 span, got %d", len(spans))
	}
	if spans[0].Status.Code != codes.Ok {
		t.Errorf("span status = %v, want Ok: a completed verification that returned VerdictFailed must not set Error status", spans[0].Status.Code)
	}
}
