// Package infrastructure provides production-grade infrastructure components.
//
// Load balancing for distributing requests across multiple agents with:
//   - Multiple strategies (round-robin, least-connections, weighted, random)
//   - Automatic health checking
//   - Failover support
//   - Real-time backend statistics
//   - Thread-safe for concurrent requests
package infrastructure

import (
	"context"
	"fmt"
	"math/rand"
	"sync"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// LoadBalancingStrategy defines the load balancing algorithm.
type LoadBalancingStrategy int

const (
	// RoundRobin distributes requests in rotation.
	RoundRobin LoadBalancingStrategy = iota
	// LeastConnections routes to agent with fewest active requests.
	LeastConnections
	// WeightedRoundRobin distributes based on agent weights.
	WeightedRoundRobin
	// Random selects a backend randomly.
	Random
)

// AgentBackend represents a backend agent with metadata.
type AgentBackend struct {
	Agent               agenkit.Agent
	Weight              int
	Healthy             bool
	ActiveConnections   int
	TotalRequests       int64
	TotalFailures       int64
	LastHealthCheck     time.Time
	consecutiveFailures int
}

// LoadBalancerConfig configures the load balancer.
type LoadBalancerConfig struct {
	Strategy            LoadBalancingStrategy
	HealthCheckInterval time.Duration
	HealthCheckTimeout  time.Duration
	FailureThreshold    int
	SuccessThreshold    int
	EnableFailover      bool
}

// DefaultLoadBalancerConfig returns default configuration.
func DefaultLoadBalancerConfig() LoadBalancerConfig {
	return LoadBalancerConfig{
		Strategy:            RoundRobin,
		HealthCheckInterval: 30 * time.Second,
		HealthCheckTimeout:  5 * time.Second,
		FailureThreshold:    3,
		SuccessThreshold:    2,
		EnableFailover:      true,
	}
}

// LoadBalancerMetrics tracks load balancer performance.
type LoadBalancerMetrics struct {
	TotalRequests        int64
	SuccessfulRequests   int64
	FailedRequests       int64
	FailoverAttempts     int64
	BackendHealthChanges map[string]int64
	mu                   sync.RWMutex
}

// LoadBalancer distributes requests across multiple agents.
type LoadBalancer struct {
	backends        []*AgentBackend
	config          LoadBalancerConfig
	metrics         *LoadBalancerMetrics
	currentIndex    int
	mu              sync.Mutex
	stopHealthCheck chan struct{}
	wg              sync.WaitGroup
}

// NewLoadBalancer creates a new load balancer.
func NewLoadBalancer(agents []agenkit.Agent, config LoadBalancerConfig, weights []int) (*LoadBalancer, error) {
	if len(agents) == 0 {
		return nil, fmt.Errorf("at least one agent required")
	}

	// Default weights to 1 if not provided
	if weights == nil {
		weights = make([]int, len(agents))
		for i := range weights {
			weights[i] = 1
		}
	}

	if len(weights) != len(agents) {
		return nil, fmt.Errorf("weights length (%d) must match agents length (%d)", len(weights), len(agents))
	}

	// Create backends
	backends := make([]*AgentBackend, len(agents))
	for i, agent := range agents {
		backends[i] = &AgentBackend{
			Agent:   agent,
			Weight:  weights[i],
			Healthy: true,
		}
	}

	lb := &LoadBalancer{
		backends: backends,
		config:   config,
		metrics: &LoadBalancerMetrics{
			BackendHealthChanges: make(map[string]int64),
		},
		stopHealthCheck: make(chan struct{}),
	}

	return lb, nil
}

// Name returns the load balancer name.
func (lb *LoadBalancer) Name() string {
	return fmt.Sprintf("LoadBalancer(%d backends)", len(lb.backends))
}

// Capabilities returns the union of all backend capabilities.
func (lb *LoadBalancer) Capabilities() []string {
	capsMap := make(map[string]bool)
	for _, backend := range lb.backends {
		for _, cap := range backend.Agent.Capabilities() {
			capsMap[cap] = true
		}
	}

	caps := make([]string, 0, len(capsMap))
	for cap := range capsMap {
		caps = append(caps, cap)
	}
	return caps
}

// Introspect returns introspection data about the load balancer.
func (lb *LoadBalancer) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    lb.Name(),
		Capabilities: lb.Capabilities(),
	}
}

// GetBackendStats returns statistics for all backends.
func (lb *LoadBalancer) GetBackendStats() []map[string]interface{} {
	lb.mu.Lock()
	defer lb.mu.Unlock()

	stats := make([]map[string]interface{}, len(lb.backends))
	for i, backend := range lb.backends {
		stats[i] = map[string]interface{}{
			"name":               backend.Agent.Name(),
			"healthy":            backend.Healthy,
			"weight":             backend.Weight,
			"active_connections": backend.ActiveConnections,
			"total_requests":     backend.TotalRequests,
			"total_failures":     backend.TotalFailures,
			"last_health_check":  backend.LastHealthCheck,
		}
	}
	return stats
}

// StartHealthChecks starts background health check task.
func (lb *LoadBalancer) StartHealthChecks(ctx context.Context) {
	lb.wg.Add(1)
	go lb.healthCheckLoop(ctx)
}

// StopHealthChecks stops background health check task.
func (lb *LoadBalancer) StopHealthChecks() {
	close(lb.stopHealthCheck)
	lb.wg.Wait()
}

func (lb *LoadBalancer) healthCheckLoop(ctx context.Context) {
	defer lb.wg.Done()

	ticker := time.NewTicker(lb.config.HealthCheckInterval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-lb.stopHealthCheck:
			return
		case <-ticker.C:
			lb.performHealthChecks(ctx)
		}
	}
}

func (lb *LoadBalancer) performHealthChecks(ctx context.Context) {
	for _, backend := range lb.backends {
		// Create timeout context for health check
		checkCtx, cancel := context.WithTimeout(ctx, lb.config.HealthCheckTimeout)

		// Simple health check: test if agent responds
		testMsg := &agenkit.Message{
			Role:    "system",
			Content: "health_check",
		}

		_, err := backend.Agent.Process(checkCtx, testMsg)
		cancel()

		backend.LastHealthCheck = time.Now()

		if err == nil {
			// Success
			backend.consecutiveFailures = 0
			if !backend.Healthy && backend.consecutiveFailures == 0 {
				backend.Healthy = true
				lb.trackHealthChange(backend.Agent.Name(), "recovered")
			}
		} else {
			// Failure
			backend.consecutiveFailures++
			backend.TotalFailures++

			if backend.Healthy && backend.consecutiveFailures >= lb.config.FailureThreshold {
				backend.Healthy = false
				lb.trackHealthChange(backend.Agent.Name(), "unhealthy")
			}
		}
	}
}

func (lb *LoadBalancer) trackHealthChange(agentName, changeType string) {
	key := fmt.Sprintf("%s:%s", agentName, changeType)
	lb.metrics.mu.Lock()
	lb.metrics.BackendHealthChanges[key]++
	lb.metrics.mu.Unlock()
}

func (lb *LoadBalancer) selectBackend() *AgentBackend {
	healthyBackends := make([]*AgentBackend, 0)
	for _, b := range lb.backends {
		if b.Healthy {
			healthyBackends = append(healthyBackends, b)
		}
	}

	if len(healthyBackends) == 0 {
		return nil
	}

	switch lb.config.Strategy {
	case RoundRobin:
		return lb.selectRoundRobin(healthyBackends)
	case LeastConnections:
		return lb.selectLeastConnections(healthyBackends)
	case WeightedRoundRobin:
		return lb.selectWeightedRoundRobin(healthyBackends)
	case Random:
		return healthyBackends[rand.Intn(len(healthyBackends))]
	default:
		return healthyBackends[0]
	}
}

func (lb *LoadBalancer) selectRoundRobin(backends []*AgentBackend) *AgentBackend {
	lb.mu.Lock()
	defer lb.mu.Unlock()

	// Find next healthy backend in rotation
	for i := 0; i < len(lb.backends); i++ {
		lb.currentIndex = (lb.currentIndex + 1) % len(lb.backends)
		if lb.backends[lb.currentIndex].Healthy {
			return lb.backends[lb.currentIndex]
		}
	}

	// Fallback to first healthy
	return backends[0]
}

func (lb *LoadBalancer) selectLeastConnections(backends []*AgentBackend) *AgentBackend {
	minConnections := backends[0].ActiveConnections
	selected := backends[0]

	for _, backend := range backends[1:] {
		if backend.ActiveConnections < minConnections {
			minConnections = backend.ActiveConnections
			selected = backend
		}
	}

	return selected
}

func (lb *LoadBalancer) selectWeightedRoundRobin(backends []*AgentBackend) *AgentBackend {
	lb.mu.Lock()
	defer lb.mu.Unlock()

	// Build weighted list
	weighted := make([]*AgentBackend, 0)
	for _, backend := range backends {
		for i := 0; i < backend.Weight; i++ {
			weighted = append(weighted, backend)
		}
	}

	if len(weighted) == 0 {
		return backends[0]
	}

	lb.currentIndex = (lb.currentIndex + 1) % len(weighted)
	return weighted[lb.currentIndex]
}

// Process processes a message using load-balanced backend.
func (lb *LoadBalancer) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	lb.metrics.mu.Lock()
	lb.metrics.TotalRequests++
	lb.metrics.mu.Unlock()

	attempted := make(map[string]bool)

	for {
		backend := lb.selectBackend()
		if backend == nil {
			return nil, fmt.Errorf("all backends unhealthy")
		}

		// Avoid retrying same backend
		if attempted[backend.Agent.Name()] {
			if !lb.config.EnableFailover || len(attempted) >= len(lb.backends) {
				return nil, fmt.Errorf("all backends attempted")
			}
			continue
		}

		attempted[backend.Agent.Name()] = true

		// Track request
		backend.ActiveConnections++
		backend.TotalRequests++

		response, err := backend.Agent.Process(ctx, message)

		backend.ActiveConnections--

		if err == nil {
			// Success
			lb.metrics.mu.Lock()
			lb.metrics.SuccessfulRequests++
			lb.metrics.mu.Unlock()
			return response, nil
		}

		// Failure
		backend.TotalFailures++
		lb.metrics.mu.Lock()
		lb.metrics.FailedRequests++
		lb.metrics.mu.Unlock()

		// Check if should mark unhealthy
		if backend.TotalFailures >= int64(lb.config.FailureThreshold) {
			backend.Healthy = false
			lb.trackHealthChange(backend.Agent.Name(), "unhealthy")
		}

		// Try failover if enabled
		if lb.config.EnableFailover && len(attempted) < len(lb.backends) {
			lb.metrics.mu.Lock()
			lb.metrics.FailoverAttempts++
			lb.metrics.mu.Unlock()
			continue
		}

		// No more failover
		return nil, fmt.Errorf("backend %s failed: %w", backend.Agent.Name(), err)
	}
}

// Metrics returns current metrics.
func (lb *LoadBalancer) Metrics() *LoadBalancerMetrics {
	return lb.metrics
}
