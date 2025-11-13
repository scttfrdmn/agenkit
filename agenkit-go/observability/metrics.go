package observability

import (
	"context"
	"fmt"
	"time"

	"github.com/agenkit/agenkit-go/agenkit"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/exporters/prometheus"
	"go.opentelemetry.io/otel/metric"
	sdkmetric "go.opentelemetry.io/otel/sdk/metric"
	"go.opentelemetry.io/otel/sdk/resource"
	semconv "go.opentelemetry.io/otel/semconv/v1.17.0"
)

// MeterProvider global instance
var globalMeterProvider *sdkmetric.MeterProvider

// InitMetrics initializes OpenTelemetry metrics with Prometheus export.
func InitMetrics(serviceName string, port int) (*sdkmetric.MeterProvider, error) {
	// Create resource
	res, err := resource.New(
		context.Background(),
		resource.WithAttributes(
			semconv.ServiceName(serviceName),
		),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create resource: %w", err)
	}

	// Create Prometheus exporter
	exporter, err := prometheus.New()
	if err != nil {
		return nil, fmt.Errorf("failed to create Prometheus exporter: %w", err)
	}

	// Create meter provider
	provider := sdkmetric.NewMeterProvider(
		sdkmetric.WithResource(res),
		sdkmetric.WithReader(exporter),
	)

	// Set as global provider
	otel.SetMeterProvider(provider)

	globalMeterProvider = provider
	return provider, nil
}

// GetMeter returns a meter from the current global meter provider.
func GetMeter(name string) metric.Meter {
	// Always get meter from current global provider
	// This allows tests to inject their own provider
	return otel.Meter(name)
}

// MetricsMiddleware wraps an agent with metrics collection.
type MetricsMiddleware struct {
	agent             agenkit.Agent
	meter             metric.Meter
	requestCounter    metric.Int64Counter
	errorCounter      metric.Int64Counter
	latencyHistogram  metric.Float64Histogram
	messageSizeHist   metric.Int64Histogram
}

// NewMetricsMiddleware creates a new metrics middleware.
func NewMetricsMiddleware(agent agenkit.Agent) (*MetricsMiddleware, error) {
	meter := GetMeter("agenkit.observability")

	// Create request counter
	requestCounter, err := meter.Int64Counter(
		"agenkit.agent.requests",
		metric.WithDescription("Total number of agent requests"),
		metric.WithUnit("1"),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create request counter: %w", err)
	}

	// Create error counter
	errorCounter, err := meter.Int64Counter(
		"agenkit.agent.errors",
		metric.WithDescription("Total number of agent errors"),
		metric.WithUnit("1"),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create error counter: %w", err)
	}

	// Create latency histogram
	latencyHistogram, err := meter.Float64Histogram(
		"agenkit.agent.latency",
		metric.WithDescription("Agent processing latency"),
		metric.WithUnit("ms"),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create latency histogram: %w", err)
	}

	// Create message size histogram
	messageSizeHist, err := meter.Int64Histogram(
		"agenkit.agent.message_size",
		metric.WithDescription("Message content size"),
		metric.WithUnit("bytes"),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create message size histogram: %w", err)
	}

	return &MetricsMiddleware{
		agent:            agent,
		meter:            meter,
		requestCounter:   requestCounter,
		errorCounter:     errorCounter,
		latencyHistogram: latencyHistogram,
		messageSizeHist:  messageSizeHist,
	}, nil
}

// Name returns the agent name.
func (m *MetricsMiddleware) Name() string {
	return m.agent.Name()
}

// Capabilities returns the agent capabilities.
func (m *MetricsMiddleware) Capabilities() []string {
	return m.agent.Capabilities()
}

// Process processes a message with metrics collection.
func (m *MetricsMiddleware) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	startTime := time.Now()

	// Common attributes
	attrs := []attribute.KeyValue{
		attribute.String("agent.name", m.agent.Name()),
		attribute.String("message.role", message.Role),
	}

	// Record message size
	messageSize := int64(len(message.Content))
	m.messageSizeHist.Record(ctx, messageSize, metric.WithAttributes(attrs...))

	// Process message
	response, err := m.agent.Process(ctx, message)

	// Calculate latency
	latencyMs := float64(time.Since(startTime).Microseconds()) / 1000.0

	if err != nil {
		// Record error
		errorAttrs := append(attrs,
			attribute.String("status", "error"),
			attribute.String("error.type", fmt.Sprintf("%T", err)),
		)
		m.requestCounter.Add(ctx, 1, metric.WithAttributes(errorAttrs...))
		m.errorCounter.Add(ctx, 1, metric.WithAttributes(errorAttrs...))
		m.latencyHistogram.Record(ctx, latencyMs, metric.WithAttributes(errorAttrs...))

		return nil, err
	}

	// Record success
	successAttrs := append(attrs, attribute.String("status", "success"))
	m.requestCounter.Add(ctx, 1, metric.WithAttributes(successAttrs...))
	m.latencyHistogram.Record(ctx, latencyMs, metric.WithAttributes(successAttrs...))

	return response, nil
}

// ShutdownMetrics gracefully shuts down the meter provider.
func ShutdownMetrics(ctx context.Context) error {
	if globalMeterProvider != nil {
		return globalMeterProvider.Shutdown(ctx)
	}
	return nil
}
