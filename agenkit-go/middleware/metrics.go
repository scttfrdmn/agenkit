package middleware

import (
	"context"
	"sync"
	"time"

	"github.com/agenkit/agenkit-go/agenkit"
)

// Metrics holds observability metrics for an agent.
type Metrics struct {
	mu sync.RWMutex

	// Request metrics
	TotalRequests   int64
	SuccessRequests int64
	ErrorRequests   int64

	// Latency metrics
	TotalLatency time.Duration
	MinLatency   time.Duration
	MaxLatency   time.Duration

	// Current state
	InFlightRequests int64
}

// AverageLatency returns the average request latency.
func (m *Metrics) AverageLatency() time.Duration {
	m.mu.RLock()
	defer m.mu.RUnlock()

	if m.TotalRequests == 0 {
		return 0
	}
	return m.TotalLatency / time.Duration(m.TotalRequests)
}

// ErrorRate returns the error rate as a percentage (0.0 to 1.0).
func (m *Metrics) ErrorRate() float64 {
	m.mu.RLock()
	defer m.mu.RUnlock()

	if m.TotalRequests == 0 {
		return 0.0
	}
	return float64(m.ErrorRequests) / float64(m.TotalRequests)
}

// Snapshot returns a copy of the current metrics.
func (m *Metrics) Snapshot() Metrics {
	m.mu.RLock()
	defer m.mu.RUnlock()

	return Metrics{
		TotalRequests:    m.TotalRequests,
		SuccessRequests:  m.SuccessRequests,
		ErrorRequests:    m.ErrorRequests,
		TotalLatency:     m.TotalLatency,
		MinLatency:       m.MinLatency,
		MaxLatency:       m.MaxLatency,
		InFlightRequests: m.InFlightRequests,
	}
}

// Reset clears all metrics.
func (m *Metrics) Reset() {
	m.mu.Lock()
	defer m.mu.Unlock()

	m.TotalRequests = 0
	m.SuccessRequests = 0
	m.ErrorRequests = 0
	m.TotalLatency = 0
	m.MinLatency = 0
	m.MaxLatency = 0
	m.InFlightRequests = 0
}

// MetricsDecorator wraps an agent with metrics collection.
type MetricsDecorator struct {
	agent   agenkit.Agent
	metrics *Metrics
}

// Verify that MetricsDecorator implements Agent interface.
var _ agenkit.Agent = (*MetricsDecorator)(nil)

// NewMetricsDecorator creates a new metrics decorator.
func NewMetricsDecorator(agent agenkit.Agent) *MetricsDecorator {
	return &MetricsDecorator{
		agent:   agent,
		metrics: &Metrics{},
	}
}

// Name returns the name of the underlying agent.
func (m *MetricsDecorator) Name() string {
	return m.agent.Name()
}

// Capabilities returns the capabilities of the underlying agent.
func (m *MetricsDecorator) Capabilities() []string {
	return m.agent.Capabilities()
}

// GetMetrics returns the current metrics.
func (m *MetricsDecorator) GetMetrics() *Metrics {
	return m.metrics
}

// Process implements the Agent interface with metrics collection.
func (m *MetricsDecorator) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	// Record in-flight request
	m.metrics.mu.Lock()
	m.metrics.InFlightRequests++
	m.metrics.mu.Unlock()

	defer func() {
		m.metrics.mu.Lock()
		m.metrics.InFlightRequests--
		m.metrics.mu.Unlock()
	}()

	// Record start time
	start := time.Now()

	// Call underlying agent
	response, err := m.agent.Process(ctx, message)

	// Record latency
	latency := time.Since(start)

	// Update metrics
	m.metrics.mu.Lock()
	defer m.metrics.mu.Unlock()

	m.metrics.TotalRequests++
	m.metrics.TotalLatency += latency

	// Update min/max latency
	if m.metrics.MinLatency == 0 || latency < m.metrics.MinLatency {
		m.metrics.MinLatency = latency
	}
	if latency > m.metrics.MaxLatency {
		m.metrics.MaxLatency = latency
	}

	// Update success/error counts
	if err != nil {
		m.metrics.ErrorRequests++
	} else {
		m.metrics.SuccessRequests++
	}

	return response, err
}
