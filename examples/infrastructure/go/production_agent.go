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
	"fmt"
	"log"
	"math/rand"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/core"
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

func (a *SimulatedAgent) Process(msg core.Message) (core.Message, error) {
	a.requestCount++

	// Simulate processing time
	time.Sleep(100 * time.Millisecond)

	// Simulate occasional failures
	if rand.Float64() < a.failureRate {
		return core.Message{}, fmt.Errorf("%s: simulated transient error", a.agentName)
	}

	return core.Message{
		Role:    "agent",
		Content: fmt.Sprintf("%s processed: %s", a.agentName, msg.Content),
		Metadata: map[string]interface{}{
			"agent":         a.agentName,
			"request_count": a.requestCount,
			"timestamp":     time.Now().Format(time.RFC3339),
		},
	}, nil
}

func main() {
	log.Println("Starting production agent system...")

	// 1. Create backend agents with varying failure rates
	backend1 := NewSimulatedAgent("agent-1", 0.1)
	backend2 := NewSimulatedAgent("agent-2", 0.05)
	backend3 := NewSimulatedAgent("agent-3", 0.15)

	// 2. Wrap each backend with enhanced retry
	retryConfig := infrastructure.EnhancedRetryConfig{
		MaxAttempts:           3,
		InitialBackoff:        100 * time.Millisecond,
		MaxBackoff:            5 * time.Second,
		BackoffMultiplier:     2.0,
		JitterType:            infrastructure.JitterTypeFull,
		EnableBackpressure:    true,
		BackpressureThreshold: 0.3,
		BackpressureWindow:    10,
		ErrorStrategies:       make(map[infrastructure.ErrorClass]infrastructure.ErrorStrategy),
	}

	// Add default error strategies
	retryConfig.ErrorStrategies[infrastructure.ErrorClassTransient] = infrastructure.ErrorStrategy{
		ErrorClass:        infrastructure.ErrorClassTransient,
		MaxAttempts:       5,
		InitialBackoff:    100 * time.Millisecond,
		MaxBackoff:        5 * time.Second,
		BackoffMultiplier: 2.0,
		ShouldRetry:       true,
	}

	retryBackend1 := infrastructure.NewEnhancedRetryDecorator(backend1, retryConfig)
	retryBackend2 := infrastructure.NewEnhancedRetryDecorator(backend2, retryConfig)
	retryBackend3 := infrastructure.NewEnhancedRetryDecorator(backend3, retryConfig)

	// 3. Create load balancer with health checking
	lbConfig := infrastructure.LoadBalancerConfig{
		Strategy:             infrastructure.StrategyLeastConnections,
		HealthCheckEnabled:   true,
		HealthCheckInterval:  5 * time.Second,
		HealthCheckTimeout:   2 * time.Second,
		MaxRetriesPerBackend: 2,
	}

	loadBalancer := infrastructure.NewLoadBalancer(
		[]core.Agent{retryBackend1, retryBackend2, retryBackend3},
		lbConfig,
	)

	// 4. Set up health checker for the load balancer
	healthConfig := infrastructure.HealthCheckConfig{
		LivenessEnabled:           true,
		LivenessInterval:          10 * time.Second,
		LivenessFailureThreshold:  3,
		ReadinessEnabled:          true,
		ReadinessInterval:         5 * time.Second,
		ReadinessFailureThreshold: 2,
		StartupEnabled:            true,
		StartupTimeout:            30 * time.Second,
		StartupFailureThreshold:   5,
	}

	healthChecker := infrastructure.NewHealthChecker(loadBalancer, healthConfig)
	healthChecker.Start()

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
		msg := core.Message{
			Role:    "user",
			Content: fmt.Sprintf("Request %d", i),
		}

		response, err := loadBalancer.Process(msg)
		if err != nil {
			log.Printf("Request %d: FAILED - %v", i, err)
			failed++
		} else {
			log.Printf("Request %d: SUCCESS - %s", i, response.Content)
			successful++
		}

		// Brief pause between requests
		time.Sleep(200 * time.Millisecond)
	}

	// 6. Export metrics
	log.Println("\n" + "============================================================")
	log.Println("FINAL METRICS")
	log.Println("============================================================")

	// Load balancer metrics
	lbMetrics := loadBalancer.GetMetrics()
	log.Printf("\nLoad Balancer:")
	log.Printf("  Total requests: %d", lbMetrics.TotalRequests)
	log.Printf("  Successful: %d", lbMetrics.SuccessfulRequests)
	log.Printf("  Failed: %d", lbMetrics.FailedRequests)
	if lbMetrics.TotalRequests > 0 {
		successRate := float64(lbMetrics.SuccessfulRequests) / float64(lbMetrics.TotalRequests) * 100
		log.Printf("  Success rate: %.1f%%", successRate)
	}

	// Backend distribution
	log.Println("\nBackend Distribution:")
	for backendID, count := range lbMetrics.BackendRequestCounts {
		log.Printf("  %s: %d requests", backendID, count)
	}

	// Retry metrics for each backend
	log.Println("\nRetry Metrics:")
	backends := []core.Agent{retryBackend1, retryBackend2, retryBackend3}
	for i, backend := range backends {
		if retryAgent, ok := backend.(*infrastructure.EnhancedRetryDecorator); ok {
			metrics := retryAgent.GetMetrics()
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
	healthMetrics := healthChecker.GetMetrics()
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
