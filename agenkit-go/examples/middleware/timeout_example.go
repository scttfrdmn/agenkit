/*
Timeout Middleware Example

This example demonstrates WHY and HOW to use timeout middleware for preventing
long-running requests from blocking resources.

WHY USE TIMEOUT MIDDLEWARE?
---------------------------
- Prevent hung requests: Stop operations that take too long
- Resource protection: Free up resources from slow/stuck operations
- Predictable latency: Ensure requests complete within SLA requirements
- Fault isolation: Prevent one slow operation from affecting others

WHEN TO USE:
- External API calls with unpredictable response times
- LLM requests that may hang or take too long
- Network operations prone to hanging
- Any operation with strict latency requirements

WHEN NOT TO USE:
- Known long-running operations (use higher timeout or streaming instead)
- Operations where partial results aren't acceptable
- When timeout would cause data corruption
- Real-time systems where timeout handling adds overhead

TRADE-OFFS:
- Incomplete work: Operations are cancelled mid-execution
- Resource cleanup: May need to handle cleanup of timed-out operations
- Tuning required: Finding the right timeout value can be challenging
- False positives: Legitimate slow operations may be cancelled

Run with: go run agenkit-go/examples/middleware/timeout_example.go
*/

package main

import (
	"context"
	"fmt"
	"math/rand"
	"strings"
	"time"

	"github.com/agenkit/agenkit-go/agenkit"
	"github.com/agenkit/agenkit-go/middleware"
)

// SlowLLMAgent simulates an LLM that sometimes takes too long to respond
type SlowLLMAgent struct {
	name         string
	responseTime time.Duration
}

func NewSlowLLMAgent(responseTime time.Duration) *SlowLLMAgent {
	return &SlowLLMAgent{
		name:         "slow-llm",
		responseTime: responseTime,
	}
}

func (a *SlowLLMAgent) Name() string {
	return a.name
}

func (a *SlowLLMAgent) Capabilities() []string {
	return []string{"text-generation"}
}

func (a *SlowLLMAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	fmt.Printf("   LLM processing (will take %.1fs)...\n", a.responseTime.Seconds())

	// Simulate processing time, respecting context cancellation
	select {
	case <-time.After(a.responseTime):
		response := agenkit.NewMessage("assistant", fmt.Sprintf("Generated response for: %s", message.Content))
		response.Metadata = map[string]interface{}{
			"processing_time": a.responseTime.Seconds(),
		}
		return response, nil
	case <-ctx.Done():
		return nil, ctx.Err()
	}
}

// UnpredictableAgent simulates an agent with highly variable response times
type UnpredictableAgent struct {
	name      string
	callCount int
}

func NewUnpredictableAgent() *UnpredictableAgent {
	return &UnpredictableAgent{
		name: "unpredictable-agent",
	}
}

func (a *UnpredictableAgent) Name() string {
	return a.name
}

func (a *UnpredictableAgent) Capabilities() []string {
	return []string{"analysis"}
}

func (a *UnpredictableAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	a.callCount++

	// Sometimes fast, sometimes slow
	responseTimes := []time.Duration{
		100 * time.Millisecond,
		500 * time.Millisecond,
		3 * time.Second,
		10 * time.Second,
	}
	responseTime := responseTimes[rand.Intn(len(responseTimes))]

	fmt.Printf("   Request #%d: will take %.1fs\n", a.callCount, responseTime.Seconds())

	// Simulate processing time, respecting context cancellation
	select {
	case <-time.After(responseTime):
		response := agenkit.NewMessage("assistant", fmt.Sprintf("Analysis complete for: %s", message.Content))
		response.Metadata = map[string]interface{}{
			"response_time": responseTime.Seconds(),
		}
		return response, nil
	case <-ctx.Done():
		return nil, ctx.Err()
	}
}

// Example 1: Basic timeout protection
func example1BasicTimeout() {
	fmt.Println("\n=== Example 1: Basic Timeout ===")
	fmt.Println("Use case: Protect against slow LLM responses\n")

	// Create a slow agent (takes 2 seconds)
	agent := NewSlowLLMAgent(2 * time.Second)

	// Wrap with timeout middleware (1 second limit)
	timeoutConfig := middleware.TimeoutConfig{
		Timeout: 1 * time.Second,
	}
	timeoutAgent := middleware.NewTimeoutDecorator(agent, timeoutConfig)

	message := agenkit.NewMessage("user", "Explain quantum computing")

	fmt.Println("Sending request with 1s timeout...")
	ctx := context.Background()
	response, err := timeoutAgent.Process(ctx, message)

	if err != nil {
		fmt.Printf("❌ Request timed out: %v\n", err)
		fmt.Println("   The request was cancelled to prevent blocking")
	} else {
		fmt.Printf("✅ Response received: %s\n", response.Content)
	}
}

// Example 2: Fast requests complete successfully
func example2SuccessfulWithTimeout() {
	fmt.Println("\n=== Example 2: Fast Request Success ===")
	fmt.Println("Use case: Normal operations complete within timeout\n")

	// Create a fast agent (takes 0.5 seconds)
	agent := NewSlowLLMAgent(500 * time.Millisecond)

	// Wrap with timeout middleware (2 second limit)
	timeoutConfig := middleware.TimeoutConfig{
		Timeout: 2 * time.Second,
	}
	timeoutAgent := middleware.NewTimeoutDecorator(agent, timeoutConfig)

	message := agenkit.NewMessage("user", "Hello!")

	fmt.Println("Sending request with 2s timeout...")
	ctx := context.Background()
	response, err := timeoutAgent.Process(ctx, message)

	if err != nil {
		fmt.Printf("❌ Unexpected timeout: %v\n", err)
	} else {
		fmt.Printf("✅ Response received: %s\n", response.Content)
		if processingTime, ok := response.Metadata["processing_time"].(float64); ok {
			fmt.Printf("   Processing time: %.1fs\n", processingTime)
		}
	}
}

// Example 3: Handling multiple requests and tracking metrics
func example3MultipleRequestsWithMetrics() {
	fmt.Println("\n=== Example 3: Multiple Requests with Metrics ===")
	fmt.Println("Use case: Track success/timeout rates across many requests\n")

	agent := NewUnpredictableAgent()

	// Set timeout at 2 seconds
	timeoutConfig := middleware.TimeoutConfig{
		Timeout: 2 * time.Second,
	}
	timeoutAgent := middleware.NewTimeoutDecorator(agent, timeoutConfig)

	message := agenkit.NewMessage("user", "Analyze this data")

	// Send 5 requests
	fmt.Println("Sending 5 requests with unpredictable response times...")
	ctx := context.Background()
	for i := 0; i < 5; i++ {
		_, err := timeoutAgent.Process(ctx, message)
		if err != nil {
			fmt.Printf("   ❌ Request %d: Timeout\n", i+1)
		} else {
			fmt.Printf("   ✅ Request %d: Success\n", i+1)
		}
	}

	// Check metrics
	metrics := timeoutAgent.Metrics()
	fmt.Println("\n📊 Metrics Summary:")
	fmt.Printf("   Total requests: %d\n", metrics.TotalRequests)
	fmt.Printf("   Successful: %d\n", metrics.SuccessfulRequests)
	fmt.Printf("   Timed out: %d\n", metrics.TimedOutRequests)

	if metrics.TotalRequests > 0 {
		successRate := float64(metrics.SuccessfulRequests) / float64(metrics.TotalRequests) * 100
		fmt.Printf("   Success rate: %.1f%%\n", successRate)
	}

	if metrics.MinDuration != nil {
		fmt.Printf("   Min duration: %.3fs\n", metrics.MinDuration.Seconds())
		fmt.Printf("   Max duration: %.3fs\n", metrics.MaxDuration.Seconds())
		fmt.Printf("   Avg duration: %.3fs\n", metrics.AvgDuration().Seconds())
	}
}

// CachedResponseAgent provides fallback responses
type CachedResponseAgent struct {
	name string
}

func NewCachedResponseAgent() *CachedResponseAgent {
	return &CachedResponseAgent{
		name: "cached-response",
	}
}

func (a *CachedResponseAgent) Name() string {
	return a.name
}

func (a *CachedResponseAgent) Capabilities() []string {
	return []string{"text-generation"}
}

func (a *CachedResponseAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	response := agenkit.NewMessage("assistant", "[Cached response] I'm a general assistant. How can I help?")
	response.Metadata = map[string]interface{}{
		"source": "cache",
	}
	return response, nil
}

// Example 4: Implement fallback when timeout occurs
func example4FallbackOnTimeout() {
	fmt.Println("\n=== Example 4: Fallback on Timeout ===")
	fmt.Println("Use case: Provide cached/default response when primary agent times out\n")

	// Primary agent (slow)
	primary := NewSlowLLMAgent(5 * time.Second)
	timeoutConfig := middleware.TimeoutConfig{
		Timeout: 1 * time.Second,
	}
	primaryWithTimeout := middleware.NewTimeoutDecorator(primary, timeoutConfig)

	// Fallback agent (fast)
	fallback := NewCachedResponseAgent()

	message := agenkit.NewMessage("user", "Hello!")

	fmt.Println("Trying primary agent with 1s timeout...")
	ctx := context.Background()
	response, err := primaryWithTimeout.Process(ctx, message)

	if err != nil {
		fmt.Printf("⚠️  Primary timed out: %v\n", err)
		fmt.Println("   Falling back to cached response...")
		response, err = fallback.Process(ctx, message)
		if err == nil {
			fmt.Printf("✅ Fallback response: %s\n", response.Content)
		}
	} else {
		fmt.Printf("✅ Primary response: %s\n", response.Content)
	}
}

// StreamingAgent simulates an agent that streams responses over time
type StreamingAgent struct {
	name       string
	chunkDelay time.Duration
	numChunks  int
}

func NewStreamingAgent(chunkDelay time.Duration, numChunks int) *StreamingAgent {
	return &StreamingAgent{
		name:       "streaming-agent",
		chunkDelay: chunkDelay,
		numChunks:  numChunks,
	}
}

func (a *StreamingAgent) Name() string {
	return a.name
}

func (a *StreamingAgent) Capabilities() []string {
	return []string{"streaming", "text-generation"}
}

func (a *StreamingAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	return agenkit.NewMessage("assistant", "Full response"), nil
}

func (a *StreamingAgent) Stream(ctx context.Context, message *agenkit.Message) (<-chan *agenkit.Message, <-chan error) {
	messageChan := make(chan *agenkit.Message)
	errorChan := make(chan error, 1)

	go func() {
		defer close(messageChan)
		defer close(errorChan)

		for i := 0; i < a.numChunks; i++ {
			// Check for context cancellation
			select {
			case <-ctx.Done():
				errorChan <- ctx.Err()
				return
			case <-time.After(a.chunkDelay):
				chunk := agenkit.NewMessage("assistant", fmt.Sprintf("Chunk %d/%d: Processing...", i+1, a.numChunks))
				messageChan <- chunk
			}
		}
	}()

	return messageChan, errorChan
}

// Example 5: Timeout with streaming responses
func example5StreamingTimeout() {
	fmt.Println("\n=== Example 5: Streaming with Timeout ===")
	fmt.Println("Use case: Apply timeout to entire stream duration\n")

	// Create streaming agent (5 chunks × 0.5s = 2.5s total)
	agent := NewStreamingAgent(500*time.Millisecond, 5)

	message := agenkit.NewMessage("user", "Generate long response")

	fmt.Println("Streaming with 2s timeout (should timeout after ~2s)...")

	// Create context with timeout (2 seconds for a stream that takes 2.5s)
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	// For streaming, we handle timeout via context directly
	// (TimeoutDecorator only wraps Process, not Stream)
	messageChan, errorChan := agent.Stream(ctx, message)

	// Read from channels
	for {
		select {
		case chunk, ok := <-messageChan:
			if !ok {
				// Channel closed, check for errors
				select {
				case err := <-errorChan:
					if err != nil {
						fmt.Printf("❌ Stream timed out: %v\n", err)
						fmt.Println("   Timeout applies to entire stream duration")
					}
				default:
					// No error, stream completed successfully
				}
				return
			}
			fmt.Printf("   📦 %s\n", chunk.Content)
		case err := <-errorChan:
			if err != nil {
				fmt.Printf("❌ Stream timed out: %v\n", err)
				fmt.Println("   Timeout applies to entire stream duration")
			}
			return
		}
	}
}

// Example 6: Different timeout strategies for different use cases
func example6DifferentTimeoutStrategies() {
	fmt.Println("\n=== Example 6: Timeout Strategies ===")
	fmt.Println("Use case: Choose appropriate timeout based on operation type\n")

	agent := NewSlowLLMAgent(1500 * time.Millisecond)

	// Strategy 1: Strict timeout for interactive responses
	interactiveConfig := middleware.TimeoutConfig{
		Timeout: 1 * time.Second, // 1 second
	}
	interactiveAgent := middleware.NewTimeoutDecorator(agent, interactiveConfig)

	// Strategy 2: Relaxed timeout for background processing
	backgroundConfig := middleware.TimeoutConfig{
		Timeout: 5 * time.Second, // 5 seconds
	}
	backgroundAgent := middleware.NewTimeoutDecorator(agent, backgroundConfig)

	message := agenkit.NewMessage("user", "Process this")

	// Interactive request (strict timeout)
	fmt.Println("Interactive request (1s timeout):")
	ctx := context.Background()
	response, err := interactiveAgent.Process(ctx, message)
	if err != nil {
		fmt.Println("   ❌ Timeout: Too slow for interactive use")
	} else {
		fmt.Printf("   ✅ Success: %s\n", response.Content)
	}

	// Background request (relaxed timeout)
	fmt.Println("\nBackground request (5s timeout):")
	response, err = backgroundAgent.Process(ctx, message)
	if err != nil {
		fmt.Println("   ❌ Timeout: Even background processing failed")
	} else {
		fmt.Printf("   ✅ Success: %s\n", response.Content)
	}
}

func main() {
	// Seed random for demonstration
	rand.Seed(time.Now().UnixNano())

	fmt.Println(strings.Repeat("=", 60))
	fmt.Println("Timeout Middleware Examples")
	fmt.Println(strings.Repeat("=", 60))

	example1BasicTimeout()

	fmt.Print("\nPress Enter to continue...")
	fmt.Scanln()

	example2SuccessfulWithTimeout()

	fmt.Print("\nPress Enter to continue...")
	fmt.Scanln()

	example3MultipleRequestsWithMetrics()

	fmt.Print("\nPress Enter to continue...")
	fmt.Scanln()

	example4FallbackOnTimeout()

	fmt.Print("\nPress Enter to continue...")
	fmt.Scanln()

	example5StreamingTimeout()

	fmt.Print("\nPress Enter to continue...")
	fmt.Scanln()

	example6DifferentTimeoutStrategies()

	fmt.Println("\n" + strings.Repeat("=", 60))
	fmt.Println("Examples complete!")
	fmt.Println(strings.Repeat("=", 60))
	fmt.Println("\nKey Takeaways:")
	fmt.Println("1. Set timeouts based on SLA requirements and operation type")
	fmt.Println("2. Implement fallback strategies for timeout scenarios")
	fmt.Println("3. Monitor metrics to tune timeout values")
	fmt.Println("4. Use different timeouts for interactive vs background operations")
	fmt.Println("5. Remember: timeout applies to entire stream duration")
}
