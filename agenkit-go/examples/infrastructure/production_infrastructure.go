// Package main demonstrates comprehensive production infrastructure for autonomous agents.
//
// Demonstrates:
// 1. Load balancing across multiple agents
// 2. Health checks with liveness/readiness probes
// 3. Enhanced retry logic with jitter and budget awareness
// 4. Prometheus metrics export
// 5. Production-ready deployment patterns
package main

import (
	"context"
	"fmt"
	"log"
	"sync"
	"time"

	"github.com/scttfrdmn/agenkit/adapters"
	"github.com/scttfrdmn/agenkit/core"
	"github.com/scttfrdmn/agenkit/infrastructure"
)

func basicLoadBalancingExample() {
	fmt.Println("\n=== Basic Load Balancing Example ===\n")

	// Create multiple agent backends
	agents := []core.Agent{
		adapters.NewEchoAgent("backend-1"),
		adapters.NewEchoAgent("backend-2"),
		adapters.NewEchoAgent("backend-3"),
	}

	// Create load balancer with round-robin strategy
	config := infrastructure.DefaultLoadBalancerConfig()
	config.Strategy = infrastructure.RoundRobin
	config.EnableFailover = true

	balancer, err := infrastructure.NewLoadBalancer(agents, config, nil)
	if err != nil {
		log.Fatalf("Failed to create load balancer: %v", err)
	}

	// Process messages - they'll be distributed across backends
	ctx := context.Background()
	for i := 0; i < 6; i++ {
		message := core.Message{
			Role:    "user",
			Content: fmt.Sprintf("Request %d", i+1),
		}
		response, err := balancer.Process(ctx, message)
		if err != nil {
			log.Printf("Request %d failed: %v", i+1, err)
			continue
		}
		fmt.Printf("Request %d: %s\n", i+1, response.Content)
	}

	// Show backend statistics
	fmt.Println("\nBackend Statistics:")
	for _, stats := range balancer.GetBackendStats() {
		fmt.Printf("  %s: %d requests\n", stats["name"], stats["total_requests"])
	}

	fmt.Printf("\nLoad Balancer Metrics:\n")
	fmt.Printf("  Total requests: %d\n", balancer.Metrics().TotalRequests)
	fmt.Printf("  Successful: %d\n", balancer.Metrics().SuccessfulRequests)
}

func weightedLoadBalancingExample() {
	fmt.Println("\n=== Weighted Load Balancing Example ===\n")

	agents := []core.Agent{
		adapters.NewEchoAgent("high-capacity"),
		adapters.NewEchoAgent("medium-capacity"),
		adapters.NewEchoAgent("low-capacity"),
	}

	// Weight 3:2:1 means high-capacity gets 50% of traffic
	weights := []int{3, 2, 1}

	config := infrastructure.DefaultLoadBalancerConfig()
	config.Strategy = infrastructure.WeightedRoundRobin

	balancer, err := infrastructure.NewLoadBalancer(agents, config, weights)
	if err != nil {
		log.Fatalf("Failed to create load balancer: %v", err)
	}

	// Send 12 requests to see distribution
	ctx := context.Background()
	for i := 0; i < 12; i++ {
		message := core.Message{
			Role:    "user",
			Content: fmt.Sprintf("Request %d", i+1),
		}
		_, err := balancer.Process(ctx, message)
		if err != nil {
			log.Printf("Request %d failed: %v", i+1, err)
		}
	}

	fmt.Println("Request distribution (weights 3:2:1):")
	for _, stats := range balancer.GetBackendStats() {
		fmt.Printf("  %s: %d requests\n", stats["name"], stats["total_requests"])
	}
}

func leastConnectionsExample() {
	fmt.Println("\n=== Least Connections Strategy Example ===\n")

	agents := []core.Agent{
		adapters.NewEchoAgent("agent-1"),
		adapters.NewEchoAgent("agent-2"),
		adapters.NewEchoAgent("agent-3"),
	}

	config := infrastructure.DefaultLoadBalancerConfig()
	config.Strategy = infrastructure.LeastConnections

	balancer, err := infrastructure.NewLoadBalancer(agents, config, nil)
	if err != nil {
		log.Fatalf("Failed to create load balancer: %v", err)
	}

	// Simulate concurrent requests
	ctx := context.Background()
	var wg sync.WaitGroup

	for i := 0; i < 10; i++ {
		wg.Add(1)
		go func(num int) {
			defer wg.Done()
			message := core.Message{
				Role:    "user",
				Content: fmt.Sprintf("Concurrent request %d", num),
			}
			_, err := balancer.Process(ctx, message)
			if err != nil {
				log.Printf("Request %d failed: %v", num, err)
			}
		}(i)
	}

	wg.Wait()

	fmt.Println("Request distribution (least connections):")
	for _, stats := range balancer.GetBackendStats() {
		fmt.Printf("  %s: %d requests\n", stats["name"], stats["total_requests"])
	}
}

func healthCheckExample() {
	fmt.Println("\n=== Health Check Example ===\n")

	agent := adapters.NewEchoAgent("monitored-agent")

	// Configure health checks
	config := infrastructure.DefaultHealthCheckConfig()
	config.LivenessEnabled = true
	config.ReadinessEnabled = true
	config.LivenessInterval = 5 * time.Second
	config.ReadinessInterval = 3 * time.Second

	health := infrastructure.NewHealthChecker(agent, config)

	// Perform manual health checks
	ctx := context.Background()
	livenessResult := health.CheckLiveness(ctx)
	fmt.Printf("Liveness: %s\n", livenessResult.Status)
	fmt.Printf("  Message: %s\n", livenessResult.Message)
	fmt.Printf("  Duration: %.2fms\n", livenessResult.DurationMS)

	readinessResult := health.CheckReadiness(ctx)
	fmt.Printf("\nReadiness: %s\n", readinessResult.Status)
	fmt.Printf("  Message: %s\n", readinessResult.Message)
	fmt.Printf("  Duration: %.2fms\n", readinessResult.DurationMS)

	// Start background health checks
	fmt.Println("\nStarting background health checks...")
	health.Start(ctx)

	// Let it run for a bit
	time.Sleep(10 * time.Second)

	// Export Prometheus metrics
	fmt.Println("\nPrometheus Metrics:")
	fmt.Println(health.ExportPrometheusMetrics())

	// Stop health checks
	health.Stop()
}

func enhancedRetryExample() {
	fmt.Println("\n=== Enhanced Retry Example ===\n")

	agent := adapters.NewEchoAgent("unreliable-agent")

	// Configure enhanced retry
	config := infrastructure.DefaultEnhancedRetryConfig()
	config.MaxAttempts = 5
	config.JitterType = infrastructure.FullJitter
	config.EnableBackpressure = true
	config.EnableBudget = false // Disabled for example

	retryAgent := infrastructure.NewEnhancedRetryDecorator(agent, config)

	// Process messages with automatic retry
	ctx := context.Background()
	message := core.Message{
		Role:    "user",
		Content: "Test with retry",
	}
	response, err := retryAgent.Process(ctx, message)
	if err != nil {
		log.Printf("Failed after retries: %v", err)
		return
	}
	fmt.Printf("Response: %s\n", response.Content)

	// Show retry metrics
	metrics := retryAgent.Metrics()
	fmt.Printf("\nRetry Metrics:\n")
	fmt.Printf("  Total attempts: %d\n", metrics.TotalAttempts)
	fmt.Printf("  Successful on first try: %d\n", metrics.SuccessfulFirstAttempt)
	fmt.Printf("  Successful after retry: %d\n", metrics.SuccessfulOnRetry)
	fmt.Printf("  Total jitter added: %.2fs\n", metrics.TotalJitterAdded)
}

func errorClassificationExample() {
	fmt.Println("\n=== Error Classification Example ===\n")

	agent := adapters.NewEchoAgent("agent-with-errors")

	// Custom error classifier
	errorClassifier := func(err error) infrastructure.ErrorClass {
		errorStr := err.Error()
		if contains(errorStr, "rate limit") {
			return infrastructure.RateLimit
		} else if contains(errorStr, "timeout") {
			return infrastructure.Timeout
		} else if contains(errorStr, "500") {
			return infrastructure.ServerError
		}
		return infrastructure.UnknownError
	}

	config := infrastructure.DefaultEnhancedRetryConfig()
	config.ErrorClassifier = errorClassifier
	config.JitterType = infrastructure.FullJitter

	retryAgent := infrastructure.NewEnhancedRetryDecorator(agent, config)

	// The agent will use different retry strategies based on error type
	ctx := context.Background()
	message := core.Message{
		Role:    "user",
		Content: "Test error classification",
	}
	response, err := retryAgent.Process(ctx, message)
	if err != nil {
		log.Printf("Failed: %v", err)
		return
	}

	fmt.Printf("Response: %s\n", response.Content)
	fmt.Printf("\nError class distribution:\n")
	for errorClass, count := range retryAgent.Metrics().ErrorClassCounts {
		fmt.Printf("  %s: %d\n", errorClass, count)
	}
}

func productionDeploymentExample() {
	fmt.Println("\n=== Production Deployment Example ===\n")

	// Step 1: Create backend agents
	backends := []core.Agent{
		adapters.NewEchoAgent("prod-backend-1"),
		adapters.NewEchoAgent("prod-backend-2"),
		adapters.NewEchoAgent("prod-backend-3"),
	}

	// Step 2: Wrap each backend with enhanced retry
	retryConfig := infrastructure.DefaultEnhancedRetryConfig()
	retryConfig.MaxAttempts = 3
	retryConfig.JitterType = infrastructure.FullJitter
	retryConfig.EnableBackpressure = true

	retryBackends := make([]core.Agent, len(backends))
	for i, backend := range backends {
		retryBackends[i] = infrastructure.NewEnhancedRetryDecorator(backend, retryConfig)
	}

	// Step 3: Add load balancer
	lbConfig := infrastructure.DefaultLoadBalancerConfig()
	lbConfig.Strategy = infrastructure.LeastConnections
	lbConfig.HealthCheckInterval = 30 * time.Second
	lbConfig.EnableFailover = true

	loadBalancer, err := infrastructure.NewLoadBalancer(retryBackends, lbConfig, nil)
	if err != nil {
		log.Fatalf("Failed to create load balancer: %v", err)
	}

	// Step 4: Add health checks
	healthConfig := infrastructure.DefaultHealthCheckConfig()
	healthConfig.LivenessEnabled = true
	healthConfig.ReadinessEnabled = true
	healthConfig.StartupEnabled = true

	healthChecker := infrastructure.NewHealthChecker(loadBalancer, healthConfig)

	ctx := context.Background()
	healthChecker.Start(ctx)

	// Step 5: Process production traffic
	fmt.Println("Processing production traffic...")

	var wg sync.WaitGroup
	for i := 0; i < 20; i++ {
		wg.Add(1)
		go func(num int) {
			defer wg.Done()
			message := core.Message{
				Role:    "user",
				Content: fmt.Sprintf("Production request %d", num+1),
			}
			_, err := loadBalancer.Process(ctx, message)
			if err != nil {
				log.Printf("Request %d failed: %v", num+1, err)
			}
		}(i)
	}

	wg.Wait()

	fmt.Printf("\nProcessed 20 requests\n")
	fmt.Printf("Load balancer metrics:\n")
	fmt.Printf("  Successful: %d\n", loadBalancer.Metrics().SuccessfulRequests)
	fmt.Printf("  Failed: %d\n", loadBalancer.Metrics().FailedRequests)
	fmt.Printf("  Failovers: %d\n", loadBalancer.Metrics().FailoverAttempts)

	// Export health metrics
	fmt.Println("\nHealth Status:")
	if healthChecker.IsHealthy() {
		fmt.Println("  Overall health: Healthy")
	} else {
		fmt.Println("  Overall health: Unhealthy")
	}
	fmt.Printf("  Uptime: %.1fs\n", healthChecker.Metrics().GetUptime())

	healthChecker.Stop()
}

func contains(s, substr string) bool {
	return len(s) >= len(substr) && (s == substr || len(s) > len(substr) && findSubstring(s, substr))
}

func findSubstring(s, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}

func main() {
	fmt.Println("Agenkit Production Infrastructure Examples")
	fmt.Println("=================================================")

	basicLoadBalancingExample()
	weightedLoadBalancingExample()
	leastConnectionsExample()
	healthCheckExample()
	enhancedRetryExample()
	errorClassificationExample()
	productionDeploymentExample()

	fmt.Println("\n=================================================")
	fmt.Println("All examples completed!")
}
