// Production-ready agent with load balancing, health checks, and enhanced retry.
//
// This example demonstrates how to build a production agent system with:
// - Load balancing across multiple backend agents
// - Health monitoring with Kubernetes-style probes
// - Enhanced retry with jitter and backpressure detection
// - Prometheus metrics export
//
// Perfect for 30-hour autonomous agent deployments.
package main

import (
	"context"
	"fmt"
	"log"
	"math/rand"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/infrastructure"
)

// SimulatedAgent implements a test agent with configurable failure rate.
type SimulatedAgent struct {
	agentName    string
	failureRate  float64
	requestCount int
}

func NewSimulatedAgent(name string, failureRate float64) *SimulatedAgent {
	return &SimulatedAgent{
		agentName:   name,
		failureRate: failureRate,
	}
}

func (a *SimulatedAgent) Name() string {
	return a.agentName
}

func (a *SimulatedAgent) Capabilities() []string {
	return []string{"text_generation", "reasoning"}
}

// Introspect satisfies agenkit.Agent. Every agent-shaped type must implement it:
// omitting it is what let 22 types silently stop satisfying the interface in #847.
func (a *SimulatedAgent) Introspect() *agenkit.IntrospectionResult {
	result, err := agenkit.NewIntrospectionResult(
		a.agentName,
		a.Capabilities(),
		nil,
		map[string]interface{}{
			"failure_rate":  a.failureRate,
			"request_count": a.requestCount,
		},
		nil,
	)
	if err != nil {
		return nil
	}
	return result
}

func (a *SimulatedAgent) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
	a.requestCount++

	// Simulate processing time, but honour cancellation while doing so.
	select {
	case <-time.After(100 * time.Millisecond):
	case <-ctx.Done():
		return nil, ctx.Err()
	}

	// Simulate occasional failures
	if rand.Float64() < a.failureRate { //nolint:gosec // simulation, not security
		return nil, fmt.Errorf("%s: simulated transient error", a.agentName)
	}

	return &agenkit.Message{
		Role:    "agent",
		Content: fmt.Sprintf("%s processed: %s", a.agentName, msg.ContentString()),
		Metadata: map[string]interface{}{
			"agent":         a.agentName,
			"request_count": a.requestCount,
			"timestamp":     time.Now().Format(time.RFC3339),
		},
	}, nil
}

func main() {
	log.Println("Starting production agent system...")

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// 1. Create backend agents with varying failure rates
	backend1 := NewSimulatedAgent("agent-1", 0.1)
	backend2 := NewSimulatedAgent("agent-2", 0.05)
	backend3 := NewSimulatedAgent("agent-3", 0.15)

	// 2. Wrap each backend with enhanced retry
	retryConfig := infrastructure.EnhancedRetryConfig{
		MaxRetries:            3,
		InitialRetryDelay:     100 * time.Millisecond,
		MaxRetryDelay:         5 * time.Second,
		RetryMultiplier:       2.0,
		JitterType:            infrastructure.FullJitter,
		EnableBackpressure:    true,
		BackpressureThreshold: 0.3,
		BackpressureWindow:    10,
		ErrorStrategies:       make(map[infrastructure.ErrorClass]infrastructure.ErrorStrategy),
	}

	// Add default error strategies
	retryConfig.ErrorStrategies[infrastructure.Transient] = infrastructure.ErrorStrategy{
		ErrorClass:        infrastructure.Transient,
		MaxRetries:        5,
		InitialRetryDelay: 100 * time.Millisecond,
		MaxRetryDelay:     5 * time.Second,
		RetryMultiplier:   2.0,
		ShouldRetry:       true,
	}

	retryBackend1 := infrastructure.NewEnhancedRetryDecorator(backend1, retryConfig)
	retryBackend2 := infrastructure.NewEnhancedRetryDecorator(backend2, retryConfig)
	retryBackend3 := infrastructure.NewEnhancedRetryDecorator(backend3, retryConfig)

	// 3. Create load balancer with health checking
	lbConfig := infrastructure.LoadBalancerConfig{
		Strategy:            infrastructure.LeastConnections,
		HealthCheckInterval: 5 * time.Second,
		HealthCheckTimeout:  2 * time.Second,
		FailureThreshold:    3,
		SuccessThreshold:    2,
		EnableFailover:      true,
	}

	// nil weights means "weight 1 each"; pass a []int to bias WeightedRoundRobin.
	loadBalancer, err := infrastructure.NewLoadBalancer(
		[]agenkit.Agent{retryBackend1, retryBackend2, retryBackend3},
		lbConfig,
		nil,
	)
	if err != nil {
		log.Fatalf("failed to create load balancer: %v", err)
	}

	loadBalancer.StartHealthChecks(ctx)
	defer loadBalancer.StopHealthChecks()

	// 4. Set up health checker for the load balancer
	healthConfig := infrastructure.HealthCheckConfig{
		LivenessEnabled:           true,
		LivenessInterval:          10 * time.Second,
		LivenessTimeout:           5 * time.Second,
		LivenessFailureThreshold:  3,
		ReadinessEnabled:          true,
		ReadinessInterval:         5 * time.Second,
		ReadinessTimeout:          3 * time.Second,
		ReadinessFailureThreshold: 2,
		StartupEnabled:            true,
		StartupTimeout:            30 * time.Second,
		StartupFailureThreshold:   5,
	}

	healthChecker := infrastructure.NewHealthChecker(loadBalancer, healthConfig)
	healthChecker.Start(ctx)

	// Wait for startup to complete
	log.Println("Waiting for startup checks...")
	time.Sleep(2 * time.Second)

	if !healthChecker.IsHealthy() {
		log.Fatal("System failed startup checks")
	}

	log.Println("System is healthy and ready!")

	// 5. Process requests through the production system
	successful := 0
	failed := 0

	for i := 0; i < 20; i++ {
		msg := &agenkit.Message{
			Role:    "user",
			Content: fmt.Sprintf("Request %d", i),
		}

		response, err := loadBalancer.Process(ctx, msg)
		if err != nil {
			log.Printf("Request %d: FAILED - %v", i, err)
			failed++
		} else {
			log.Printf("Request %d: SUCCESS - %s", i, response.ContentString())
			successful++
		}

		// Brief pause between requests
		time.Sleep(200 * time.Millisecond)
	}

	// 6. Export metrics
	log.Println("\n" + "============================================================")
	log.Println("FINAL METRICS")
	log.Println("============================================================")
	log.Printf("Requests attempted here: %d successful, %d failed", successful, failed)

	// Load balancer metrics
	lbMetrics := loadBalancer.Metrics()
	log.Printf("\nLoad Balancer:")
	log.Printf("  Total requests: %d", lbMetrics.TotalRequests)
	log.Printf("  Successful: %d", lbMetrics.SuccessfulRequests)
	log.Printf("  Failed: %d", lbMetrics.FailedRequests)
	log.Printf("  Failover attempts: %d", lbMetrics.FailoverAttempts)
	if lbMetrics.TotalRequests > 0 {
		successRate := float64(lbMetrics.SuccessfulRequests) / float64(lbMetrics.TotalRequests) * 100
		log.Printf("  Success rate: %.1f%%", successRate)
	}

	// Backend health transitions
	log.Println("\nBackend Health Changes:")
	for backendID, count := range lbMetrics.BackendHealthChanges {
		log.Printf("  %s: %d transitions", backendID, count)
	}

	// Per-backend request distribution
	log.Println("\nBackend Distribution:")
	for _, stats := range loadBalancer.GetBackendStats() {
		log.Printf("  %v: %v requests (healthy=%v)", stats["name"], stats["total_requests"], stats["healthy"])
	}

	// Retry metrics for each backend
	log.Println("\nRetry Metrics:")
	backends := []agenkit.Agent{retryBackend1, retryBackend2, retryBackend3}
	for i, backend := range backends {
		if retryAgent, ok := backend.(*infrastructure.EnhancedRetryDecorator); ok {
			metrics := retryAgent.Metrics()
			log.Printf("  Agent %d:", i+1)
			log.Printf("    Total attempts: %d", metrics.TotalAttempts)
			log.Printf("    Successful on first: %d", metrics.SuccessfulFirstAttempt)
			log.Printf("    Successful on retry: %d", metrics.SuccessfulOnRetry)
			log.Printf("    Failed after retries: %d", metrics.FailedAfterRetries)
			log.Printf("    Total retries: %d", metrics.TotalRetries)
			if metrics.BackpressureDetected > 0 {
				log.Printf("    Backpressure detected: %d times", metrics.BackpressureDetected)
			}
		}
	}

	// Health metrics
	healthMetrics := healthChecker.Metrics()
	log.Println("\nHealth Checks:")
	for probeType, count := range healthMetrics.TotalChecks {
		success := healthMetrics.SuccessfulChecks[probeType]
		failedCount := healthMetrics.FailedChecks[probeType]
		log.Printf("  %s: %d/%d passed (%d failed)", probeType, success, count, failedCount)
	}

	// Export Prometheus metrics
	log.Println("\nPrometheus Metrics:")
	log.Println("============================================================")
	prometheusMetrics := healthChecker.ExportPrometheusMetrics()
	log.Println(prometheusMetrics)

	// Stop health checker
	healthChecker.Stop()
	log.Println("\nProduction agent system stopped.")
}
