// Package middleware provides reusable middleware for agents.
package middleware

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/agenkit/agenkit-go/agenkit"
)

// BatchingConfig configures batching behavior.
type BatchingConfig struct {
	// MaxBatchSize is the maximum number of requests to batch together.
	// When this many requests are queued, they are processed immediately.
	// Default: 10
	MaxBatchSize int

	// MaxWaitTime is the maximum time to wait for a batch to fill.
	// If this time elapses, the batch is processed even if not full.
	// Default: 100ms
	MaxWaitTime time.Duration

	// MaxQueueSize is the maximum number of pending requests.
	// When full, new requests will block or fail.
	// Default: 1000
	MaxQueueSize int
}

// DefaultBatchingConfig returns a batching config with sensible defaults.
func DefaultBatchingConfig() BatchingConfig {
	return BatchingConfig{
		MaxBatchSize: 10,
		MaxWaitTime:  100 * time.Millisecond,
		MaxQueueSize: 1000,
	}
}

// BatchingMetrics tracks batching middleware metrics.
type BatchingMetrics struct {
	mu                sync.RWMutex
	TotalRequests     int64
	TotalBatches      int64
	SuccessfulBatches int64
	FailedBatches     int64
	PartialBatches    int64 // Batches with some failures
	TotalWaitTime     time.Duration
	MinBatchSize      *int
	MaxBatchSize      *int
}

// NewBatchingMetrics creates a new metrics instance.
func NewBatchingMetrics() *BatchingMetrics {
	return &BatchingMetrics{}
}

// RecordBatch records a batch execution.
func (m *BatchingMetrics) RecordBatch(batchSize int, successes, failures int, totalWait time.Duration) {
	m.mu.Lock()
	defer m.mu.Unlock()

	m.TotalRequests += int64(batchSize)
	m.TotalBatches++
	m.TotalWaitTime += totalWait

	// Update batch size stats
	if m.MinBatchSize == nil || batchSize < *m.MinBatchSize {
		size := batchSize
		m.MinBatchSize = &size
	}
	if m.MaxBatchSize == nil || batchSize > *m.MaxBatchSize {
		size := batchSize
		m.MaxBatchSize = &size
	}

	// Update success/failure stats
	if failures == 0 {
		m.SuccessfulBatches++
	} else if successes == 0 {
		m.FailedBatches++
	} else {
		m.PartialBatches++
	}
}

// AvgBatchSize returns the average batch size.
func (m *BatchingMetrics) AvgBatchSize() float64 {
	m.mu.RLock()
	defer m.mu.RUnlock()

	if m.TotalBatches == 0 {
		return 0.0
	}
	return float64(m.TotalRequests) / float64(m.TotalBatches)
}

// AvgWaitTime returns the average wait time per request.
func (m *BatchingMetrics) AvgWaitTime() time.Duration {
	m.mu.RLock()
	defer m.mu.RUnlock()

	if m.TotalRequests == 0 {
		return 0
	}
	return m.TotalWaitTime / time.Duration(m.TotalRequests)
}

// batchRequest represents a single request in a batch.
type batchRequest struct {
	message    *agenkit.Message
	resultChan chan batchResult
	enqueuedAt time.Time
}

// batchResult holds the result of processing a request.
type batchResult struct {
	message *agenkit.Message
	err     error
}

// BatchingDecorator is an agent decorator that batches multiple requests.
type BatchingDecorator struct {
	agent   agenkit.Agent
	config  BatchingConfig
	metrics *BatchingMetrics

	queue    chan *batchRequest
	shutdown chan struct{}
	wg       sync.WaitGroup
}

// NewBatchingDecorator creates a new batching decorator.
func NewBatchingDecorator(agent agenkit.Agent, config BatchingConfig) *BatchingDecorator {
	d := &BatchingDecorator{
		agent:    agent,
		config:   config,
		metrics:  NewBatchingMetrics(),
		queue:    make(chan *batchRequest, config.MaxQueueSize),
		shutdown: make(chan struct{}),
	}

	// Start batch processor
	d.wg.Add(1)
	go d.batchProcessor()

	return d
}

// Name returns the name of the underlying agent.
func (d *BatchingDecorator) Name() string {
	return d.agent.Name()
}

// Capabilities returns the capabilities of the underlying agent.
func (d *BatchingDecorator) Capabilities() []string {
	return d.agent.Capabilities()
}

// Metrics returns the batching metrics.
func (d *BatchingDecorator) Metrics() *BatchingMetrics {
	return d.metrics
}

// Process processes a message with batching.
func (d *BatchingDecorator) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	// Create batch request with result channel
	req := &batchRequest{
		message:    message,
		resultChan: make(chan batchResult, 1),
		enqueuedAt: time.Now(),
	}

	// Enqueue request (blocks if queue is full)
	select {
	case d.queue <- req:
		// Successfully enqueued
	case <-ctx.Done():
		return nil, ctx.Err()
	case <-d.shutdown:
		return nil, fmt.Errorf("batching middleware shutting down")
	}

	// Wait for result
	select {
	case result := <-req.resultChan:
		return result.message, result.err
	case <-ctx.Done():
		return nil, ctx.Err()
	}
}

// batchProcessor runs in the background and processes batches.
func (d *BatchingDecorator) batchProcessor() {
	defer d.wg.Done()

	for {
		select {
		case <-d.shutdown:
			// Process any remaining requests
			d.processPendingBatches()
			return
		default:
			batch := d.collectBatch()
			if len(batch) > 0 {
				d.processBatch(batch)
			}
		}
	}
}

// collectBatch collects a batch of requests from the queue.
func (d *BatchingDecorator) collectBatch() []*batchRequest {
	batch := make([]*batchRequest, 0, d.config.MaxBatchSize)

	// Wait for first request with timeout
	timeout := time.After(100 * time.Millisecond) // Short timeout to check shutdown
	select {
	case req := <-d.queue:
		batch = append(batch, req)
	case <-timeout:
		return batch
	case <-d.shutdown:
		return batch
	}

	// Collect more requests until batch is full or timeout
	deadline := time.After(d.config.MaxWaitTime)
	for len(batch) < d.config.MaxBatchSize {
		select {
		case req := <-d.queue:
			batch = append(batch, req)
		case <-deadline:
			return batch
		case <-d.shutdown:
			return batch
		}
	}

	return batch
}

// processBatch processes a batch of requests.
func (d *BatchingDecorator) processBatch(batch []*batchRequest) {
	if len(batch) == 0 {
		return
	}

	batchSize := len(batch)
	now := time.Now()

	// Calculate total wait time for metrics
	var totalWait time.Duration
	for _, req := range batch {
		totalWait += now.Sub(req.enqueuedAt)
	}

	// Process all requests in parallel using goroutines
	var wg sync.WaitGroup
	results := make([]batchResult, batchSize)

	for i, req := range batch {
		wg.Add(1)
		go func(idx int, request *batchRequest) {
			defer wg.Done()

			// Process the request
			msg, err := d.agent.Process(context.Background(), request.message)
			results[idx] = batchResult{message: msg, err: err}
		}(i, req)
	}

	// Wait for all requests to complete
	wg.Wait()

	// Send results back to callers and count successes/failures
	successes := 0
	failures := 0
	for i, req := range batch {
		req.resultChan <- results[i]
		close(req.resultChan)

		if results[i].err == nil {
			successes++
		} else {
			failures++
		}
	}

	// Record metrics
	d.metrics.RecordBatch(batchSize, successes, failures, totalWait)
}

// processPendingBatches processes any remaining requests in the queue.
func (d *BatchingDecorator) processPendingBatches() {
	for {
		batch := make([]*batchRequest, 0, d.config.MaxBatchSize)

		// Drain queue without blocking
		for len(batch) < d.config.MaxBatchSize {
			select {
			case req := <-d.queue:
				batch = append(batch, req)
			default:
				// No more requests
				if len(batch) > 0 {
					d.processBatch(batch)
				}
				return
			}
		}

		if len(batch) > 0 {
			d.processBatch(batch)
		}
	}
}

// Shutdown gracefully shuts down the batching middleware.
func (d *BatchingDecorator) Shutdown() {
	close(d.shutdown)
	d.wg.Wait()
	close(d.queue)
}
