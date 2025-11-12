package middleware

import (
	"context"
	"fmt"
	"sync"
	"testing"
	"time"

	"github.com/agenkit/agenkit-go/agenkit"
)

// testAgent is a simple test agent
type testAgent struct {
	delay       time.Duration
	shouldFail  bool
	callCount   int
	mu          sync.Mutex
}

func newTestAgent(delay time.Duration, shouldFail bool) *testAgent {
	return &testAgent{
		delay:      delay,
		shouldFail: shouldFail,
	}
}

func (a *testAgent) Name() string {
	return "test"
}

func (a *testAgent) Capabilities() []string {
	return []string{}
}

func (a *testAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	a.mu.Lock()
	a.callCount++
	a.mu.Unlock()

	time.Sleep(a.delay)

	if a.shouldFail {
		return nil, fmt.Errorf("agent failed processing: %s", message.Content)
	}

	return &agenkit.Message{
		Role:    "agent",
		Content: fmt.Sprintf("Processed: %s", message.Content),
	}, nil
}

func (a *testAgent) CallCount() int {
	a.mu.Lock()
	defer a.mu.Unlock()
	return a.callCount
}

// TestBatchingConfig tests configuration validation
func TestBatchingConfig(t *testing.T) {
	t.Run("DefaultConfig", func(t *testing.T) {
		config := DefaultBatchingConfig()
		if config.MaxBatchSize != 10 {
			t.Errorf("Expected MaxBatchSize=10, got %d", config.MaxBatchSize)
		}
		if config.MaxWaitTime != 100*time.Millisecond {
			t.Errorf("Expected MaxWaitTime=100ms, got %v", config.MaxWaitTime)
		}
		if config.MaxQueueSize != 1000 {
			t.Errorf("Expected MaxQueueSize=1000, got %d", config.MaxQueueSize)
		}
	})

	t.Run("CustomConfig", func(t *testing.T) {
		config := BatchingConfig{
			MaxBatchSize: 5,
			MaxWaitTime:  50 * time.Millisecond,
			MaxQueueSize: 100,
		}
		if config.MaxBatchSize != 5 {
			t.Errorf("Expected MaxBatchSize=5, got %d", config.MaxBatchSize)
		}
		if config.MaxWaitTime != 50*time.Millisecond {
			t.Errorf("Expected MaxWaitTime=50ms, got %v", config.MaxWaitTime)
		}
		if config.MaxQueueSize != 100 {
			t.Errorf("Expected MaxQueueSize=100, got %d", config.MaxQueueSize)
		}
	})
}

// TestBatchingMetrics tests metrics functionality
func TestBatchingMetrics(t *testing.T) {
	t.Run("DefaultMetrics", func(t *testing.T) {
		metrics := NewBatchingMetrics()
		if metrics.TotalRequests != 0 {
			t.Errorf("Expected TotalRequests=0, got %d", metrics.TotalRequests)
		}
		if metrics.TotalBatches != 0 {
			t.Errorf("Expected TotalBatches=0, got %d", metrics.TotalBatches)
		}
		if metrics.SuccessfulBatches != 0 {
			t.Errorf("Expected SuccessfulBatches=0, got %d", metrics.SuccessfulBatches)
		}
	})

	t.Run("AvgBatchSizeEmpty", func(t *testing.T) {
		metrics := NewBatchingMetrics()
		if avg := metrics.AvgBatchSize(); avg != 0.0 {
			t.Errorf("Expected AvgBatchSize=0.0, got %f", avg)
		}
	})

	t.Run("AvgBatchSize", func(t *testing.T) {
		metrics := NewBatchingMetrics()
		metrics.TotalRequests = 10
		metrics.TotalBatches = 4
		if avg := metrics.AvgBatchSize(); avg != 2.5 {
			t.Errorf("Expected AvgBatchSize=2.5, got %f", avg)
		}
	})

	t.Run("AvgWaitTimeEmpty", func(t *testing.T) {
		metrics := NewBatchingMetrics()
		if avg := metrics.AvgWaitTime(); avg != 0 {
			t.Errorf("Expected AvgWaitTime=0, got %v", avg)
		}
	})

	t.Run("AvgWaitTime", func(t *testing.T) {
		metrics := NewBatchingMetrics()
		metrics.TotalRequests = 10
		metrics.TotalWaitTime = 1 * time.Second
		expected := 100 * time.Millisecond
		if avg := metrics.AvgWaitTime(); avg != expected {
			t.Errorf("Expected AvgWaitTime=%v, got %v", expected, avg)
		}
	})
}

// TestBasicBatching tests basic batching functionality
func TestBasicBatching(t *testing.T) {
	agent := newTestAgent(10*time.Millisecond, false)
	config := BatchingConfig{
		MaxBatchSize: 3,
		MaxWaitTime:  100 * time.Millisecond,
		MaxQueueSize: 100,
	}
	batchingAgent := NewBatchingDecorator(agent, config)
	defer batchingAgent.Shutdown()

	// Send 5 concurrent requests
	var wg sync.WaitGroup
	results := make([]*agenkit.Message, 5)
	errors := make([]error, 5)

	for i := 0; i < 5; i++ {
		wg.Add(1)
		go func(idx int) {
			defer wg.Done()
			msg := &agenkit.Message{
				Role:    "user",
				Content: fmt.Sprintf("msg%d", idx),
			}
			result, err := batchingAgent.Process(context.Background(), msg)
			results[idx] = result
			errors[idx] = err
		}(i)
	}

	wg.Wait()

	// Verify results
	for i, result := range results {
		if errors[i] != nil {
			t.Errorf("Request %d failed: %v", i, errors[i])
		}
		if result == nil {
			t.Errorf("Request %d got nil result", i)
			continue
		}
		expected := fmt.Sprintf("Processed: msg%d", i)
		if result.Content != expected {
			t.Errorf("Request %d: expected %q, got %q", i, expected, result.Content)
		}
	}

	// Verify metrics
	metrics := batchingAgent.Metrics()
	if metrics.TotalRequests != 5 {
		t.Errorf("Expected TotalRequests=5, got %d", metrics.TotalRequests)
	}
	if metrics.TotalBatches != 2 {
		t.Errorf("Expected TotalBatches=2 (3+2), got %d", metrics.TotalBatches)
	}
	if metrics.SuccessfulBatches != 2 {
		t.Errorf("Expected SuccessfulBatches=2, got %d", metrics.SuccessfulBatches)
	}
	if avg := metrics.AvgBatchSize(); avg != 2.5 {
		t.Errorf("Expected AvgBatchSize=2.5, got %f", avg)
	}
}

// TestBatchSizeThreshold tests that batch triggers on max batch size
func TestBatchSizeThreshold(t *testing.T) {
	agent := newTestAgent(10*time.Millisecond, false)
	config := BatchingConfig{
		MaxBatchSize: 3,
		MaxWaitTime:  1 * time.Second, // Long timeout
		MaxQueueSize: 100,
	}
	batchingAgent := NewBatchingDecorator(agent, config)
	defer batchingAgent.Shutdown()

	// Send exactly max_batch_size requests
	var wg sync.WaitGroup
	results := make([]*agenkit.Message, 3)
	errors := make([]error, 3)

	start := time.Now()
	for i := 0; i < 3; i++ {
		wg.Add(1)
		go func(idx int) {
			defer wg.Done()
			msg := &agenkit.Message{
				Role:    "user",
				Content: fmt.Sprintf("msg%d", idx),
			}
			result, err := batchingAgent.Process(context.Background(), msg)
			results[idx] = result
			errors[idx] = err
		}(i)
	}

	wg.Wait()
	elapsed := time.Since(start)

	// Should process quickly (not wait for timeout)
	if elapsed > 500*time.Millisecond {
		t.Errorf("Batch took too long: %v (expected < 500ms)", elapsed)
	}

	// Verify all completed
	for i := range results {
		if errors[i] != nil {
			t.Errorf("Request %d failed: %v", i, errors[i])
		}
	}

	// Should be 1 batch
	metrics := batchingAgent.Metrics()
	if metrics.TotalBatches != 1 {
		t.Errorf("Expected TotalBatches=1, got %d", metrics.TotalBatches)
	}
	if metrics.TotalRequests != 3 {
		t.Errorf("Expected TotalRequests=3, got %d", metrics.TotalRequests)
	}
}

// TestWaitTimeThreshold tests that batch triggers on max wait time
func TestWaitTimeThreshold(t *testing.T) {
	agent := newTestAgent(10*time.Millisecond, false)
	config := BatchingConfig{
		MaxBatchSize: 10, // Large batch size
		MaxWaitTime:  50 * time.Millisecond,
		MaxQueueSize: 100,
	}
	batchingAgent := NewBatchingDecorator(agent, config)
	defer batchingAgent.Shutdown()

	// Send fewer requests than batch size
	var wg sync.WaitGroup
	results := make([]*agenkit.Message, 3)
	errors := make([]error, 3)

	start := time.Now()
	for i := 0; i < 3; i++ {
		wg.Add(1)
		go func(idx int) {
			defer wg.Done()
			msg := &agenkit.Message{
				Role:    "user",
				Content: fmt.Sprintf("msg%d", idx),
			}
			result, err := batchingAgent.Process(context.Background(), msg)
			results[idx] = result
			errors[idx] = err
		}(i)
	}

	wg.Wait()
	elapsed := time.Since(start)

	// Should wait for timeout (plus processing time)
	if elapsed < 40*time.Millisecond || elapsed > 150*time.Millisecond {
		t.Errorf("Batch timing unexpected: %v (expected 40-150ms)", elapsed)
	}

	// Verify all completed
	for i := range results {
		if errors[i] != nil {
			t.Errorf("Request %d failed: %v", i, errors[i])
		}
	}

	// Should be 1 batch triggered by timeout
	metrics := batchingAgent.Metrics()
	if metrics.TotalBatches != 1 {
		t.Errorf("Expected TotalBatches=1, got %d", metrics.TotalBatches)
	}
	if metrics.TotalRequests != 3 {
		t.Errorf("Expected TotalRequests=3, got %d", metrics.TotalRequests)
	}
}

// TestPartialFailure tests handling of partial batch failures
func TestPartialFailure(t *testing.T) {
	// Create agent that fails on specific messages
	agent := &partialFailAgent{}
	config := BatchingConfig{
		MaxBatchSize: 5,
		MaxWaitTime:  50 * time.Millisecond,
		MaxQueueSize: 100,
	}
	batchingAgent := NewBatchingDecorator(agent, config)
	defer batchingAgent.Shutdown()

	// Send mix of success and failure messages
	messages := []string{"msg0", "fail1", "msg2", "fail3", "msg4"}
	var wg sync.WaitGroup
	results := make([]*agenkit.Message, 5)
	errors := make([]error, 5)

	for i, content := range messages {
		wg.Add(1)
		go func(idx int, msgContent string) {
			defer wg.Done()
			msg := &agenkit.Message{
				Role:    "user",
				Content: msgContent,
			}
			result, err := batchingAgent.Process(context.Background(), msg)
			results[idx] = result
			errors[idx] = err
		}(i, content)
	}

	wg.Wait()

	// Verify partial success/failure
	if errors[0] != nil {
		t.Errorf("Request 0 should succeed, got error: %v", errors[0])
	}
	if errors[1] == nil {
		t.Error("Request 1 should fail, got no error")
	}
	if errors[2] != nil {
		t.Errorf("Request 2 should succeed, got error: %v", errors[2])
	}
	if errors[3] == nil {
		t.Error("Request 3 should fail, got no error")
	}
	if errors[4] != nil {
		t.Errorf("Request 4 should succeed, got error: %v", errors[4])
	}

	// Verify metrics show partial batch
	metrics := batchingAgent.Metrics()
	if metrics.TotalBatches != 1 {
		t.Errorf("Expected TotalBatches=1, got %d", metrics.TotalBatches)
	}
	if metrics.PartialBatches != 1 {
		t.Errorf("Expected PartialBatches=1, got %d", metrics.PartialBatches)
	}
	if metrics.SuccessfulBatches != 0 {
		t.Errorf("Expected SuccessfulBatches=0, got %d", metrics.SuccessfulBatches)
	}
	if metrics.FailedBatches != 0 {
		t.Errorf("Expected FailedBatches=0, got %d", metrics.FailedBatches)
	}
}

// TestAllFailures tests batch with all failures
func TestAllFailures(t *testing.T) {
	agent := newTestAgent(10*time.Millisecond, true) // All fail
	config := BatchingConfig{
		MaxBatchSize: 3,
		MaxWaitTime:  50 * time.Millisecond,
		MaxQueueSize: 100,
	}
	batchingAgent := NewBatchingDecorator(agent, config)
	defer batchingAgent.Shutdown()

	// Send requests
	var wg sync.WaitGroup
	results := make([]*agenkit.Message, 3)
	errors := make([]error, 3)

	for i := 0; i < 3; i++ {
		wg.Add(1)
		go func(idx int) {
			defer wg.Done()
			msg := &agenkit.Message{
				Role:    "user",
				Content: fmt.Sprintf("msg%d", idx),
			}
			result, err := batchingAgent.Process(context.Background(), msg)
			results[idx] = result
			errors[idx] = err
		}(i)
	}

	wg.Wait()

	// All should fail
	for i, err := range errors {
		if err == nil {
			t.Errorf("Request %d should fail, got no error", i)
		}
	}

	// Verify metrics
	metrics := batchingAgent.Metrics()
	if metrics.TotalBatches != 1 {
		t.Errorf("Expected TotalBatches=1, got %d", metrics.TotalBatches)
	}
	if metrics.FailedBatches != 1 {
		t.Errorf("Expected FailedBatches=1, got %d", metrics.FailedBatches)
	}
	if metrics.SuccessfulBatches != 0 {
		t.Errorf("Expected SuccessfulBatches=0, got %d", metrics.SuccessfulBatches)
	}
	if metrics.PartialBatches != 0 {
		t.Errorf("Expected PartialBatches=0, got %d", metrics.PartialBatches)
	}
}

// TestSequentialBatches tests multiple sequential batches
func TestSequentialBatches(t *testing.T) {
	agent := newTestAgent(10*time.Millisecond, false)
	config := BatchingConfig{
		MaxBatchSize: 2,
		MaxWaitTime:  50 * time.Millisecond,
		MaxQueueSize: 100,
	}
	batchingAgent := NewBatchingDecorator(agent, config)
	defer batchingAgent.Shutdown()

	// Send first batch
	var wg1 sync.WaitGroup
	for i := 0; i < 2; i++ {
		wg1.Add(1)
		go func(idx int) {
			defer wg1.Done()
			msg := &agenkit.Message{
				Role:    "user",
				Content: fmt.Sprintf("batch1_msg%d", idx),
			}
			_, err := batchingAgent.Process(context.Background(), msg)
			if err != nil {
				t.Errorf("Batch 1 request %d failed: %v", idx, err)
			}
		}(i)
	}
	wg1.Wait()

	// Send second batch
	var wg2 sync.WaitGroup
	for i := 0; i < 2; i++ {
		wg2.Add(1)
		go func(idx int) {
			defer wg2.Done()
			msg := &agenkit.Message{
				Role:    "user",
				Content: fmt.Sprintf("batch2_msg%d", idx),
			}
			_, err := batchingAgent.Process(context.Background(), msg)
			if err != nil {
				t.Errorf("Batch 2 request %d failed: %v", idx, err)
			}
		}(i)
	}
	wg2.Wait()

	// Verify metrics
	metrics := batchingAgent.Metrics()
	if metrics.TotalBatches != 2 {
		t.Errorf("Expected TotalBatches=2, got %d", metrics.TotalBatches)
	}
	if metrics.TotalRequests != 4 {
		t.Errorf("Expected TotalRequests=4, got %d", metrics.TotalRequests)
	}
	if metrics.SuccessfulBatches != 2 {
		t.Errorf("Expected SuccessfulBatches=2, got %d", metrics.SuccessfulBatches)
	}
}

// TestMinMaxBatchSize tests tracking of min and max batch sizes
func TestMinMaxBatchSize(t *testing.T) {
	agent := newTestAgent(10*time.Millisecond, false)
	config := BatchingConfig{
		MaxBatchSize: 10,
		MaxWaitTime:  50 * time.Millisecond,
		MaxQueueSize: 100,
	}
	batchingAgent := NewBatchingDecorator(agent, config)
	defer batchingAgent.Shutdown()

	// Batch 1: 1 message
	msg := &agenkit.Message{Role: "user", Content: "single"}
	_, err := batchingAgent.Process(context.Background(), msg)
	if err != nil {
		t.Fatalf("Batch 1 failed: %v", err)
	}

	time.Sleep(100 * time.Millisecond) // Ensure separate batches

	// Batch 2: 5 messages
	var wg sync.WaitGroup
	for i := 0; i < 5; i++ {
		wg.Add(1)
		go func(idx int) {
			defer wg.Done()
			msg := &agenkit.Message{
				Role:    "user",
				Content: fmt.Sprintf("msg%d", idx),
			}
			_, _ = batchingAgent.Process(context.Background(), msg)
		}(i)
	}
	wg.Wait()

	time.Sleep(100 * time.Millisecond)

	// Batch 3: 3 messages
	for i := 0; i < 3; i++ {
		wg.Add(1)
		go func(idx int) {
			defer wg.Done()
			msg := &agenkit.Message{
				Role:    "user",
				Content: fmt.Sprintf("msg%d", idx),
			}
			_, _ = batchingAgent.Process(context.Background(), msg)
		}(i)
	}
	wg.Wait()

	// Verify min/max tracking
	metrics := batchingAgent.Metrics()
	if metrics.MinBatchSize == nil || *metrics.MinBatchSize != 1 {
		t.Errorf("Expected MinBatchSize=1, got %v", metrics.MinBatchSize)
	}
	if metrics.MaxBatchSize == nil || *metrics.MaxBatchSize != 5 {
		t.Errorf("Expected MaxBatchSize=5, got %v", metrics.MaxBatchSize)
	}
	if metrics.TotalBatches != 3 {
		t.Errorf("Expected TotalBatches=3, got %d", metrics.TotalBatches)
	}
}

// TestProperties tests that agent properties are proxied correctly
func TestProperties(t *testing.T) {
	agent := newTestAgent(10*time.Millisecond, false)
	config := DefaultBatchingConfig()
	batchingAgent := NewBatchingDecorator(agent, config)
	defer batchingAgent.Shutdown()

	if name := batchingAgent.Name(); name != "test" {
		t.Errorf("Expected Name()='test', got %q", name)
	}
	if caps := batchingAgent.Capabilities(); len(caps) != 0 {
		t.Errorf("Expected empty Capabilities(), got %v", caps)
	}
}

// TestHighConcurrency tests batching with high concurrency
func TestHighConcurrency(t *testing.T) {
	agent := newTestAgent(10*time.Millisecond, false)
	config := BatchingConfig{
		MaxBatchSize: 10,
		MaxWaitTime:  50 * time.Millisecond,
		MaxQueueSize: 100,
	}
	batchingAgent := NewBatchingDecorator(agent, config)
	defer batchingAgent.Shutdown()

	// Send 50 concurrent requests
	const numRequests = 50
	var wg sync.WaitGroup
	errors := make([]error, numRequests)

	for i := 0; i < numRequests; i++ {
		wg.Add(1)
		go func(idx int) {
			defer wg.Done()
			msg := &agenkit.Message{
				Role:    "user",
				Content: fmt.Sprintf("msg%d", idx),
			}
			_, err := batchingAgent.Process(context.Background(), msg)
			errors[idx] = err
		}(i)
	}

	wg.Wait()

	// Verify all completed
	for i, err := range errors {
		if err != nil {
			t.Errorf("Request %d failed: %v", i, err)
		}
	}

	// Verify metrics
	metrics := batchingAgent.Metrics()
	if metrics.TotalRequests != numRequests {
		t.Errorf("Expected TotalRequests=%d, got %d", numRequests, metrics.TotalRequests)
	}
	if metrics.TotalBatches < 5 {
		t.Errorf("Expected at least 5 batches, got %d", metrics.TotalBatches)
	}
	if metrics.SuccessfulBatches < 5 {
		t.Errorf("Expected at least 5 successful batches, got %d", metrics.SuccessfulBatches)
	}
}

// TestContextCancellation tests that context cancellation is respected
func TestContextCancellation(t *testing.T) {
	agent := newTestAgent(10*time.Millisecond, false)
	config := BatchingConfig{
		MaxBatchSize: 10,
		MaxWaitTime:  1 * time.Second,
		MaxQueueSize: 100,
	}
	batchingAgent := NewBatchingDecorator(agent, config)
	defer batchingAgent.Shutdown()

	// Create cancellable context
	ctx, cancel := context.WithCancel(context.Background())

	// Start request in goroutine
	done := make(chan error, 1)
	go func() {
		msg := &agenkit.Message{Role: "user", Content: "test"}
		_, err := batchingAgent.Process(ctx, msg)
		done <- err
	}()

	// Cancel context before batch processes
	time.Sleep(10 * time.Millisecond)
	cancel()

	// Should get cancellation error
	select {
	case err := <-done:
		if err == nil {
			t.Error("Expected cancellation error, got nil")
		}
	case <-time.After(1 * time.Second):
		t.Error("Request did not complete after cancellation")
	}
}

// partialFailAgent fails on messages containing "fail"
type partialFailAgent struct{}

func (a *partialFailAgent) Name() string {
	return "partial_fail"
}

func (a *partialFailAgent) Capabilities() []string {
	return []string{}
}

func (a *partialFailAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	time.Sleep(10 * time.Millisecond)
	if len(message.Content) >= 4 && message.Content[:4] == "fail" {
		return nil, fmt.Errorf("Failed: %s", message.Content)
	}
	return &agenkit.Message{
		Role:    "agent",
		Content: fmt.Sprintf("Success: %s", message.Content),
	}, nil
}
