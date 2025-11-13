package observability

import (
	"context"
	"testing"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/sdk/metric"
	"go.opentelemetry.io/otel/sdk/metric/metricdata"
)

// setupTestMetrics sets up a test meter provider with in-memory reader
func setupTestMetrics(t *testing.T) (*metric.MeterProvider, *metric.ManualReader) {
	reader := metric.NewManualReader()
	provider := metric.NewMeterProvider(
		metric.WithReader(reader),
	)
	otel.SetMeterProvider(provider)
	return provider, reader
}

func TestMetricsMiddlewareCollectsRequestCount(t *testing.T) {
	provider, reader := setupTestMetrics(t)
	defer provider.Shutdown(context.Background())

	agent := &SimpleTestAgent{name: "agent1", response: "response"}
	metricsAgent, err := NewMetricsMiddleware(agent)
	if err != nil {
		t.Fatalf("NewMetricsMiddleware failed: %v", err)
	}

	message := &Message{Role: "user", Content: "test"}
	_, err = metricsAgent.Process(context.Background(), message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	// Collect metrics
	var rm metricdata.ResourceMetrics
	err = reader.Collect(context.Background(), &rm)
	if err != nil {
		t.Fatalf("Collect failed: %v", err)
	}

	// Find request counter
	var requestCounter *metricdata.Metrics
	for _, sm := range rm.ScopeMetrics {
		for i := range sm.Metrics {
			if sm.Metrics[i].Name == "agenkit.agent.requests" {
				requestCounter = &sm.Metrics[i]
				break
			}
		}
	}

	if requestCounter == nil {
		t.Fatal("Request counter metric not found")
	}

	// Check that it's a sum
	sum, ok := requestCounter.Data.(metricdata.Sum[int64])
	if !ok {
		t.Fatalf("Expected Sum[int64], got %T", requestCounter.Data)
	}

	if len(sum.DataPoints) == 0 {
		t.Fatal("No data points in request counter")
	}

	// Check attributes and value
	foundSuccess := false
	for _, dp := range sum.DataPoints {
		attrs := dp.Attributes.ToSlice()
		agentName := ""
		status := ""

		for _, attr := range attrs {
			if string(attr.Key) == "agent.name" {
				agentName = attr.Value.AsString()
			}
			if string(attr.Key) == "status" {
				status = attr.Value.AsString()
			}
		}

		if agentName == "agent1" && status == "success" {
			foundSuccess = true
			if dp.Value < 1 {
				t.Errorf("Expected value >= 1, got %d", dp.Value)
			}
		}
	}

	if !foundSuccess {
		t.Error("Did not find success data point for agent1")
	}
}

func TestMetricsMiddlewareRecordsLatency(t *testing.T) {
	provider, reader := setupTestMetrics(t)
	defer provider.Shutdown(context.Background())

	agent := &SimpleTestAgent{name: "agent1", response: "response"}
	metricsAgent, err := NewMetricsMiddleware(agent)
	if err != nil {
		t.Fatalf("NewMetricsMiddleware failed: %v", err)
	}

	message := &Message{Role: "user", Content: "test"}
	_, err = metricsAgent.Process(context.Background(), message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	// Collect metrics
	var rm metricdata.ResourceMetrics
	err = reader.Collect(context.Background(), &rm)
	if err != nil {
		t.Fatalf("Collect failed: %v", err)
	}

	// Find latency histogram
	var latencyHistogram *metricdata.Metrics
	for _, sm := range rm.ScopeMetrics {
		for i := range sm.Metrics {
			if sm.Metrics[i].Name == "agenkit.agent.latency" {
				latencyHistogram = &sm.Metrics[i]
				break
			}
		}
	}

	if latencyHistogram == nil {
		t.Fatal("Latency histogram metric not found")
	}

	// Check that it's a histogram
	hist, ok := latencyHistogram.Data.(metricdata.Histogram[float64])
	if !ok {
		t.Fatalf("Expected Histogram[float64], got %T", latencyHistogram.Data)
	}

	if len(hist.DataPoints) == 0 {
		t.Fatal("No data points in latency histogram")
	}

	// Check that latency was recorded
	dp := hist.DataPoints[0]
	if dp.Count < 1 {
		t.Errorf("Expected count >= 1, got %d", dp.Count)
	}
	if dp.Sum < 0 {
		t.Errorf("Expected sum >= 0, got %f", dp.Sum)
	}
}

func TestMetricsMiddlewareRecordsMessageSize(t *testing.T) {
	provider, reader := setupTestMetrics(t)
	defer provider.Shutdown(context.Background())

	agent := &SimpleTestAgent{name: "agent1", response: "response"}
	metricsAgent, err := NewMetricsMiddleware(agent)
	if err != nil {
		t.Fatalf("NewMetricsMiddleware failed: %v", err)
	}

	testContent := "test message content"
	message := &Message{Role: "user", Content: testContent}
	_, err = metricsAgent.Process(context.Background(), message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	// Collect metrics
	var rm metricdata.ResourceMetrics
	err = reader.Collect(context.Background(), &rm)
	if err != nil {
		t.Fatalf("Collect failed: %v", err)
	}

	// Find message size histogram
	var messageSizeHistogram *metricdata.Metrics
	for _, sm := range rm.ScopeMetrics {
		for i := range sm.Metrics {
			if sm.Metrics[i].Name == "agenkit.agent.message_size" {
				messageSizeHistogram = &sm.Metrics[i]
				break
			}
		}
	}

	if messageSizeHistogram == nil {
		t.Fatal("Message size histogram metric not found")
	}

	// Check that it's a histogram
	hist, ok := messageSizeHistogram.Data.(metricdata.Histogram[int64])
	if !ok {
		t.Fatalf("Expected Histogram[int64], got %T", messageSizeHistogram.Data)
	}

	if len(hist.DataPoints) == 0 {
		t.Fatal("No data points in message size histogram")
	}

	// Check that message size was recorded
	dp := hist.DataPoints[0]
	if dp.Count < 1 {
		t.Errorf("Expected count >= 1, got %d", dp.Count)
	}
	if dp.Sum != int64(len(testContent)) {
		t.Errorf("Expected sum=%d, got %d", len(testContent), dp.Sum)
	}
}

func TestMetricsMiddlewareRecordsErrors(t *testing.T) {
	provider, reader := setupTestMetrics(t)
	defer provider.Shutdown(context.Background())

	agent := &ErrorTestAgent{}
	metricsAgent, err := NewMetricsMiddleware(agent)
	if err != nil {
		t.Fatalf("NewMetricsMiddleware failed: %v", err)
	}

	message := &Message{Role: "user", Content: "test"}
	_, err = metricsAgent.Process(context.Background(), message)
	if err == nil {
		t.Fatal("Expected error, got nil")
	}

	// Collect metrics
	var rm metricdata.ResourceMetrics
	err = reader.Collect(context.Background(), &rm)
	if err != nil {
		t.Fatalf("Collect failed: %v", err)
	}

	// Find error counter
	var errorCounter *metricdata.Metrics
	for _, sm := range rm.ScopeMetrics {
		for i := range sm.Metrics {
			if sm.Metrics[i].Name == "agenkit.agent.errors" {
				errorCounter = &sm.Metrics[i]
				break
			}
		}
	}

	if errorCounter == nil {
		t.Fatal("Error counter metric not found")
	}

	// Check that it's a sum
	sum, ok := errorCounter.Data.(metricdata.Sum[int64])
	if !ok {
		t.Fatalf("Expected Sum[int64], got %T", errorCounter.Data)
	}

	if len(sum.DataPoints) == 0 {
		t.Fatal("No data points in error counter")
	}

	// Check attributes
	dp := sum.DataPoints[0]
	attrs := dp.Attributes.ToSlice()

	hasErrorStatus := false
	hasErrorType := false

	for _, attr := range attrs {
		if string(attr.Key) == "status" && attr.Value.AsString() == "error" {
			hasErrorStatus = true
		}
		if string(attr.Key) == "error.type" {
			hasErrorType = true
		}
	}

	if !hasErrorStatus {
		t.Error("Missing status=error attribute")
	}
	if !hasErrorType {
		t.Error("Missing error.type attribute")
	}

	if dp.Value < 1 {
		t.Errorf("Expected value >= 1, got %d", dp.Value)
	}
}

func TestMetricsMiddlewareSetsCorrectAttributes(t *testing.T) {
	provider, reader := setupTestMetrics(t)
	defer provider.Shutdown(context.Background())

	agent := &SimpleTestAgent{name: "test-agent", response: "response"}
	metricsAgent, err := NewMetricsMiddleware(agent)
	if err != nil {
		t.Fatalf("NewMetricsMiddleware failed: %v", err)
	}

	message := &Message{Role: "user", Content: "test"}
	_, err = metricsAgent.Process(context.Background(), message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	// Collect metrics
	var rm metricdata.ResourceMetrics
	err = reader.Collect(context.Background(), &rm)
	if err != nil {
		t.Fatalf("Collect failed: %v", err)
	}

	// Find request counter
	var requestCounter *metricdata.Metrics
	for _, sm := range rm.ScopeMetrics {
		for i := range sm.Metrics {
			if sm.Metrics[i].Name == "agenkit.agent.requests" {
				requestCounter = &sm.Metrics[i]
				break
			}
		}
	}

	if requestCounter == nil {
		t.Fatal("Request counter metric not found")
	}

	sum := requestCounter.Data.(metricdata.Sum[int64])

	// Check attributes
	foundCorrectAttrs := false
	for _, dp := range sum.DataPoints {
		attrs := dp.Attributes.ToSlice()
		agentName := ""
		messageRole := ""
		status := ""

		for _, attr := range attrs {
			switch string(attr.Key) {
			case "agent.name":
				agentName = attr.Value.AsString()
			case "message.role":
				messageRole = attr.Value.AsString()
			case "status":
				status = attr.Value.AsString()
			}
		}

		if agentName == "test-agent" && messageRole == "user" && status == "success" {
			foundCorrectAttrs = true
			break
		}
	}

	if !foundCorrectAttrs {
		t.Error("Did not find data point with correct attributes")
	}
}

func TestMetricsMiddlewareMultipleRequests(t *testing.T) {
	provider, reader := setupTestMetrics(t)
	defer provider.Shutdown(context.Background())

	agent := &SimpleTestAgent{name: "agent1", response: "response"}
	metricsAgent, err := NewMetricsMiddleware(agent)
	if err != nil {
		t.Fatalf("NewMetricsMiddleware failed: %v", err)
	}

	// Process multiple messages
	for i := 0; i < 5; i++ {
		message := &Message{Role: "user", Content: "test"}
		_, err = metricsAgent.Process(context.Background(), message)
		if err != nil {
			t.Fatalf("Process %d failed: %v", i, err)
		}
	}

	// Collect metrics
	var rm metricdata.ResourceMetrics
	err = reader.Collect(context.Background(), &rm)
	if err != nil {
		t.Fatalf("Collect failed: %v", err)
	}

	// Find request counter
	var requestCounter *metricdata.Metrics
	for _, sm := range rm.ScopeMetrics {
		for i := range sm.Metrics {
			if sm.Metrics[i].Name == "agenkit.agent.requests" {
				requestCounter = &sm.Metrics[i]
				break
			}
		}
	}

	if requestCounter == nil {
		t.Fatal("Request counter metric not found")
	}

	sum := requestCounter.Data.(metricdata.Sum[int64])

	// Check that count is at least 5
	totalCount := int64(0)
	for _, dp := range sum.DataPoints {
		attrs := dp.Attributes.ToSlice()
		agentName := ""
		status := ""

		for _, attr := range attrs {
			if string(attr.Key) == "agent.name" {
				agentName = attr.Value.AsString()
			}
			if string(attr.Key) == "status" {
				status = attr.Value.AsString()
			}
		}

		if agentName == "agent1" && status == "success" {
			totalCount += dp.Value
		}
	}

	if totalCount < 5 {
		t.Errorf("Expected count >= 5, got %d", totalCount)
	}
}

func TestMetricsMiddlewarePreservesAgentInterface(t *testing.T) {
	provider, _ := setupTestMetrics(t)
	defer provider.Shutdown(context.Background())

	agent := &SimpleTestAgent{name: "agent1", response: "response"}
	metricsAgent, err := NewMetricsMiddleware(agent)
	if err != nil {
		t.Fatalf("NewMetricsMiddleware failed: %v", err)
	}

	// Check that agent interface is preserved
	if metricsAgent.Name() != "agent1" {
		t.Errorf("Expected name 'agent1', got '%s'", metricsAgent.Name())
	}

	caps := metricsAgent.Capabilities()
	if len(caps) != 1 || caps[0] != "test" {
		t.Errorf("Expected capabilities ['test'], got %v", caps)
	}

	// Check that process works
	message := &Message{Role: "user", Content: "test"}
	response, err := metricsAgent.Process(context.Background(), message)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}
	if response.Content != "response" {
		t.Errorf("Expected content 'response', got '%s'", response.Content)
	}
}

func TestInitMetrics(t *testing.T) {
	// Note: InitMetrics creates a Prometheus exporter which starts an HTTP server
	// We just test that it initializes without error
	provider, err := InitMetrics("test-service", 0)
	if err != nil {
		t.Fatalf("InitMetrics failed: %v", err)
	}
	defer provider.Shutdown(context.Background())

	if provider == nil {
		t.Fatal("Expected provider, got nil")
	}

	// Verify meter works
	meter := otel.Meter("test")
	counter, err := meter.Int64Counter("test_counter")
	if err != nil {
		t.Fatalf("Failed to create counter: %v", err)
	}

	counter.Add(context.Background(), 1)
}
