package middleware

import (
	"context"
	"errors"
	"sync"
	"testing"
	"time"

	"github.com/agenkit/agenkit-go/agenkit"
)

// DelayAgent introduces a configurable delay before responding.
type DelayAgent struct {
	delay time.Duration
	fail  bool
}

func (d *DelayAgent) Name() string {
	return "delay-agent"
}

func (d *DelayAgent) Capabilities() []string {
	return []string{}
}

func (d *DelayAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	time.Sleep(d.delay)
	if d.fail {
		return nil, errors.New("intentional failure")
	}
	return agenkit.NewMessage("agent", "response"), nil
}

func TestMetricsBasicCounts(t *testing.T) {
	ctx := context.Background()
	agent := &DelayAgent{delay: 10 * time.Millisecond}
	metrics := NewMetricsDecorator(agent)

	// Initially all metrics should be zero
	m := metrics.GetMetrics().Snapshot()
	if m.TotalRequests != 0 {
		t.Errorf("Expected 0 total requests, got %d", m.TotalRequests)
	}

	// Make 5 successful requests
	for i := 0; i < 5; i++ {
		msg := agenkit.NewMessage("user", "test")
		_, err := metrics.Process(ctx, msg)
		if err != nil {
			t.Fatalf("Request %d failed: %v", i, err)
		}
	}

	// Check metrics
	m = metrics.GetMetrics().Snapshot()
	if m.TotalRequests != 5 {
		t.Errorf("Expected 5 total requests, got %d", m.TotalRequests)
	}
	if m.SuccessRequests != 5 {
		t.Errorf("Expected 5 successful requests, got %d", m.SuccessRequests)
	}
	if m.ErrorRequests != 0 {
		t.Errorf("Expected 0 error requests, got %d", m.ErrorRequests)
	}
}

func TestMetricsErrorCounting(t *testing.T) {
	ctx := context.Background()
	agent := &DelayAgent{delay: 1 * time.Millisecond, fail: true}
	metrics := NewMetricsDecorator(agent)

	// Make 3 requests that will fail
	for i := 0; i < 3; i++ {
		msg := agenkit.NewMessage("user", "test")
		_, err := metrics.Process(ctx, msg)
		if err == nil {
			t.Fatal("Expected error, got nil")
		}
	}

	// Check metrics
	m := metrics.GetMetrics().Snapshot()
	if m.TotalRequests != 3 {
		t.Errorf("Expected 3 total requests, got %d", m.TotalRequests)
	}
	if m.ErrorRequests != 3 {
		t.Errorf("Expected 3 error requests, got %d", m.ErrorRequests)
	}
	if m.SuccessRequests != 0 {
		t.Errorf("Expected 0 successful requests, got %d", m.SuccessRequests)
	}
}

func TestMetricsLatencyTracking(t *testing.T) {
	ctx := context.Background()
	delay := 50 * time.Millisecond
	agent := &DelayAgent{delay: delay}
	metrics := NewMetricsDecorator(agent)

	// Make 3 requests
	for i := 0; i < 3; i++ {
		msg := agenkit.NewMessage("user", "test")
		_, err := metrics.Process(ctx, msg)
		if err != nil {
			t.Fatalf("Request %d failed: %v", i, err)
		}
	}

	// Check latency metrics
	m := metrics.GetMetrics().Snapshot()

	// Average latency should be around the delay
	avgLatency := m.AverageLatency()
	if avgLatency < delay || avgLatency > delay+20*time.Millisecond {
		t.Errorf("Expected average latency around %v, got %v", delay, avgLatency)
	}

	// Min latency should be at least the delay
	if m.MinLatency < delay {
		t.Errorf("Expected min latency >= %v, got %v", delay, m.MinLatency)
	}

	// Max latency should be at least the delay
	if m.MaxLatency < delay {
		t.Errorf("Expected max latency >= %v, got %v", delay, m.MaxLatency)
	}

	// Total latency should be roughly 3x delay
	expectedTotal := delay * 3
	if m.TotalLatency < expectedTotal || m.TotalLatency > expectedTotal+60*time.Millisecond {
		t.Errorf("Expected total latency around %v, got %v", expectedTotal, m.TotalLatency)
	}
}

func TestMetricsErrorRate(t *testing.T) {
	ctx := context.Background()

	// Test 0% error rate
	agent1 := &DelayAgent{delay: 1 * time.Millisecond, fail: false}
	metrics1 := NewMetricsDecorator(agent1)

	for i := 0; i < 10; i++ {
		msg := agenkit.NewMessage("user", "test")
		metrics1.Process(ctx, msg)
	}

	errorRate := metrics1.GetMetrics().ErrorRate()
	if errorRate != 0.0 {
		t.Errorf("Expected 0%% error rate, got %.2f%%", errorRate*100)
	}

	// Test 100% error rate
	agent2 := &DelayAgent{delay: 1 * time.Millisecond, fail: true}
	metrics2 := NewMetricsDecorator(agent2)

	for i := 0; i < 10; i++ {
		msg := agenkit.NewMessage("user", "test")
		metrics2.Process(ctx, msg)
	}

	errorRate = metrics2.GetMetrics().ErrorRate()
	if errorRate != 1.0 {
		t.Errorf("Expected 100%% error rate, got %.2f%%", errorRate*100)
	}
}

func TestMetricsInFlightRequests(t *testing.T) {
	ctx := context.Background()
	agent := &DelayAgent{delay: 100 * time.Millisecond}
	metrics := NewMetricsDecorator(agent)

	var wg sync.WaitGroup
	numConcurrent := 5

	// Start concurrent requests
	for i := 0; i < numConcurrent; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			msg := agenkit.NewMessage("user", "test")
			metrics.Process(ctx, msg)
		}()
	}

	// Check in-flight count while requests are running
	time.Sleep(20 * time.Millisecond)
	m := metrics.GetMetrics().Snapshot()

	if m.InFlightRequests < 1 || m.InFlightRequests > int64(numConcurrent) {
		t.Errorf("Expected 1-%d in-flight requests, got %d", numConcurrent, m.InFlightRequests)
	}

	// Wait for completion
	wg.Wait()

	// In-flight should be back to 0
	m = metrics.GetMetrics().Snapshot()
	if m.InFlightRequests != 0 {
		t.Errorf("Expected 0 in-flight requests after completion, got %d", m.InFlightRequests)
	}

	// Total requests should be correct
	if m.TotalRequests != int64(numConcurrent) {
		t.Errorf("Expected %d total requests, got %d", numConcurrent, m.TotalRequests)
	}
}

func TestMetricsSnapshot(t *testing.T) {
	ctx := context.Background()
	agent := &DelayAgent{delay: 10 * time.Millisecond}
	metrics := NewMetricsDecorator(agent)

	// Make some requests
	for i := 0; i < 3; i++ {
		msg := agenkit.NewMessage("user", "test")
		metrics.Process(ctx, msg)
	}

	// Get snapshot
	snapshot := metrics.GetMetrics().Snapshot()

	// Make more requests
	for i := 0; i < 2; i++ {
		msg := agenkit.NewMessage("user", "test")
		metrics.Process(ctx, msg)
	}

	// Snapshot should still have old values
	if snapshot.TotalRequests != 3 {
		t.Errorf("Snapshot was modified: expected 3 total requests, got %d", snapshot.TotalRequests)
	}

	// Current metrics should have new values
	current := metrics.GetMetrics().Snapshot()
	if current.TotalRequests != 5 {
		t.Errorf("Current metrics incorrect: expected 5 total requests, got %d", current.TotalRequests)
	}
}

func TestMetricsReset(t *testing.T) {
	ctx := context.Background()
	agent := &DelayAgent{delay: 10 * time.Millisecond}
	metrics := NewMetricsDecorator(agent)

	// Make some requests
	for i := 0; i < 5; i++ {
		msg := agenkit.NewMessage("user", "test")
		metrics.Process(ctx, msg)
	}

	// Verify metrics are non-zero
	m := metrics.GetMetrics().Snapshot()
	if m.TotalRequests == 0 {
		t.Fatal("Expected non-zero metrics before reset")
	}

	// Reset metrics
	metrics.GetMetrics().Reset()

	// Verify all metrics are zero
	m = metrics.GetMetrics().Snapshot()
	if m.TotalRequests != 0 {
		t.Errorf("Expected 0 total requests after reset, got %d", m.TotalRequests)
	}
	if m.SuccessRequests != 0 {
		t.Errorf("Expected 0 success requests after reset, got %d", m.SuccessRequests)
	}
	if m.ErrorRequests != 0 {
		t.Errorf("Expected 0 error requests after reset, got %d", m.ErrorRequests)
	}
	if m.TotalLatency != 0 {
		t.Errorf("Expected 0 total latency after reset, got %v", m.TotalLatency)
	}
	if m.MinLatency != 0 {
		t.Errorf("Expected 0 min latency after reset, got %v", m.MinLatency)
	}
	if m.MaxLatency != 0 {
		t.Errorf("Expected 0 max latency after reset, got %v", m.MaxLatency)
	}
}

func TestMetricsAverageLatencyEdgeCases(t *testing.T) {
	metrics := &Metrics{}

	// Average latency should be 0 when no requests
	avg := metrics.AverageLatency()
	if avg != 0 {
		t.Errorf("Expected 0 average latency with no requests, got %v", avg)
	}

	// Add one request
	metrics.TotalRequests = 1
	metrics.TotalLatency = 100 * time.Millisecond

	avg = metrics.AverageLatency()
	if avg != 100*time.Millisecond {
		t.Errorf("Expected 100ms average latency, got %v", avg)
	}
}

func TestMetricsErrorRateEdgeCases(t *testing.T) {
	metrics := &Metrics{}

	// Error rate should be 0 when no requests
	rate := metrics.ErrorRate()
	if rate != 0.0 {
		t.Errorf("Expected 0.0 error rate with no requests, got %f", rate)
	}

	// 50% error rate
	metrics.TotalRequests = 10
	metrics.ErrorRequests = 5

	rate = metrics.ErrorRate()
	if rate != 0.5 {
		t.Errorf("Expected 0.5 error rate, got %f", rate)
	}
}

func TestMetricsConcurrentAccess(t *testing.T) {
	ctx := context.Background()
	agent := &DelayAgent{delay: 10 * time.Millisecond}
	metrics := NewMetricsDecorator(agent)

	var wg sync.WaitGroup
	numGoroutines := 10
	requestsPerGoroutine := 5

	// Concurrent requests
	for i := 0; i < numGoroutines; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for j := 0; j < requestsPerGoroutine; j++ {
				msg := agenkit.NewMessage("user", "test")
				metrics.Process(ctx, msg)
			}
		}()
	}

	// Concurrent snapshot reads
	for i := 0; i < 10; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for j := 0; j < 10; j++ {
				_ = metrics.GetMetrics().Snapshot()
				time.Sleep(1 * time.Millisecond)
			}
		}()
	}

	wg.Wait()

	// Verify total requests
	m := metrics.GetMetrics().Snapshot()
	expected := int64(numGoroutines * requestsPerGoroutine)
	if m.TotalRequests != expected {
		t.Errorf("Expected %d total requests, got %d", expected, m.TotalRequests)
	}
}

func TestMetricsDecoratorImplementsAgent(t *testing.T) {
	agent := &DelayAgent{delay: 1 * time.Millisecond}
	metrics := NewMetricsDecorator(agent)

	// Verify it implements Agent interface
	var _ agenkit.Agent = metrics

	// Test Name()
	if metrics.Name() != "delay-agent" {
		t.Errorf("Expected name 'delay-agent', got '%s'", metrics.Name())
	}

	// Test Capabilities()
	caps := metrics.Capabilities()
	if len(caps) != 0 {
		t.Errorf("Expected empty capabilities, got %v", caps)
	}
}
