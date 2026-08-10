// Package observability provides OpenTelemetry integration for Agenkit Go.
//
// Includes distributed tracing, metrics export, and logging integration
// for monitoring agent interactions with cross-language support.
package observability

import (
	"context"
	"fmt"
	"os"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/codes"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
	"go.opentelemetry.io/otel/exporters/stdout/stdouttrace"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.41.0"
	"go.opentelemetry.io/otel/trace"
)

// otelExporterOTLPEndpointEnv and otelServiceNameEnv are the OTel spec-named
// environment variables consulted by InitTracing when the corresponding
// parameter is not supplied (empty string). An explicitly passed parameter
// always takes precedence over the environment — this matches the OTel SDK
// convention, where env vars are defaults, not overrides.
const (
	otelExporterOTLPEndpointEnv = "OTEL_EXPORTER_OTLP_ENDPOINT"
	otelServiceNameEnv          = "OTEL_SERVICE_NAME"
)

// TracerProvider global instance
var globalTracerProvider *sdktrace.TracerProvider

// resolveOTLPEndpoint returns otlpEndpoint if non-empty, otherwise the value
// of OTEL_EXPORTER_OTLP_ENDPOINT. An empty result means OTLP export stays
// disabled — neither the parameter nor the environment named an endpoint.
func resolveOTLPEndpoint(otlpEndpoint string) string {
	if otlpEndpoint != "" {
		return otlpEndpoint
	}
	return os.Getenv(otelExporterOTLPEndpointEnv)
}

// resolveServiceName returns serviceName if non-empty, otherwise the value of
// OTEL_SERVICE_NAME, otherwise the literal "agenkit".
func resolveServiceName(serviceName string) string {
	if serviceName != "" {
		return serviceName
	}
	if name := os.Getenv(otelServiceNameEnv); name != "" {
		return name
	}
	return "agenkit"
}

// InitTracing initializes OpenTelemetry tracing with the specified configuration.
//
// Parameters:
//   - serviceName: Name of the service for trace identification. If empty, falls
//     back to the OTEL_SERVICE_NAME environment variable, then "agenkit".
//   - otlpEndpoint: Optional OTLP collector endpoint (e.g., "localhost:4317"). If
//     empty, falls back to the OTEL_EXPORTER_OTLP_ENDPOINT environment variable.
//     OTLP export is disabled only if neither the parameter nor the environment
//     variable is set.
//   - consoleExport: If true, export spans to console for debugging
//   - sampleRate: Sampling rate (0.0 to 1.0). Default 1.0 (100%). For production, use lower rates (e.g., 0.01 = 1%)
//
// An explicitly passed serviceName/otlpEndpoint always takes precedence over
// the environment — this matches the OTel SDK convention of treating env vars
// as defaults, not overrides.
//
// Example:
//
//	// Development: 100% sampling with console export
//	tp, _ := InitTracing("my-service", "", true, 1.0)
//
//	// Production: 1% sampling with OTLP export
//	tp, _ := InitTracing("my-service", "localhost:4317", false, 0.01)
//
//	// Production: endpoint and service name from OTEL_EXPORTER_OTLP_ENDPOINT /
//	// OTEL_SERVICE_NAME, set by the deployment environment.
//	tp, _ := InitTracing("", "", false, 0.01)
func InitTracing(serviceName string, otlpEndpoint string, consoleExport bool, sampleRate float64) (*sdktrace.TracerProvider, error) {
	// Explicit parameters take precedence over the environment; the
	// environment is consulted only when the parameter is not supplied.
	serviceName = resolveServiceName(serviceName)
	otlpEndpoint = resolveOTLPEndpoint(otlpEndpoint)

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

	// Configure sampling
	// ParentBased: if parent span is sampled, always sample child spans
	// Otherwise, use TraceIDRatioBased for root spans
	sampler := sdktrace.ParentBased(sdktrace.TraceIDRatioBased(sampleRate))

	// Create tracer provider with sampler
	tp := sdktrace.NewTracerProvider(
		sdktrace.WithResource(res),
		sdktrace.WithSampler(sampler),
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

// Verify that TracingMiddleware implements Agent interface.
var _ agenkit.Agent = (*TracingMiddleware)(nil)

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

// Introspect returns the agent's introspection result.
func (t *TracingMiddleware) Introspect() *agenkit.IntrospectionResult {
	return t.agent.Introspect()
}

// genAIMetadataKeys are the well-known Message.Metadata keys (defined in the
// core agenkit package) that this middleware promotes onto explicit gen_ai.*/
// agenkit.* span attributes rather than the generic message.metadata.*
// promotion below. Excluded from that generic loop so they never appear twice
// under two different namespaces (message.metadata.gen_ai_system alongside
// gen_ai.system) — docs/OTEL_CONVENTION.md's attribute-namespace contract
// (#783) only grandfathers message.metadata.* for metadata that has no more
// specific home.
var genAIMetadataKeys = map[string]bool{
	agenkit.MetadataKeyGenAISystem:    true,
	agenkit.MetadataKeyRequestModel:   true,
	agenkit.MetadataKeyResponseModel:  true,
	"usage":                           true,
	agenkit.MetadataKeyCostMicroUnits: true,
	agenkit.MetadataKeyRetryCount:     true,
	agenkit.MetadataKeyVerifyRetries:  true,
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
		attribute.Int("message.content_length", len(message.ContentString())),
	)

	// Add metadata attributes
	if message.Metadata != nil {
		for key, value := range message.Metadata {
			if key == "trace_context" || genAIMetadataKeys[key] {
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

	// Promote GenAI attributes (#782) from whatever the wrapped agent's
	// response carries. The common case is an agent (e.g. ConversationalAgent)
	// that returns an adapter/llm response's Message essentially unchanged, so
	// the gen_ai_system/request_model/... keys the adapter set are present
	// here without this middleware knowing anything about adapter/llm.
	promoteGenAIAttributes(span, response.Metadata)

	// Inject trace context into response
	if response.Metadata == nil {
		response.Metadata = make(map[string]interface{})
	}
	response.Metadata = InjectTraceContext(ctx, response.Metadata)

	return response, nil
}

// promoteGenAIAttributes sets the GenAI semconv and agenkit.* span attributes
// from docs/OTEL_CONVENTION.md's GenAI attributes table (#782), reading the
// well-known Metadata keys an adapter/llm response (or a pattern that passes
// one through unchanged) carries.
//
// gen_ai.system/request.model/response.model/operation.name are only emitted
// when MetadataKeyGenAISystem is present — that key is the signal this
// response actually came from an LLM call, so a plain non-LLM agent's span
// does not get a fabricated set of GenAI attributes. The cost/retry counters
// are independent concepts and are emitted whenever present, regardless.
func promoteGenAIAttributes(span trace.Span, metadata map[string]interface{}) {
	if metadata == nil {
		return
	}

	if system, ok := metadata[agenkit.MetadataKeyGenAISystem].(string); ok {
		// docs/OTEL_CONVENTION.md's GenAI attributes table specifies the
		// literal key "gen_ai.system". The current semconv package (v1.41.0)
		// no longer exports a Go constant for it — the upstream spec
		// deprecated gen_ai.system in favour of gen_ai.provider.name after
		// this doc's contract was written — so it is spelled out here rather
		// than via a semconv.GenAI*Key that does not exist at this pin.
		span.SetAttributes(attribute.String("gen_ai.system", system))
		// gen_ai.operation.name is fixed at the semconv enum constant "chat":
		// every adapter/llm provider this promotes from is a chat-completion
		// call (Complete/Stream), never embeddings or another operation.
		span.SetAttributes(semconv.GenAIOperationNameChat)

		if reqModel, ok := metadata[agenkit.MetadataKeyRequestModel].(string); ok {
			span.SetAttributes(semconv.GenAIRequestModel(reqModel))
		}
		if respModel, ok := metadata[agenkit.MetadataKeyResponseModel].(string); ok {
			span.SetAttributes(semconv.GenAIResponseModel(respModel))
		}
	}

	if usage, ok := agenkit.UsageFromMessage(&agenkit.Message{Metadata: metadata}); ok {
		span.SetAttributes(semconv.GenAIUsageInputTokens(usage.PromptTokens))
		span.SetAttributes(semconv.GenAIUsageOutputTokens(usage.CompletionTokens))
		if usage.CacheReadTokens > 0 {
			span.SetAttributes(attribute.Int("agenkit.usage.cache_read_tokens", usage.CacheReadTokens))
		}
		if usage.CacheCreationTokens > 0 {
			span.SetAttributes(attribute.Int("agenkit.usage.cache_creation_tokens", usage.CacheCreationTokens))
		}
	}

	if cost, ok := toInt64(metadata[agenkit.MetadataKeyCostMicroUnits]); ok {
		span.SetAttributes(attribute.Int64("agenkit.cost.micro_units", cost))
	}
	if retries, ok := toInt64(metadata[agenkit.MetadataKeyRetryCount]); ok {
		span.SetAttributes(attribute.Int64("agenkit.retry.count", retries))
	}
	if retries, ok := toInt64(metadata[agenkit.MetadataKeyVerifyRetries]); ok {
		span.SetAttributes(attribute.Int64("agenkit.verify.retries", retries))
	}
}

// toInt64 coerces the numeric types a caller might reasonably store in
// Message.Metadata (int, int32, int64, float64) to int64. ok is false when v
// is nil or not a recognized numeric type, so an absent key is distinguishable
// from a genuine zero.
func toInt64(v interface{}) (int64, bool) {
	switch n := v.(type) {
	case int64:
		return n, true
	case int:
		return int64(n), true
	case int32:
		return int64(n), true
	case float64:
		return int64(n), true
	default:
		return 0, false
	}
}

// Shutdown gracefully shuts down the tracer provider.
func Shutdown(ctx context.Context) error {
	if globalTracerProvider != nil {
		return globalTracerProvider.Shutdown(ctx)
	}
	return nil
}
