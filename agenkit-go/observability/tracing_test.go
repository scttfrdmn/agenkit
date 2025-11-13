package observability

import (
	"context"
	"testing"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/codes"
	"go.opentelemetry.io/otel/propagation"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	"go.opentelemetry.io/otel/sdk/trace/tracetest"
)

// SimpleTestAgent implements Agent interface for testing
type SimpleTestAgent struct {
	name     string
	response string
}

func (a *SimpleTestAgent) Name() string {
	return a.name
}

func (a *SimpleTestAgent) Capabilities() []string {
	return []string{"test"}
}

func (a *SimpleTestAgent) Process(ctx context.Context, message *Message) (*Message, error) {
	return &Message{
		Role:    "agent",
		Content: a.response,
		Metadata: map[string]interface{}{
			"processed_by": a.name,
		},
	}, nil
}

// ErrorTestAgent implements Agent interface that returns errors
type ErrorTestAgent struct{}

func (a *ErrorTestAgent) Name() string {
	return "error-agent"
}

func (a *ErrorTestAgent) Capabilities() []string {
	return []string{}
}

func (a *ErrorTestAgent) Process(ctx context.Context, message *Message) (*Message, error) {
	return nil, &TestError{Msg: "test error"}
}

// TestError is a custom error type for testing
type TestError struct {
	Msg string
}

func (e *TestError) Error() string {
	return e.Msg
}

// setupTestTracing sets up a test tracer provider with in-memory exporter
func setupTestTracing(t *testing.T) (*sdktrace.TracerProvider, *tracetest.InMemoryExporter) {
	exporter := tracetest.NewInMemoryExporter()
	provider := sdktrace.NewTracerProvider(
		sdktrace.WithSpanProcessor(sdktrace.NewSimpleSpanProcessor(exporter)),
	)
	otel.SetTracerProvider(provider)

	// Set W3C Trace Context propagator for context propagation
	otel.SetTextMapPropagator(propagation.NewCompositeTextMapPropagator(
		propagation.TraceContext{},
		propagation.Baggage{},
	))

	return provider, exporter
}

func TestTracingMiddlewareCreatesSpan(t *testing.T) {
	provider, exporter := setupTestTracing(t)
	defer provider.Shutdown(context.Background())

	// Reset exporter to ensure clean state
	exporter.Reset()

	agent := &SimpleTestAgent{name: "agent1", response: "response"}
	traced := NewTracingMiddleware(agent, "")

	message := &Message{Role: "user", Content: "test message"}
	_, err := traced.Process(context.Background(), message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	// Force flush to get spans
	provider.ForceFlush(context.Background())

	spans := exporter.GetSpans()
	if len(spans) != 1 {
		t.Fatalf("Expected 1 span, got %d", len(spans))
	}

	span := spans[0]
	if span.Name != "agent.agent1.process" {
		t.Errorf("Expected span name 'agent.agent1.process', got '%s'", span.Name)
	}
	if span.Status.Code != codes.Ok {
		t.Errorf("Expected status OK, got %v", span.Status.Code)
	}
}

func TestTracingMiddlewareSetsAttributes(t *testing.T) {
	provider, exporter := setupTestTracing(t)
	defer provider.Shutdown(context.Background())

	agent := &SimpleTestAgent{name: "agent1", response: "response"}
	traced := NewTracingMiddleware(agent, "")

	message := &Message{
		Role:    "user",
		Content: "test message",
		Metadata: map[string]interface{}{
			"key": "value",
		},
	}
	_, err := traced.Process(context.Background(), message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	provider.ForceFlush(context.Background())

	spans := exporter.GetSpans()
	if len(spans) != 1 {
		t.Fatalf("Expected 1 span, got %d", len(spans))
	}

	span := spans[0]
	attrs := span.Attributes

	// Check attributes
	hasAgentName := false
	hasMessageRole := false
	hasContentLength := false
	hasMetadataKey := false

	for _, attr := range attrs {
		switch string(attr.Key) {
		case "agent.name":
			if attr.Value.AsString() != "agent1" {
				t.Errorf("Expected agent.name='agent1', got '%s'", attr.Value.AsString())
			}
			hasAgentName = true
		case "message.role":
			if attr.Value.AsString() != "user" {
				t.Errorf("Expected message.role='user', got '%s'", attr.Value.AsString())
			}
			hasMessageRole = true
		case "message.content_length":
			if attr.Value.AsInt64() != int64(len("test message")) {
				t.Errorf("Expected content_length=%d, got %d", len("test message"), attr.Value.AsInt64())
			}
			hasContentLength = true
		case "message.metadata.key":
			if attr.Value.AsString() != "value" {
				t.Errorf("Expected message.metadata.key='value', got '%s'", attr.Value.AsString())
			}
			hasMetadataKey = true
		}
	}

	if !hasAgentName {
		t.Error("Missing agent.name attribute")
	}
	if !hasMessageRole {
		t.Error("Missing message.role attribute")
	}
	if !hasContentLength {
		t.Error("Missing message.content_length attribute")
	}
	if !hasMetadataKey {
		t.Error("Missing message.metadata.key attribute")
	}
}

func TestTracingMiddlewareInjectsTraceContext(t *testing.T) {
	provider, exporter := setupTestTracing(t)
	defer provider.Shutdown(context.Background())
	_ = exporter // Unused but needed for setup

	agent := &SimpleTestAgent{name: "agent1", response: "response"}
	traced := NewTracingMiddleware(agent, "")

	message := &Message{Role: "user", Content: "test"}
	response, err := traced.Process(context.Background(), message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	provider.ForceFlush(context.Background())

	// Check that trace context was injected
	if response.Metadata == nil {
		t.Fatal("Response metadata is nil")
	}

	traceCtx, ok := response.Metadata["trace_context"]
	if !ok {
		t.Fatal("trace_context not found in response metadata")
	}

	traceCtxMap, ok := traceCtx.(map[string]interface{})
	if !ok {
		t.Fatal("trace_context is not a map")
	}

	if _, ok := traceCtxMap["traceparent"]; !ok {
		t.Error("traceparent not found in trace_context")
	}
}

func TestTracingMiddlewarePropagatesContext(t *testing.T) {
	provider, exporter := setupTestTracing(t)
	defer provider.Shutdown(context.Background())

	agent1 := &SimpleTestAgent{name: "agent1", response: "response1"}
	agent2 := &SimpleTestAgent{name: "agent2", response: "response2"}

	traced1 := NewTracingMiddleware(agent1, "")
	traced2 := NewTracingMiddleware(agent2, "")

	// Process through agent1
	message := &Message{Role: "user", Content: "test"}
	response1, err := traced1.Process(context.Background(), message)
	if err != nil {
		t.Fatalf("Process 1 failed: %v", err)
	}

	// Process through agent2 with response1 (which has trace context)
	response2, err := traced2.Process(context.Background(), response1)
	if err != nil {
		t.Fatalf("Process 2 failed: %v", err)
	}

	provider.ForceFlush(context.Background())

	spans := exporter.GetSpans()
	if len(spans) != 2 {
		t.Fatalf("Expected 2 spans, got %d", len(spans))
	}

	// Both spans should have the same trace ID
	trace1 := spans[0].SpanContext.TraceID()
	trace2 := spans[1].SpanContext.TraceID()

	if trace1 != trace2 {
		t.Errorf("Trace IDs don't match: %s != %s", trace1, trace2)
	}

	// Verify response2 also has trace context
	if response2.Metadata == nil {
		t.Fatal("Response2 metadata is nil")
	}
	if _, ok := response2.Metadata["trace_context"]; !ok {
		t.Error("trace_context not found in response2 metadata")
	}
}

func TestTracingMiddlewareRecordsErrors(t *testing.T) {
	provider, exporter := setupTestTracing(t)
	defer provider.Shutdown(context.Background())

	agent := &ErrorTestAgent{}
	traced := NewTracingMiddleware(agent, "")

	message := &Message{Role: "user", Content: "test"}
	_, err := traced.Process(context.Background(), message)
	if err == nil {
		t.Fatal("Expected error, got nil")
	}

	provider.ForceFlush(context.Background())

	spans := exporter.GetSpans()
	if len(spans) != 1 {
		t.Fatalf("Expected 1 span, got %d", len(spans))
	}

	span := spans[0]
	if span.Status.Code != codes.Error {
		t.Errorf("Expected status Error, got %v", span.Status.Code)
	}
	if span.Status.Description != "test error" {
		t.Errorf("Expected description 'test error', got '%s'", span.Status.Description)
	}

	// Check that error was recorded as an event
	if len(span.Events) == 0 {
		t.Fatal("Expected at least one event (exception)")
	}

	hasException := false
	for _, event := range span.Events {
		if event.Name == "exception" {
			hasException = true
			break
		}
	}
	if !hasException {
		t.Error("No exception event found in span")
	}
}

func TestTracingMiddlewareCustomSpanName(t *testing.T) {
	provider, exporter := setupTestTracing(t)
	defer provider.Shutdown(context.Background())

	agent := &SimpleTestAgent{name: "agent1", response: "response"}
	traced := NewTracingMiddleware(agent, "custom.operation")

	message := &Message{Role: "user", Content: "test"}
	_, err := traced.Process(context.Background(), message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	provider.ForceFlush(context.Background())

	spans := exporter.GetSpans()
	if len(spans) != 1 {
		t.Fatalf("Expected 1 span, got %d", len(spans))
	}

	if spans[0].Name != "custom.operation" {
		t.Errorf("Expected span name 'custom.operation', got '%s'", spans[0].Name)
	}
}

func TestTracingMiddlewarePreservesAgentInterface(t *testing.T) {
	provider, exporter := setupTestTracing(t)
	defer provider.Shutdown(context.Background())
	_ = exporter // Unused but needed for setup

	agent := &SimpleTestAgent{name: "agent1", response: "response"}
	traced := NewTracingMiddleware(agent, "")

	// Check that agent interface is preserved
	if traced.Name() != "agent1" {
		t.Errorf("Expected name 'agent1', got '%s'", traced.Name())
	}

	caps := traced.Capabilities()
	if len(caps) != 1 || caps[0] != "test" {
		t.Errorf("Expected capabilities ['test'], got %v", caps)
	}

	// Check that process works
	message := &Message{Role: "user", Content: "test"}
	response, err := traced.Process(context.Background(), message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}
	if response.Content != "response" {
		t.Errorf("Expected content 'response', got '%s'", response.Content)
	}
}

func TestInitTracingWithConsoleExport(t *testing.T) {
	provider, err := InitTracing("test-service", "", true)
	if err != nil {
		t.Fatalf("InitTracing failed: %v", err)
	}
	defer provider.Shutdown(context.Background())

	if provider == nil {
		t.Fatal("Expected provider, got nil")
	}

	// Verify tracer works
	tracer := otel.Tracer("test")
	ctx, span := tracer.Start(context.Background(), "test-span")
	defer span.End()

	if !span.IsRecording() {
		t.Error("Span is not recording")
	}

	_ = ctx // Use ctx to avoid unused variable error
}
