package observability

import (
	"testing"

	semconv "go.opentelemetry.io/otel/semconv/v1.41.0"
)

// The semconv import path used by tracing.go and metrics.go was pinned to
// v1.17.0 while the SDK itself was v1.44.0 (#785). v1.17.0 predates the GenAI
// semantic conventions entirely, so #782 could not have used a single
// `semconv.GenAI*` constant — it would have had to hardcode the attribute key
// strings, and a free string that happens to equal "gen_ai.request.model" is
// indistinguishable from the constant right up until someone typos it.
//
// These tests exist so that a revert of the bump fails rather than silently
// reintroducing that state. Asserting on ServiceName alone would not do it:
// ServiceName resolves in both versions, so such a test passes either way.

// TestSemconvSchemaURLIsCurrent pins the convention revision. v1.17.0 reports
// ".../schemas/1.17.0", so this assertion is what actually detects a revert.
func TestSemconvSchemaURLIsCurrent(t *testing.T) {
	const want = "https://opentelemetry.io/schemas/1.41.0"
	if semconv.SchemaURL != want {
		t.Errorf("semconv.SchemaURL = %q, want %q — the import path in tracing.go/metrics.go moved", semconv.SchemaURL, want)
	}
}

// TestServiceNameStillResolves guards the one symbol tracing.go and metrics.go
// actually consume. semconv occasionally renames declarations across revisions
// (v1.41.0 removed DeploymentEnvironmentName, for instance), so the next bump
// should keep this honest.
func TestServiceNameStillResolves(t *testing.T) {
	kv := semconv.ServiceName("agenkit-test")
	if got := string(kv.Key); got != "service.name" {
		t.Errorf("ServiceName key = %q, want \"service.name\"", got)
	}
	if got := kv.Value.AsString(); got != "agenkit-test" {
		t.Errorf("ServiceName value = %q, want \"agenkit-test\"", got)
	}
}

// TestGenAIConventionsAreAvailable is the reason the bump was worth doing before
// #782. Each key below is one #782 will emit; none of them exist in v1.17.0.
func TestGenAIConventionsAreAvailable(t *testing.T) {
	cases := []struct {
		got  string
		want string
	}{
		{string(semconv.GenAIOperationNameKey), "gen_ai.operation.name"},
		{string(semconv.GenAIProviderNameKey), "gen_ai.provider.name"},
		{string(semconv.GenAIRequestModelKey), "gen_ai.request.model"},
		{string(semconv.GenAIResponseModelKey), "gen_ai.response.model"},
		{string(semconv.GenAIUsageInputTokensKey), "gen_ai.usage.input_tokens"},
		{string(semconv.GenAIUsageOutputTokensKey), "gen_ai.usage.output_tokens"},
		{string(semconv.GenAIToolNameKey), "gen_ai.tool.name"},
		{string(semconv.GenAIConversationIDKey), "gen_ai.conversation.id"},
	}

	for _, c := range cases {
		if c.got != c.want {
			t.Errorf("semconv GenAI key = %q, want %q", c.got, c.want)
		}
	}
}
