package observability

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"os"
	"runtime"
	"time"

	"go.opentelemetry.io/otel/trace"
)

// TraceContextHandler is a slog.Handler that adds trace context to log records.
type TraceContextHandler struct {
	handler slog.Handler
}

// NewTraceContextHandler creates a new handler that adds trace context.
func NewTraceContextHandler(handler slog.Handler) *TraceContextHandler {
	return &TraceContextHandler{
		handler: handler,
	}
}

// Enabled reports whether the handler handles records at the given level.
func (h *TraceContextHandler) Enabled(ctx context.Context, level slog.Level) bool {
	return h.handler.Enabled(ctx, level)
}

// Handle adds trace context and passes to underlying handler.
func (h *TraceContextHandler) Handle(ctx context.Context, record slog.Record) error {
	// Get current span
	span := trace.SpanFromContext(ctx)
	spanContext := span.SpanContext()

	if spanContext.IsValid() {
		// Add trace context as attributes
		record.AddAttrs(
			slog.String("trace_id", spanContext.TraceID().String()),
			slog.String("span_id", spanContext.SpanID().String()),
		)
	}

	return h.handler.Handle(ctx, record)
}

// WithAttrs returns a new handler with additional attributes.
func (h *TraceContextHandler) WithAttrs(attrs []slog.Attr) slog.Handler {
	return &TraceContextHandler{
		handler: h.handler.WithAttrs(attrs),
	}
}

// WithGroup returns a new handler with the given group.
func (h *TraceContextHandler) WithGroup(name string) slog.Handler {
	return &TraceContextHandler{
		handler: h.handler.WithGroup(name),
	}
}

// StructuredHandler is a JSON slog.Handler for structured logging.
type StructuredHandler struct {
	attrs  []slog.Attr
	groups []string
}

// NewStructuredHandler creates a new structured JSON handler.
func NewStructuredHandler() *StructuredHandler {
	return &StructuredHandler{
		attrs:  []slog.Attr{},
		groups: []string{},
	}
}

// Enabled always returns true for structured handler.
func (h *StructuredHandler) Enabled(_ context.Context, _ slog.Level) bool {
	return true
}

// Handle formats and outputs the log record as JSON.
func (h *StructuredHandler) Handle(ctx context.Context, record slog.Record) error {
	// Build log entry
	logEntry := make(map[string]interface{})

	// Add timestamp
	logEntry["timestamp"] = record.Time.Format(time.RFC3339)
	logEntry["level"] = record.Level.String()
	logEntry["message"] = record.Message

	// Add source location if available
	if record.PC != 0 {
		fs := runtime.CallersFrames([]uintptr{record.PC})
		f, _ := fs.Next()
		logEntry["source"] = map[string]interface{}{
			"function": f.Function,
			"file":     f.File,
			"line":     f.Line,
		}
	}

	// Add record attributes
	record.Attrs(func(attr slog.Attr) bool {
		logEntry[attr.Key] = attr.Value.Any()
		return true
	})

	// Add handler attributes
	for _, attr := range h.attrs {
		logEntry[attr.Key] = attr.Value.Any()
	}

	// Marshal to JSON
	data, err := json.Marshal(logEntry)
	if err != nil {
		return fmt.Errorf("failed to marshal log entry: %w", err)
	}

	// Write to stdout
	_, err = fmt.Fprintln(os.Stdout, string(data))
	return err
}

// WithAttrs returns a new handler with additional attributes.
func (h *StructuredHandler) WithAttrs(attrs []slog.Attr) slog.Handler {
	newAttrs := make([]slog.Attr, len(h.attrs)+len(attrs))
	copy(newAttrs, h.attrs)
	copy(newAttrs[len(h.attrs):], attrs)

	return &StructuredHandler{
		attrs:  newAttrs,
		groups: h.groups,
	}
}

// WithGroup returns a new handler with the given group.
func (h *StructuredHandler) WithGroup(name string) slog.Handler {
	newGroups := make([]string, len(h.groups)+1)
	copy(newGroups, h.groups)
	newGroups[len(h.groups)] = name

	return &StructuredHandler{
		attrs:  h.attrs,
		groups: newGroups,
	}
}

// ConfigureLogging configures structured logging with trace correlation.
func ConfigureLogging(level slog.Level, structured bool, includeTraceContext bool) {
	var handler slog.Handler

	if structured {
		handler = NewStructuredHandler()
	} else {
		handler = slog.NewTextHandler(os.Stdout, &slog.HandlerOptions{
			Level: level,
		})
	}

	if includeTraceContext {
		handler = NewTraceContextHandler(handler)
	}

	logger := slog.New(handler)
	slog.SetDefault(logger)
}

// GetLoggerWithTrace returns a logger that includes trace context.
func GetLoggerWithTrace() *slog.Logger {
	handler := NewTraceContextHandler(slog.Default().Handler())
	return slog.New(handler)
}
