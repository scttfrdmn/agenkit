/*
Circuit Breaker Middleware Example

This example demonstrates WHY and HOW to use circuit breaker middleware for
preventing cascading failures in distributed systems.

WHY USE CIRCUIT BREAKER MIDDLEWARE?
-----------------------------------
- Prevent cascading failures: Stop calling a failing service before it causes system-wide collapse
- Fail fast: Return errors immediately instead of waiting for timeouts
- Allow recovery: Give failing services time to recover without constant traffic
- Resource protection: Prevent thread/connection pool exhaustion from hanging requests

WHEN TO USE:
- External service calls (databases, APIs, microservices)
- Operations with potential for prolonged outages
- Services that experience load-related failures
- Any dependency where failures could cascade to other systems

WHEN NOT TO USE:
- Single-point operations where retry is sufficient
- Services with guaranteed availability (e.g., localhost)
- Operations where every attempt must be made (critical writes)
- Systems where stale data is unacceptable

TRADE-OFFS:
- Temporary unavailability: Service might recover while circuit is open
- State management: Need to track failure counts and timings across requests
- Configuration tuning: Wrong thresholds can cause premature or delayed trips
- Cold start issues: First requests after recovery may be slower

Run with: go run agenkit-go/examples/middleware/circuit_breaker_example.go
*/

package main

import (
	"context"
	"fmt"
	"strings"
	"time"

	"github.com/agenkit/agenkit-go/agenkit"
	"github.com/agenkit/agenkit-go/middleware"
)

// UnstableExternalAPI simulates an external API that experiences outages
type UnstableExternalAPI struct {
	name      string
	callCount int
	isDown    bool
}

func NewUnstableExternalAPI(name string) *UnstableExternalAPI {
	return &UnstableExternalAPI{
		name: name,
	}
}

func (a *UnstableExternalAPI) Name() string {
	return a.name
}

func (a *UnstableExternalAPI) Capabilities() []string {
	return []string{"weather_data"}
}

func (a *UnstableExternalAPI) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	a.callCount++

	// Simulate service going down after 3 calls
	if a.callCount > 3 {
		a.isDown = true
	}

	if a.isDown {
		// Simulate slow failing service (timeout scenario)
		time.Sleep(200 * time.Millisecond)
		return nil, fmt.Errorf("ServiceError: API is experiencing an outage")
	}

	return agenkit.NewMessage("assistant",
		fmt.Sprintf("Weather data: 72°F, Sunny (call #%d)", a.callCount)), nil
}

func (a *UnstableExternalAPI) Recover() {
	a.isDown = false
	a.callCount = 0
}

// Example 1: Basic Circuit Breaker
func example1BasicCircuitBreaker() {
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("EXAMPLE 1: Basic Circuit Breaker")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println("\nWHY: External API that experiences an outage")
	fmt.Println("     Circuit breaker prevents repeated calls to failing service\n")

	api := NewUnstableExternalAPI("external-api")

	// Wrap with circuit breaker
	config := middleware.CircuitBreakerConfig{
		FailureThreshold: 3,                // Open after 3 failures
		RecoveryTimeout:  2 * time.Second,  // Try recovery after 2 seconds
		SuccessThreshold: 2,                // Need 2 successes to fully recover
		Timeout:          1 * time.Second,  // 1 second request timeout
	}
	protectedAPI := middleware.NewCircuitBreakerDecorator(api, config)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Get weather for San Francisco")

	// Make successful calls
	fmt.Println("Making successful calls...")
	for i := 0; i < 3; i++ {
		response, err := protectedAPI.Process(ctx, message)
		if err != nil {
			fmt.Printf("❌ Call %d: %v\n", i+1, err)
		} else {
			fmt.Printf("✅ Call %d: %s\n", i+1, response.Content)
		}
	}

	// Now the service goes down
	fmt.Println("\n💥 Service goes down!")
	fmt.Println("Making calls that will fail...\n")

	for i := 0; i < 5; i++ {
		response, err := protectedAPI.Process(ctx, message)
		if err != nil {
			// Check if it's a circuit breaker error
			if _, ok := err.(*middleware.CircuitBreakerError); ok {
				fmt.Printf("⚡ Call %d: Circuit breaker OPEN - %v\n", i+4, err)
			} else {
				fmt.Printf("❌ Call %d: Failed - %v\n", i+4, err)
			}
		} else {
			fmt.Printf("✅ Call %d: %s\n", i+4, response.Content)
		}
	}

	// Display metrics
	metrics := protectedAPI.Metrics()
	fmt.Printf("\n📊 Circuit State: %s\n", protectedAPI.State())
	fmt.Printf("   Total requests: %d\n", metrics.TotalRequests)
	fmt.Printf("   Failed: %d\n", metrics.FailedRequests)
	fmt.Printf("   Rejected (fast-fail): %d\n", metrics.RejectedRequests)

	fmt.Println("\n💡 KEY INSIGHT:")
	fmt.Println("   After 3 failures, circuit opened and rejected remaining calls instantly.")
	fmt.Println("   No more slow timeouts - system fails fast and protects resources!")
}

// Example 2: Recovery Scenario
func example2RecoveryScenario() {
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("EXAMPLE 2: Recovery Scenario")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println("\nWHY: Service recovers and circuit breaker detects it")
	fmt.Println("     Demonstrates HALF_OPEN -> CLOSED transition\n")

	api := NewUnstableExternalAPI("external-api")
	config := middleware.CircuitBreakerConfig{
		FailureThreshold: 2,
		RecoveryTimeout:  1 * time.Second,
		SuccessThreshold: 2,
		Timeout:          500 * time.Millisecond,
	}
	protectedAPI := middleware.NewCircuitBreakerDecorator(api, config)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Get data")

	// Cause failures to open circuit
	fmt.Println("Causing failures to open circuit...")
	api.isDown = true

	for i := 0; i < 3; i++ {
		_, err := protectedAPI.Process(ctx, message)
		if err != nil {
			if _, ok := err.(*middleware.CircuitBreakerError); ok {
				fmt.Printf("⚡ Failure %d: CircuitBreakerError\n", i+1)
			} else {
				fmt.Printf("❌ Failure %d: %v\n", i+1, err)
			}
		}
	}

	fmt.Printf("⚡ Circuit State: %s\n", protectedAPI.State())

	// Wait for recovery timeout
	fmt.Printf("\n⏳ Waiting %v for recovery timeout...\n", config.RecoveryTimeout)
	time.Sleep(config.RecoveryTimeout + 100*time.Millisecond)

	// Service recovers
	fmt.Println("🔧 Service recovers!\n")
	api.Recover()

	// Next call will transition to HALF_OPEN
	fmt.Println("Making test call (circuit will enter HALF_OPEN)...")
	response, err := protectedAPI.Process(ctx, message)
	if err != nil {
		fmt.Printf("❌ Failed: %v\n", err)
	} else {
		fmt.Printf("✅ Success: %s\n", response.Content)
		fmt.Printf("   Circuit State: %s\n", protectedAPI.State())
	}

	// Second success will close the circuit
	fmt.Println("\nMaking second test call (should close circuit)...")
	response, err = protectedAPI.Process(ctx, message)
	if err != nil {
		fmt.Printf("❌ Failed: %v\n", err)
	} else {
		fmt.Printf("✅ Success: %s\n", response.Content)
		fmt.Printf("   Circuit State: %s 🎉\n", protectedAPI.State())
	}

	// Display state transitions
	fmt.Println("\n📊 State Transitions:")
	metrics := protectedAPI.Metrics()
	for transition, count := range metrics.StateChanges {
		fmt.Printf("   %s: %d time(s)\n", transition, count)
	}

	fmt.Println("\n💡 KEY INSIGHT:")
	fmt.Println("   Circuit breaker automatically tests recovery and closes when healthy.")
	fmt.Println("   State flow: CLOSED -> OPEN -> HALF_OPEN -> CLOSED")
}

// FlakeyDatabase simulates a database with transient failures and occasional outages
type FlakeyDatabase struct {
	name           string
	callCount      int
	failurePattern []bool // true = fail
}

func NewFlakeyDatabase(name string) *FlakeyDatabase {
	return &FlakeyDatabase{
		name:           name,
		failurePattern: []bool{false, true, false, true, true, true, true}, // Pattern of failures
	}
}

func (d *FlakeyDatabase) Name() string {
	return d.name
}

func (d *FlakeyDatabase) Capabilities() []string {
	return []string{"query"}
}

func (d *FlakeyDatabase) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	idx := d.callCount % len(d.failurePattern)
	d.callCount++

	if d.failurePattern[idx] {
		return nil, fmt.Errorf("DatabaseError: Connection pool exhausted")
	}

	return agenkit.NewMessage("assistant",
		fmt.Sprintf("Query result: [data] (call #%d)", d.callCount)), nil
}

// Example 3: Combining with Retry Middleware
func example3CircuitBreakerWithRetry() {
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("EXAMPLE 3: Circuit Breaker + Retry")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println("\nWHY: Retry transient failures, but fail fast if service is down")
	fmt.Println("     Layered protection: retry handles transient, circuit handles persistent\n")

	db := NewFlakeyDatabase("database")

	// Layer 1: Retry for transient failures (inner)
	retryConfig := middleware.RetryConfig{
		MaxAttempts:       2,
		InitialBackoff:    100 * time.Millisecond,
		BackoffMultiplier: 2.0,
	}
	retryDB := middleware.NewRetryDecorator(db, retryConfig)

	// Layer 2: Circuit breaker for persistent failures (outer)
	cbConfig := middleware.CircuitBreakerConfig{
		FailureThreshold: 3,
		RecoveryTimeout:  1500 * time.Millisecond,
		SuccessThreshold: 1,
		Timeout:          2 * time.Second,
	}
	protectedDB := middleware.NewCircuitBreakerDecorator(retryDB, cbConfig)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "SELECT * FROM users")

	fmt.Println("Making calls with layered protection (retry + circuit breaker)...\n")

	for i := 0; i < 8; i++ {
		response, err := protectedDB.Process(ctx, message)
		if err != nil {
			if _, ok := err.(*middleware.CircuitBreakerError); ok {
				fmt.Printf("⚡ Call %d: Circuit OPEN - failing fast\n", i+1)
			} else {
				fmt.Printf("❌ Call %d: Failed after retries\n", i+1)
			}
		} else {
			fmt.Printf("✅ Call %d: Success - %s\n", i+1, response.Content)
		}

		time.Sleep(100 * time.Millisecond)
	}

	fmt.Printf("\n📊 Final State: %s\n", protectedDB.State())
	fmt.Println("   This pattern prevents: retry storms on failing services!")

	fmt.Println("\n💡 KEY INSIGHT:")
	fmt.Println("   Retry handles 1-2 transient failures automatically.")
	fmt.Println("   Circuit breaker kicks in when failures become persistent.")
	fmt.Println("   This prevents wasting resources on a clearly failing service.")
}

// OverloadedService simulates a service that fails under load
type OverloadedService struct {
	name         string
	requestCount int
}

func NewOverloadedService(name string) *OverloadedService {
	return &OverloadedService{
		name: name,
	}
}

func (s *OverloadedService) Name() string {
	return s.name
}

func (s *OverloadedService) Capabilities() []string {
	return []string{"process_job"}
}

func (s *OverloadedService) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	s.requestCount++

	// Fail every other request to simulate overload
	if s.requestCount%2 == 0 {
		return nil, fmt.Errorf("ServiceOverload: Too many concurrent requests")
	}

	return agenkit.NewMessage("assistant", "Job processed"), nil
}

// Example 4: Metrics Tracking
func example4MetricsTracking() {
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("EXAMPLE 4: Metrics Tracking")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println("\nWHY: Monitor circuit breaker behavior for alerting and debugging")
	fmt.Println("     Track success/failure rates and state transitions\n")

	service := NewOverloadedService("overloaded-service")
	config := middleware.CircuitBreakerConfig{
		FailureThreshold: 3,
		RecoveryTimeout:  1 * time.Second,
		SuccessThreshold: 2,
		Timeout:          1 * time.Second,
	}
	protectedService := middleware.NewCircuitBreakerDecorator(service, config)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Process job")

	fmt.Println("Simulating load on overloaded service...\n")

	for i := 0; i < 10; i++ {
		_, err := protectedService.Process(ctx, message)
		if err != nil {
			if _, ok := err.(*middleware.CircuitBreakerError); ok {
				fmt.Printf("⚡ Request %d: Rejected (circuit open)\n", i+1)
			} else {
				fmt.Printf("❌ Request %d: Failed\n", i+1)
			}
		} else {
			fmt.Printf("✅ Request %d: Success\n", i+1)
		}

		time.Sleep(50 * time.Millisecond)
	}

	// Display comprehensive metrics
	metrics := protectedService.Metrics()

	fmt.Println("\n" + strings.Repeat("=", 50))
	fmt.Println("📊 CIRCUIT BREAKER METRICS")
	fmt.Println(strings.Repeat("=", 50))
	fmt.Printf("Total Requests:       %d\n", metrics.TotalRequests)
	fmt.Printf("Successful:           %d (%.1f%%)\n",
		metrics.SuccessfulRequests,
		float64(metrics.SuccessfulRequests)/float64(metrics.TotalRequests)*100)
	fmt.Printf("Failed:               %d (%.1f%%)\n",
		metrics.FailedRequests,
		float64(metrics.FailedRequests)/float64(metrics.TotalRequests)*100)
	fmt.Printf("Rejected (Fast-Fail): %d (%.1f%%)\n",
		metrics.RejectedRequests,
		float64(metrics.RejectedRequests)/float64(metrics.TotalRequests)*100)
	fmt.Printf("\nCurrent State:        %s\n", metrics.CurrentState)

	if metrics.LastStateChange != nil {
		elapsed := time.Since(*metrics.LastStateChange)
		fmt.Printf("Time in State:        %.2fs\n", elapsed.Seconds())
	}

	fmt.Println("\nState Transition History:")
	for transition, count := range metrics.StateChanges {
		fmt.Printf("  %s: %d\n", transition, count)
	}

	fmt.Println("\n💡 Use these metrics for:")
	fmt.Println("  - Alerting on circuit state changes")
	fmt.Println("  - Tracking service health trends")
	fmt.Println("  - Capacity planning and load testing")
	fmt.Println("  - Debugging cascading failure scenarios")
}

func main() {
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("CIRCUIT BREAKER MIDDLEWARE EXAMPLES FOR AGENKIT-GO")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println("\nThese examples show how circuit breakers prevent cascading")
	fmt.Println("failures and protect your system from unhealthy dependencies.\n")

	// Run examples
	example1BasicCircuitBreaker()

	fmt.Print("\nPress Enter to continue...")
	fmt.Scanln()

	example2RecoveryScenario()

	fmt.Print("\nPress Enter to continue...")
	fmt.Scanln()

	example3CircuitBreakerWithRetry()

	fmt.Print("\nPress Enter to continue...")
	fmt.Scanln()

	example4MetricsTracking()

	// Summary
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("KEY TAKEAWAYS")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println(`
1. CIRCUIT BREAKER STATES:
   - CLOSED: Normal operation, requests pass through
   - OPEN: Too many failures, fail fast without calling service
   - HALF_OPEN: Testing if service has recovered

2. WHY USE CIRCUIT BREAKERS:
   - Prevent cascading failures in distributed systems
   - Fail fast instead of waiting for timeouts
   - Give failing services time to recover
   - Protect resource pools (connections, threads)

3. CONFIGURATION:
   - FailureThreshold: How many failures before opening (3-5 typical)
   - RecoveryTimeout: How long to wait before testing recovery (30-60s typical)
   - SuccessThreshold: Successful calls needed to close circuit (1-2 typical)
   - Timeout: Request timeout duration (5-30s typical)

4. REAL-WORLD SCENARIOS:
   - External API outages (third-party services down)
   - Database connection pool exhaustion
   - Service overload and cascading failures
   - Network partitions and timeouts

5. COMBINE WITH RETRY:
   - Retry layer (inner): Handles transient failures (1-3 retries)
   - Circuit breaker (outer): Handles persistent failures
   - This prevents "retry storms" on failing services

6. MONITORING:
   - Track state transitions (CLOSED->OPEN alerts critical)
   - Monitor rejection rate (high = service issues)
   - Measure time in OPEN state (long = extended outage)
   - Alert on repeated OPEN/CLOSED cycles (flapping)

7. BEST PRACTICES:
   - Set thresholds based on service SLOs
   - Use longer RecoveryTimeout for external services
   - Log state changes for debugging
   - Combine with metrics and alerting
   - Test failure scenarios in staging

Next steps:
- See retry_example.go for retry patterns
- See metrics_example.go for observability
- See MIDDLEWARE.md for design patterns
	`)
}
