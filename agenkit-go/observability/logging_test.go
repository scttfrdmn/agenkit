package observability

import (
	"bytes"
	"context"
	"encoding/json"
	"log/slog"
	"strings"
	"testing"
	"time"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/sdk/trace"
	"go.opentelemetry.io/otel/sdk/trace/tracetest"
)

func TestTraceContextHandlerAddsTraceContext(t *testing.T) {
	// Setup tracing
	exporter := tracetest.NewInMemoryExporter()
	provider := trace.NewTracerProvider(
		trace.WithSyncer(exporter),
	)
	otel.SetTracerProvider(provider)
	defer provider.Shutdown(context.Background())

	// Create a buffer to capture log output
	var buf bytes.Buffer

	// Create handler with trace context
	baseHandler := slog.NewTextHandler(&buf, &slog.HandlerOptions{
		Level: slog.LevelInfo,
	})
	handler := NewTraceContextHandler(baseHandler)

	logger := slog.New(handler)

	// Create a span and log within it
	tracer := otel.Tracer("test")
	ctx, span := tracer.Start(context.Background(), "test-span")
	spanContext := span.SpanContext()

	logger.InfoContext(ctx, "Test message with trace")
	span.End()

	// Check output
	output := buf.String()
	if !strings.Contains(output, "Test message with trace") {
		t.Errorf("Output missing message: %s", output)
	}

	// Check trace IDs are present
	traceID := spanContext.TraceID().String()
	spanID := spanContext.SpanID().String()

	if !strings.Contains(output, traceID) {
		t.Errorf("Output missing trace_id %s: %s", traceID, output)
	}
	if !strings.Contains(output, spanID) {
		t.Errorf("Output missing span_id %s: %s", spanID, output)
	}
}

func TestTraceContextHandlerWithoutSpan(t *testing.T) {
	// Create a buffer to capture log output
	var buf bytes.Buffer

	// Create handler with trace context
	baseHandler := slog.NewTextHandler(&buf, &slog.HandlerOptions{
		Level: slog.LevelInfo,
	})
	handler := NewTraceContextHandler(baseHandler)

	logger := slog.New(handler)

	// Log without span
	logger.InfoContext(context.Background(), "Test message without span")

	// Check output - should still work without span
	output := buf.String()
	if !strings.Contains(output, "Test message without span") {
		t.Errorf("Output missing message: %s", output)
	}
}

func TestStructuredHandlerProducesJSON(t *testing.T) {
	// Setup tracing
	exporter := tracetest.NewInMemoryExporter()
	provider := trace.NewTracerProvider(
		trace.WithSyncer(exporter),
	)
	otel.SetTracerProvider(provider)
	defer provider.Shutdown(context.Background())

	// Create structured handler with trace context
	structuredHandler := NewStructuredHandler()
	handler := NewTraceContextHandler(structuredHandler)

	logger := slog.New(handler)

	// Create a span and log within it
	tracer := otel.Tracer("test")
	ctx, span := tracer.Start(context.Background(), "test-span")

	// Since StructuredHandler writes to stdout which is hard to capture in tests,
	// we just verify the logger works without panicking
	logger.InfoContext(ctx, "Structured message",
		slog.String("key", "value"),
		slog.Int("count", 42),
	)
	span.End()

	// If we got here without panicking, the test passes
}

func TestStructuredHandlerHandlesRecord(t *testing.T) {
	// Test the Handle method directly
	handler := NewStructuredHandler()

	record := slog.NewRecord(
		time.Now(),
		slog.LevelInfo,
		"Test message",
		0,
	)
	record.AddAttrs(
		slog.String("key", "value"),
		slog.Int("count", 42),
	)

	err := handler.Handle(context.Background(), record)
	if err != nil {
		t.Errorf("Handle failed: %v", err)
	}
}

func TestConfigureLogging(t *testing.T) {
	// Test that ConfigureLogging doesn't panic
	ConfigureLogging(slog.LevelInfo, true, true)

	// Get the default logger and verify it works
	logger := slog.Default()
	logger.Info("Test message after configure")
}

func TestGetLoggerWithTrace(t *testing.T) {
	// Setup tracing
	exporter := tracetest.NewInMemoryExporter()
	provider := trace.NewTracerProvider(
		trace.WithSyncer(exporter),
	)
	otel.SetTracerProvider(provider)
	defer provider.Shutdown(context.Background())

	logger := GetLoggerWithTrace()
	if logger == nil {
		t.Fatal("GetLoggerWithTrace returned nil")
	}

	// Create a span and log within it
	tracer := otel.Tracer("test")
	ctx, span := tracer.Start(context.Background(), "test-span")

	logger.InfoContext(ctx, "Test message",
		slog.String("test", "value"),
	)
	span.End()
}

func TestTraceContextHandlerPreservesAttributes(t *testing.T) {
	var buf bytes.Buffer

	baseHandler := slog.NewJSONHandler(&buf, &slog.HandlerOptions{
		Level: slog.LevelInfo,
	})
	handler := NewTraceContextHandler(baseHandler)

	logger := slog.New(handler)

	logger.Info("Test message",
		slog.String("key1", "value1"),
		slog.Int("key2", 42),
		slog.Bool("key3", true),
	)

	// Parse JSON output
	var logData map[string]interface{}
	err := json.Unmarshal(buf.Bytes(), &logData)
	if err != nil {
		t.Fatalf("Failed to parse JSON: %v", err)
	}

	// Check attributes are present
	if logData["msg"] != "Test message" {
		t.Errorf("Expected msg='Test message', got '%v'", logData["msg"])
	}
	if logData["key1"] != "value1" {
		t.Errorf("Expected key1='value1', got '%v'", logData["key1"])
	}
	if logData["key2"] != float64(42) { // JSON numbers are float64
		t.Errorf("Expected key2=42, got '%v'", logData["key2"])
	}
	if logData["key3"] != true {
		t.Errorf("Expected key3=true, got '%v'", logData["key3"])
	}
}

func TestTraceContextHandlerWithGroup(t *testing.T) {
	var buf bytes.Buffer

	baseHandler := slog.NewJSONHandler(&buf, &slog.HandlerOptions{
		Level: slog.LevelInfo,
	})
	handler := NewTraceContextHandler(baseHandler)

	logger := slog.New(handler).WithGroup("request")

	logger.Info("Test message",
		slog.String("method", "GET"),
		slog.String("path", "/api/test"),
	)

	// Parse JSON output
	var logData map[string]interface{}
	err := json.Unmarshal(buf.Bytes(), &logData)
	if err != nil {
		t.Fatalf("Failed to parse JSON: %v", err)
	}

	// Check that group is present
	requestGroup, ok := logData["request"].(map[string]interface{})
	if !ok {
		t.Fatal("Expected 'request' group in output")
	}

	if requestGroup["method"] != "GET" {
		t.Errorf("Expected method='GET', got '%v'", requestGroup["method"])
	}
	if requestGroup["path"] != "/api/test" {
		t.Errorf("Expected path='/api/test', got '%v'", requestGroup["path"])
	}
}

func TestStructuredHandlerWithGroup(t *testing.T) {
	handler := NewStructuredHandler()

	// Test WithGroup
	groupedHandler := handler.WithGroup("test")
	if groupedHandler == nil {
		t.Fatal("WithGroup returned nil")
	}

	// Verify it's a StructuredHandler
	_, ok := groupedHandler.(*StructuredHandler)
	if !ok {
		t.Errorf("Expected *StructuredHandler, got %T", groupedHandler)
	}
}

func TestStructuredHandlerWithAttrs(t *testing.T) {
	handler := NewStructuredHandler()

	// Test WithAttrs
	attrs := []slog.Attr{
		slog.String("service", "test-service"),
		slog.String("version", "1.0.0"),
	}

	newHandler := handler.WithAttrs(attrs)
	if newHandler == nil {
		t.Fatal("WithAttrs returned nil")
	}

	// Verify it's a StructuredHandler
	_, ok := newHandler.(*StructuredHandler)
	if !ok {
		t.Errorf("Expected *StructuredHandler, got %T", newHandler)
	}
}

func TestTraceContextHandlerEnabled(t *testing.T) {
	baseHandler := slog.NewTextHandler(&bytes.Buffer{}, &slog.HandlerOptions{
		Level: slog.LevelWarn,
	})
	handler := NewTraceContextHandler(baseHandler)

	// Check that Enabled respects base handler's level
	if handler.Enabled(context.Background(), slog.LevelInfo) {
		t.Error("Expected Info level to be disabled when base is Warn")
	}

	if !handler.Enabled(context.Background(), slog.LevelWarn) {
		t.Error("Expected Warn level to be enabled")
	}

	if !handler.Enabled(context.Background(), slog.LevelError) {
		t.Error("Expected Error level to be enabled")
	}
}

func TestConfigureLoggingWithDifferentLevels(t *testing.T) {
	testCases := []struct {
		level      slog.Level
		structured bool
		traceCtx   bool
	}{
		{slog.LevelDebug, false, false},
		{slog.LevelInfo, true, false},
		{slog.LevelWarn, false, true},
		{slog.LevelError, true, true},
	}

	for _, tc := range testCases {
		t.Run("", func(t *testing.T) {
			// Test that each configuration works
			ConfigureLogging(tc.level, tc.structured, tc.traceCtx)

			logger := slog.Default()
			logger.Log(context.Background(), tc.level, "Test message")
		})
	}
}
