/*
Batching Middleware Example

This example demonstrates WHY and HOW to use batching middleware for improving
throughput by processing multiple concurrent requests together.

WHY USE BATCHING MIDDLEWARE?
----------------------------
- Improve throughput: Process multiple requests together for better efficiency
- Reduce costs: Use batch API endpoints (e.g., OpenAI batch API) for lower per-request costs
- Amortize overhead: Spread per-request setup costs across multiple requests
- Better resource utilization: Maximize use of available processing capacity
- Reduce network round-trips: Send multiple operations in one call (databases, APIs)

WHEN TO USE:
- LLM batch processing endpoints (OpenAI, Anthropic batch APIs)
- Database bulk operations (INSERT, UPDATE, DELETE multiple records)
- High-throughput data pipelines (log processing, analytics)
- API aggregation services (combining multiple API calls)
- Image/video processing pipelines (batch GPU operations)

WHEN NOT TO USE:
- Real-time interactive applications (adds latency)
- Low-volume APIs (batching overhead not worth it)
- Operations requiring immediate feedback
- When request interdependencies make batching complex
- Single-threaded/sequential processing patterns

TRADE-OFFS:
- Latency vs throughput: Adds wait time but improves overall throughput
- Memory usage: Buffers requests in queue (configure max_queue_size)
- Complexity: Need to handle partial failures within batches
- Tuning required: Finding optimal batch_size and wait_time

CONFIGURATION:
- max_batch_size: Process when this many requests collected (default: 10)
- max_wait_time: Process after this much time (default: 100ms)
- max_queue_size: Maximum pending requests (default: 1000)

Run with: go run agenkit-go/examples/middleware/batching_example.go
*/

package main

import (
	"context"
	"fmt"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	"github.com/agenkit/agenkit-go/agenkit"
	"github.com/agenkit/agenkit-go/middleware"
)

// MockLLMBatchAgent simulates an LLM that benefits from batch processing.
//
// Real-world example: OpenAI Batch API offers 50% cost savings.
// https://platform.openai.com/docs/guides/batch
type MockLLMBatchAgent struct {
	batchCount     atomic.Int32
	totalProcessed atomic.Int32
}

func NewMockLLMBatchAgent() *MockLLMBatchAgent {
	return &MockLLMBatchAgent{}
}

func (a *MockLLMBatchAgent) Name() string {
	return "llm-batch-processor"
}

func (a *MockLLMBatchAgent) Capabilities() []string {
	return []string{"text-generation", "batch-processing"}
}

func (a *MockLLMBatchAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	// Simulate per-batch setup overhead (amortized across batch)
	time.Sleep(50 * time.Millisecond)

	// Simulate per-request processing
	time.Sleep(10 * time.Millisecond)

	a.totalProcessed.Add(1)

	response := agenkit.NewMessage("assistant", fmt.Sprintf("Generated: %s", message.Content))
	response.Metadata = map[string]interface{}{
		"model":        "gpt-4-batch",
		"cost_savings": "50%", // Batch API pricing
	}

	return response, nil
}

// MockDatabaseAgent simulates database bulk INSERT operations.
//
// Real-world example: PostgreSQL bulk INSERT is 10-100x faster than
// individual INSERTs due to reduced round-trips and transaction overhead.
type MockDatabaseAgent struct {
	dbCalls        atomic.Int32
	recordsInserted atomic.Int32
}

func NewMockDatabaseAgent() *MockDatabaseAgent {
	return &MockDatabaseAgent{}
}

func (a *MockDatabaseAgent) Name() string {
	return "database-bulk-inserter"
}

func (a *MockDatabaseAgent) Capabilities() []string {
	return []string{"database", "bulk-operations"}
}

func (a *MockDatabaseAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	// Simulate network + connection overhead (amortized in batch)
	time.Sleep(20 * time.Millisecond)

	// Simulate actual insert
	time.Sleep(1 * time.Millisecond)

	a.dbCalls.Add(1)
	a.recordsInserted.Add(1)

	response := agenkit.NewMessage("assistant", fmt.Sprintf("Inserted: %s", message.Content))
	response.Metadata = map[string]interface{}{
		"table":     "users",
		"operation": "INSERT",
	}

	return response, nil
}

// MockAnalyticsAgent simulates high-throughput log/event processing.
//
// Real-world example: Processing millions of events per second in
// analytics pipelines by batching writes to data warehouses.
type MockAnalyticsAgent struct {
	eventsProcessed atomic.Int32
}

func NewMockAnalyticsAgent() *MockAnalyticsAgent {
	return &MockAnalyticsAgent{}
}

func (a *MockAnalyticsAgent) Name() string {
	return "analytics-processor"
}

func (a *MockAnalyticsAgent) Capabilities() []string {
	return []string{"analytics", "stream-processing"}
}

func (a *MockAnalyticsAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	// Simulate very fast processing per event
	time.Sleep(5 * time.Millisecond)

	a.eventsProcessed.Add(1)

	response := agenkit.NewMessage("assistant", fmt.Sprintf("Processed event: %s", message.Content))
	response.Metadata = map[string]interface{}{
		"pipeline":  "clickstream",
		"timestamp": time.Now().Unix(),
	}

	return response, nil
}

// Example 1: LLM Batch Processing
//
// Demonstrates cost savings with batch LLM API endpoints.
// OpenAI Batch API: 50% cost reduction, 24-hour turnaround.
func example1LLMBatchProcessing() {
	fmt.Println("\n" + strings.Repeat("=", 70))
	fmt.Println("Example 1: LLM Batch Processing (Cost Optimization)")
	fmt.Println(strings.Repeat("=", 70))

	fmt.Println("\nScenario: Processing 20 LLM requests")
	fmt.Println("Real-world: OpenAI Batch API offers 50% cost savings")
	fmt.Println("Trade-off: Adds latency but reduces costs significantly\n")

	agent := NewMockLLMBatchAgent()

	// Configure batching for LLM: larger batches, willing to wait longer
	config := middleware.BatchingConfig{
		MaxBatchSize: 5,                  // Batch up to 5 requests
		MaxWaitTime:  100 * time.Millisecond, // Wait up to 100ms to fill batch
		MaxQueueSize: 100,
	}

	batchingAgent := middleware.NewBatchingDecorator(agent, config)

	// Simulate 20 concurrent LLM requests
	fmt.Println("Sending 20 concurrent LLM requests...")
	start := time.Now()

	ctx := context.Background()
	var wg sync.WaitGroup
	results := make([]*agenkit.Message, 20)
	errors := make([]error, 20)

	for i := 0; i < 20; i++ {
		wg.Add(1)
		go func(idx int) {
			defer wg.Done()
			msg := agenkit.NewMessage("user", fmt.Sprintf("Summarize document %d", idx+1))
			result, err := batchingAgent.Process(ctx, msg)
			results[idx] = result
			errors[idx] = err
		}(i)
	}

	wg.Wait()
	elapsed := time.Since(start)

	fmt.Printf("✓ Completed in %.2fs\n", elapsed.Seconds())
	fmt.Printf("   Total requests: %d\n", len(results))
	if results[0] != nil {
		fmt.Printf("   Sample result: %s\n", results[0].Content)
	}

	// Show batching metrics
	metrics := batchingAgent.Metrics()
	fmt.Println("\n📊 Batching Metrics:")
	fmt.Printf("   Total batches: %d\n", metrics.TotalBatches)
	fmt.Printf("   Avg batch size: %.1f\n", metrics.AvgBatchSize())
	fmt.Printf("   Requests/batch ratio: %d/%d\n", metrics.TotalRequests, metrics.TotalBatches)
	fmt.Println("   💰 Cost savings: ~50% (batch API pricing)")

	batchingAgent.Shutdown()
}

// Example 2: Database Bulk Operations
//
// Demonstrates throughput improvement for database operations.
// Bulk INSERT can be 10-100x faster than individual INSERTs.
func example2DatabaseBulkOperations() {
	fmt.Println("\n" + strings.Repeat("=", 70))
	fmt.Println("Example 2: Database Bulk Operations (Throughput Optimization)")
	fmt.Println(strings.Repeat("=", 70))

	fmt.Println("\nScenario: Inserting 50 database records")
	fmt.Println("Real-world: Bulk INSERT 10-100x faster than individual INSERTs")
	fmt.Println("Trade-off: Small latency increase, huge throughput gain\n")

	agent := NewMockDatabaseAgent()

	// Configure batching for database: medium batches, short wait time
	config := middleware.BatchingConfig{
		MaxBatchSize: 10,                 // Batch up to 10 records
		MaxWaitTime:  50 * time.Millisecond, // Wait max 50ms
		MaxQueueSize: 200,
	}

	batchingAgent := middleware.NewBatchingDecorator(agent, config)

	// Simulate 50 concurrent database inserts
	fmt.Println("Inserting 50 user records...")
	start := time.Now()

	ctx := context.Background()
	var wg sync.WaitGroup
	results := make([]*agenkit.Message, 50)
	errors := make([]error, 50)

	for i := 0; i < 50; i++ {
		wg.Add(1)
		go func(idx int) {
			defer wg.Done()
			msg := agenkit.NewMessage("user", fmt.Sprintf("user_%d@example.com", idx+1))
			result, err := batchingAgent.Process(ctx, msg)
			results[idx] = result
			errors[idx] = err
		}(i)
	}

	wg.Wait()
	elapsed := time.Since(start)

	fmt.Printf("✓ Completed in %.2fs\n", elapsed.Seconds())
	fmt.Printf("   Records inserted: %d\n", agent.recordsInserted.Load())
	fmt.Printf("   DB calls made: %d\n", agent.dbCalls.Load())

	// Show batching efficiency
	metrics := batchingAgent.Metrics()
	dbCalls := float64(agent.dbCalls.Load())
	if dbCalls > 0 {
		fmt.Println("\n📊 Batching Metrics:")
		fmt.Printf("   Total batches: %d\n", metrics.TotalBatches)
		fmt.Printf("   Avg batch size: %.1f\n", metrics.AvgBatchSize())
		fmt.Printf("   Efficiency gain: ~%.1fx fewer DB round-trips\n", 50.0/dbCalls)
		fmt.Printf("   ⚡ Throughput: %.0f records/sec\n", float64(agent.recordsInserted.Load())/elapsed.Seconds())
	}

	batchingAgent.Shutdown()
}

// Example 3: High-Throughput Analytics
//
// Demonstrates batching for high-volume event processing.
// Real streaming systems process millions of events per second.
func example3HighThroughputAnalytics() {
	fmt.Println("\n" + strings.Repeat("=", 70))
	fmt.Println("Example 3: High-Throughput Analytics (Stream Processing)")
	fmt.Println(strings.Repeat("=", 70))

	fmt.Println("\nScenario: Processing 100 analytics events")
	fmt.Println("Real-world: Data pipelines batch events for warehouse writes")
	fmt.Println("Trade-off: Slight delay acceptable for massive throughput\n")

	agent := NewMockAnalyticsAgent()

	// Configure batching for analytics: aggressive batching
	config := middleware.BatchingConfig{
		MaxBatchSize: 20,                 // Large batches for throughput
		MaxWaitTime:  50 * time.Millisecond, // Quick batching
		MaxQueueSize: 500,
	}

	batchingAgent := middleware.NewBatchingDecorator(agent, config)

	// Simulate 100 concurrent analytics events
	fmt.Println("Processing 100 clickstream events...")
	start := time.Now()

	ctx := context.Background()
	var wg sync.WaitGroup
	results := make([]*agenkit.Message, 100)
	errors := make([]error, 100)

	for i := 0; i < 100; i++ {
		wg.Add(1)
		go func(idx int) {
			defer wg.Done()
			msg := agenkit.NewMessage("user", fmt.Sprintf("click_event_%d", idx+1))
			result, err := batchingAgent.Process(ctx, msg)
			results[idx] = result
			errors[idx] = err
		}(i)
	}

	wg.Wait()
	elapsed := time.Since(start)

	fmt.Printf("✓ Completed in %.2fs\n", elapsed.Seconds())
	fmt.Printf("   Events processed: %d\n", agent.eventsProcessed.Load())

	// Show batching performance
	metrics := batchingAgent.Metrics()
	fmt.Println("\n📊 Batching Metrics:")
	fmt.Printf("   Total batches: %d\n", metrics.TotalBatches)
	fmt.Printf("   Avg batch size: %.1f\n", metrics.AvgBatchSize())
	fmt.Printf("   Avg wait time: %.1fms\n", float64(metrics.AvgWaitTime().Milliseconds()))
	fmt.Printf("   ⚡ Throughput: %.0f events/sec\n", float64(agent.eventsProcessed.Load())/elapsed.Seconds())

	batchingAgent.Shutdown()
}

// PartialFailAgent is an agent that fails on specific inputs
type PartialFailAgent struct {
	successCount atomic.Int32
	failureCount atomic.Int32
}

func NewPartialFailAgent() *PartialFailAgent {
	return &PartialFailAgent{}
}

func (a *PartialFailAgent) Name() string {
	return "partial-fail-agent"
}

func (a *PartialFailAgent) Capabilities() []string {
	return []string{}
}

func (a *PartialFailAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	time.Sleep(10 * time.Millisecond)

	// Fail on messages containing "fail"
	if strings.Contains(strings.ToLower(message.Content), "fail") {
		a.failureCount.Add(1)
		return nil, fmt.Errorf("processing failed for: %s", message.Content)
	}

	a.successCount.Add(1)
	return agenkit.NewMessage("assistant", fmt.Sprintf("Success: %s", message.Content)), nil
}

// Example 4: Handling Partial Failures
//
// Demonstrates how batching handles individual request failures
// without affecting other requests in the batch.
func example4PartialFailures() {
	fmt.Println("\n" + strings.Repeat("=", 70))
	fmt.Println("Example 4: Partial Failure Handling")
	fmt.Println(strings.Repeat("=", 70))

	fmt.Println("\nScenario: Batch with some failing requests")
	fmt.Println("Real-world: Individual requests can fail independently")
	fmt.Println("Batching isolates failures - only failed requests error out\n")

	agent := NewPartialFailAgent()
	config := middleware.BatchingConfig{
		MaxBatchSize: 5,
		MaxWaitTime:  50 * time.Millisecond,
		MaxQueueSize: 100,
	}
	batchingAgent := middleware.NewBatchingDecorator(agent, config)

	// Mix of successful and failing requests
	messages := []string{
		"request_1",
		"FAIL_2",
		"request_3",
		"FAIL_4",
		"request_5",
	}

	fmt.Println("Processing batch with mixed success/failure...")

	ctx := context.Background()
	var wg sync.WaitGroup
	results := make([]interface{}, len(messages))

	for i, content := range messages {
		wg.Add(1)
		go func(idx int, msgContent string) {
			defer wg.Done()
			msg := agenkit.NewMessage("user", msgContent)
			result, err := batchingAgent.Process(ctx, msg)
			if err != nil {
				results[idx] = err
			} else {
				results[idx] = result
			}
		}(i, content)
	}

	wg.Wait()

	// Show results
	fmt.Println("\nResults:")
	for i, result := range results {
		switch v := result.(type) {
		case error:
			fmt.Printf("   ❌ Request %d: %v\n", i+1, v)
		case *agenkit.Message:
			fmt.Printf("   ✓ Request %d: %s\n", i+1, v.Content)
		}
	}

	metrics := batchingAgent.Metrics()
	fmt.Println("\n📊 Batch Metrics:")
	fmt.Printf("   Partial batches: %d\n", metrics.PartialBatches)
	fmt.Println("   ℹ️  Only failed requests raised errors - others succeeded")

	batchingAgent.Shutdown()
}

// Example 5: Configuration Tuning
//
// Demonstrates the impact of different configuration settings
// on latency and throughput.
func example5ConfigurationTuning() {
	fmt.Println("\n" + strings.Repeat("=", 70))
	fmt.Println("Example 5: Configuration Tuning (Latency vs Throughput)")
	fmt.Println(strings.Repeat("=", 70))

	fmt.Println("\nComparing different batching configurations:\n")

	// Test configurations
	type configTest struct {
		name   string
		config middleware.BatchingConfig
	}

	configs := []configTest{
		{
			name: "Aggressive (low latency)",
			config: middleware.BatchingConfig{
				MaxBatchSize: 3,
				MaxWaitTime:  10 * time.Millisecond, // 10ms
				MaxQueueSize: 100,
			},
		},
		{
			name: "Balanced (default)",
			config: middleware.BatchingConfig{
				MaxBatchSize: 10,
				MaxWaitTime:  100 * time.Millisecond, // 100ms
				MaxQueueSize: 100,
			},
		},
		{
			name: "Throughput-optimized",
			config: middleware.BatchingConfig{
				MaxBatchSize: 20,
				MaxWaitTime:  200 * time.Millisecond, // 200ms
				MaxQueueSize: 100,
			},
		},
	}

	for _, test := range configs {
		agent := NewMockAnalyticsAgent()
		batchingAgent := middleware.NewBatchingDecorator(agent, test.config)

		// Send 30 requests
		start := time.Now()
		ctx := context.Background()
		var wg sync.WaitGroup

		for i := 0; i < 30; i++ {
			wg.Add(1)
			go func(idx int) {
				defer wg.Done()
				msg := agenkit.NewMessage("user", fmt.Sprintf("event_%d", idx))
				batchingAgent.Process(ctx, msg)
			}(i)
		}

		wg.Wait()
		elapsed := time.Since(start)

		metrics := batchingAgent.Metrics()
		fmt.Printf("%s:\n", test.name)
		fmt.Printf("   Total time: %.3fs\n", elapsed.Seconds())
		fmt.Printf("   Batches: %d\n", metrics.TotalBatches)
		fmt.Printf("   Avg batch: %.1f requests\n", metrics.AvgBatchSize())
		fmt.Printf("   Avg wait: %.1fms\n", float64(metrics.AvgWaitTime().Milliseconds()))
		fmt.Printf("   Throughput: %.0f req/sec\n\n", 30.0/elapsed.Seconds())

		batchingAgent.Shutdown()
	}
}

func main() {
	fmt.Println("\n" + strings.Repeat("=", 70))
	fmt.Println("BATCHING MIDDLEWARE EXAMPLES")
	fmt.Println(strings.Repeat("=", 70))
	fmt.Println("\nBatching collects concurrent requests and processes them together")
	fmt.Println("to improve throughput at the cost of added latency.")
	fmt.Println("\nKey benefits: Lower costs, better throughput, fewer round-trips")
	fmt.Println("Key trade-off: Adds wait time (tune max_wait_time to control)")

	// Run all examples
	example1LLMBatchProcessing()

	fmt.Print("\nPress Enter to continue...")
	fmt.Scanln()

	example2DatabaseBulkOperations()

	fmt.Print("\nPress Enter to continue...")
	fmt.Scanln()

	example3HighThroughputAnalytics()

	fmt.Print("\nPress Enter to continue...")
	fmt.Scanln()

	example4PartialFailures()

	fmt.Print("\nPress Enter to continue...")
	fmt.Scanln()

	example5ConfigurationTuning()

	fmt.Println("\n" + strings.Repeat("=", 70))
	fmt.Println("BATCHING BEST PRACTICES")
	fmt.Println(strings.Repeat("=", 70))
	fmt.Println(`
1. Choose batch size based on your use case:
   - LLM APIs: 5-50 (API limits vary)
   - Database: 10-100 (balance transaction size)
   - Analytics: 100-1000 (maximize throughput)

2. Tune wait time for your latency requirements:
   - Interactive: 10-50ms (responsive UX)
   - Background: 100-500ms (balanced)
   - Batch jobs: 1-5s (maximize efficiency)

3. Handle partial failures gracefully:
   - Check error returns for each goroutine
   - Monitor metrics.PartialBatches to track health
   - Log failures for debugging

4. Monitor metrics:
   - avg_batch_size: Should be close to max_batch_size
   - avg_wait_time: Should match your SLA
   - partial_batches: Should be low

5. Set queue limits to prevent memory issues:
   - Set max_queue_size based on traffic patterns
   - Monitor queue depth in production
   - Use backpressure signals upstream if needed

6. Go-specific considerations:
   - Use sync.WaitGroup for coordinating goroutines
   - Use atomic operations for thread-safe counters
   - Channel-based batching works naturally with Go's concurrency model
`)
}
