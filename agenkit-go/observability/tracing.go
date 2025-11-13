// Package observability provides OpenTelemetry integration for Agenkit Go.
//
// Includes distributed tracing, metrics export, and logging integration
// for monitoring agent interactions with cross-language support.
package observability

import (
	"context"
	"fmt"

	"github.com/agenkit/agenkit-go/agenkit"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/codes"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
	"go.opentelemetry.io/otel/exporters/stdout/stdouttrace"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.17.0"
	"go.opentelemetry.io/otel/trace"
)

// TracerProvider global instance
var globalTracerProvider *sdktrace.TracerProvider

// InitTracing initializes OpenTelemetry tracing with the specified configuration.
func InitTracing(serviceName string, otlpEndpoint string, consoleExport bool) (*sdktrace.TracerProvider, error) {
	// Create resource with service name
	res, err := resource.New(
		context.Background(),
		resource.WithAttributes(
			semconv.ServiceName(serviceName),
		),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create resource: %w", err)
	}

	// Create span processors
	var spanProcessors []sdktrace.SpanProcessor

	// Add OTLP exporter if endpoint provided
	if otlpEndpoint != "" {
		exporter, err := otlptracegrpc.New(
			context.Background(),
			otlptracegrpc.WithEndpoint(otlpEndpoint),
			otlptracegrpc.WithInsecure(), // For development; use TLS in production
		)
		if err != nil {
			return nil, fmt.Errorf("failed to create OTLP exporter: %w", err)
		}
		spanProcessors = append(spanProcessors, sdktrace.NewBatchSpanProcessor(exporter))
	}

	// Add console exporter if requested
	if consoleExport {
		exporter, err := stdouttrace.New(
			stdouttrace.WithPrettyPrint(),
		)
		if err != nil {
			return nil, fmt.Errorf("failed to create console exporter: %w", err)
		}
		spanProcessors = append(spanProcessors, sdktrace.NewBatchSpanProcessor(exporter))
	}

	// Create tracer provider
	tp := sdktrace.NewTracerProvider(
		sdktrace.WithResource(res),
	)

	// Add all span processors
	for _, processor := range spanProcessors {
		tp.RegisterSpanProcessor(processor)
	}

	// Set as global provider
	otel.SetTracerProvider(tp)

	// Set W3C Trace Context propagator for cross-language compatibility
	otel.SetTextMapPropagator(propagation.NewCompositeTextMapPropagator(
		propagation.TraceContext{},
		propagation.Baggage{},
	))

	globalTracerProvider = tp
	return tp, nil
}

// GetTracer returns a tracer from the current global tracer provider.
func GetTracer(name string) trace.Tracer {
	// Always get tracer from current global provider
	// This allows tests to inject their own provider
	return otel.Tracer(name)
}

// ExtractTraceContext extracts W3C Trace Context from metadata.
func ExtractTraceContext(ctx context.Context, metadata map[string]interface{}) context.Context {
	if metadata == nil {
		return ctx
	}

	traceCtx, ok := metadata["trace_context"]
	if !ok {
		return ctx
	}

	// Convert to carrier map
	carrier := make(propagation.MapCarrier)
	if traceMap, ok := traceCtx.(map[string]interface{}); ok {
		for k, v := range traceMap {
			if str, ok := v.(string); ok {
				carrier[k] = str
			}
		}
	}

	// Extract context
	propagator := otel.GetTextMapPropagator()
	return propagator.Extract(ctx, carrier)
}

// InjectTraceContext injects current W3C Trace Context into metadata.
func InjectTraceContext(ctx context.Context, metadata map[string]interface{}) map[string]interface{} {
	if metadata == nil {
		metadata = make(map[string]interface{})
	}

	// Create carrier
	carrier := make(propagation.MapCarrier)

	// Inject context
	propagator := otel.GetTextMapPropagator()
	propagator.Inject(ctx, carrier)

	// Convert to metadata
	if len(carrier) > 0 {
		traceCtx := make(map[string]interface{})
		for k, v := range carrier {
			traceCtx[k] = v
		}
		metadata["trace_context"] = traceCtx
	}

	return metadata
}

// TracingMiddleware wraps an agent with distributed tracing.
type TracingMiddleware struct {
	agent    agenkit.Agent
	spanName string
	tracer   trace.Tracer
}

// NewTracingMiddleware creates a new tracing middleware.
func NewTracingMiddleware(agent agenkit.Agent, spanName string) *TracingMiddleware {
	if spanName == "" {
		spanName = fmt.Sprintf("agent.%s.process", agent.Name())
	}

	return &TracingMiddleware{
		agent:    agent,
		spanName: spanName,
		tracer:   GetTracer("agenkit.observability"),
	}
}

// Name returns the agent name.
func (t *TracingMiddleware) Name() string {
	return t.agent.Name()
}

// Capabilities returns the agent capabilities.
func (t *TracingMiddleware) Capabilities() []string {
	return t.agent.Capabilities()
}

// Process processes a message with distributed tracing.
func (t *TracingMiddleware) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	// Extract parent context from message metadata
	if message.Metadata != nil {
		ctx = ExtractTraceContext(ctx, message.Metadata)
	}

	// Start span
	ctx, span := t.tracer.Start(ctx, t.spanName, trace.WithSpanKind(trace.SpanKindInternal))
	defer span.End()

	// Set span attributes
	span.SetAttributes(
		attribute.String("agent.name", t.agent.Name()),
		attribute.String("message.role", message.Role),
		attribute.Int("message.content_length", len(message.Content)),
	)

	// Add metadata attributes
	if message.Metadata != nil {
		for key, value := range message.Metadata {
			if key == "trace_context" {
				continue
			}

			// Only add simple types
			switch v := value.(type) {
			case string:
				span.SetAttributes(attribute.String(fmt.Sprintf("message.metadata.%s", key), v))
			case int:
				span.SetAttributes(attribute.Int(fmt.Sprintf("message.metadata.%s", key), v))
			case int64:
				span.SetAttributes(attribute.Int64(fmt.Sprintf("message.metadata.%s", key), v))
			case float64:
				span.SetAttributes(attribute.Float64(fmt.Sprintf("message.metadata.%s", key), v))
			case bool:
				span.SetAttributes(attribute.Bool(fmt.Sprintf("message.metadata.%s", key), v))
			}
		}
	}

	// Process message
	response, err := t.agent.Process(ctx, message)

	if err != nil {
		// Record error
		span.RecordError(err)
		span.SetStatus(codes.Error, err.Error())
		return nil, err
	}

	// Set success status
	span.SetStatus(codes.Ok, "")

	// Inject trace context into response
	if response.Metadata == nil {
		response.Metadata = make(map[string]interface{})
	}
	response.Metadata = InjectTraceContext(ctx, response.Metadata)

	return response, nil
}

// Shutdown gracefully shuts down the tracer provider.
func Shutdown(ctx context.Context) error {
	if globalTracerProvider != nil {
		return globalTracerProvider.Shutdown(ctx)
	}
	return nil
}
