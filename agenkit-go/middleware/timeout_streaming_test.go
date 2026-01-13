package middleware

import (
	"context"
	"fmt"
	"testing"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// ============================================
// Streaming Test Agent Implementations
// ============================================

// StreamingTestAgent implements the StreamingAgent interface for testing.
type StreamingTestAgent struct {
	name         string
	messageDelay time.Duration // Delay between each message
	messageCount int           // Number of messages to send
}

func NewStreamingTestAgent(name string, messageDelay time.Duration, messageCount int) *StreamingTestAgent {
	return &StreamingTestAgent{
		name:         name,
		messageDelay: messageDelay,
		messageCount: messageCount,
	}
}

func (a *StreamingTestAgent) Name() string {
	return a.name
}

func (a *StreamingTestAgent) Capabilities() []string {
	return []string{"streaming"}
}

func (a *StreamingTestAgent) Introspect() *agenkit.IntrospectionResult {
	return agenkit.DefaultIntrospectionResult(a)
}

func (a *StreamingTestAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	return &agenkit.Message{
		Role:    "agent",
		Content: "Processed: " + message.Content,
	}, nil
}

func (a *StreamingTestAgent) Stream(ctx context.Context, message *agenkit.Message) (<-chan *agenkit.Message, <-chan error) {
	messageChan := make(chan *agenkit.Message, 10)
	errorChan := make(chan error, 1)

	go func() {
		defer close(messageChan)
		defer close(errorChan)

		for i := 0; i < a.messageCount; i++ {
			// Check for cancellation
			select {
			case <-ctx.Done():
				errorChan <- ctx.Err()
				return
			case <-time.After(a.messageDelay):
				// Send message
				select {
				case messageChan <- &agenkit.Message{
					Role:    "agent",
					Content: fmt.Sprintf("Chunk %d: %s", i, message.Content),
				}:
				case <-ctx.Done():
					errorChan <- ctx.Err()
					return
				}
			}
		}
	}()

	return messageChan, errorChan
}

// ============================================
// Timeout Streaming Tests
// ============================================

func TestTimeoutStreamingSuccess(t *testing.T) {
	// Create a streaming agent that completes within timeout
	agent := NewStreamingTestAgent("fast-streaming", 20*time.Millisecond, 3)

	config := TimeoutConfig{
		Timeout: 200 * time.Millisecond,
	}
	timeoutAgent := NewTimeoutDecorator(agent, config)

	msg := &agenkit.Message{
		Role:    "user",
		Content: "test",
	}

	messageChan, errorChan := timeoutAgent.Stream(context.Background(), msg)

	// Collect all messages
	messages := []string{}
	for {
		select {
		case msg, ok := <-messageChan:
			if !ok {
				// Check for errors
				select {
				case err := <-errorChan:
					if err != nil {
						t.Fatalf("Expected no error, got %v", err)
					}
				default:
					// No error - successful completion
				}
				// Success!
				if len(messages) != 3 {
					t.Errorf("Expected 3 messages, got %d", len(messages))
				}
				return
			}
			messages = append(messages, msg.Content)
		case err := <-errorChan:
			if err != nil {
				t.Fatalf("Unexpected error: %v", err)
			}
		}
	}
}

func TestTimeoutStreamingTimesOut(t *testing.T) {
	// Create a streaming agent that exceeds timeout
	agent := NewStreamingTestAgent("slow-streaming", 100*time.Millisecond, 5)

	config := TimeoutConfig{
		Timeout: 250 * time.Millisecond, // Will timeout after ~2 messages
	}
	timeoutAgent := NewTimeoutDecorator(agent, config)

	msg := &agenkit.Message{
		Role:    "user",
		Content: "test",
	}

	messageChan, errorChan := timeoutAgent.Stream(context.Background(), msg)

	// Should eventually timeout
	timedOut := false
	for {
		select {
		case _, ok := <-messageChan:
			if !ok {
				// Channel closed, check for timeout error
				select {
				case err := <-errorChan:
					if _, ok := err.(*TimeoutError); ok {
						timedOut = true
					}
				default:
				}
				if !timedOut {
					t.Error("Expected timeout error")
				}
				return
			}
		case err := <-errorChan:
			if timeoutErr, ok := err.(*TimeoutError); ok {
				if timeoutErr.Timeout != 250*time.Millisecond {
					t.Errorf("Expected timeout of 250ms, got %v", timeoutErr.Timeout)
				}
				timedOut = true
				return
			}
			t.Fatalf("Expected TimeoutError, got %v", err)
		case <-time.After(2 * time.Second):
			t.Fatal("Test timed out waiting for timeout error")
		}
	}
}

func TestTimeoutStreamingNonStreamingAgent(t *testing.T) {
	// Use a non-streaming agent
	agent := NewFastAgent(10 * time.Millisecond)

	config := TimeoutConfig{
		Timeout: 100 * time.Millisecond,
	}
	timeoutAgent := NewTimeoutDecorator(agent, config)

	msg := &agenkit.Message{
		Role:    "user",
		Content: "test",
	}

	messageChan, errorChan := timeoutAgent.Stream(context.Background(), msg)

	// Should immediately receive an error
	select {
	case _, ok := <-messageChan:
		if ok {
			t.Error("Expected no messages from non-streaming agent")
		}
	case err := <-errorChan:
		if err == nil {
			t.Error("Expected error for non-streaming agent")
		}
		if err.Error() != "underlying agent does not support streaming" {
			t.Errorf("Expected 'underlying agent does not support streaming', got '%s'", err.Error())
		}
		return
	case <-time.After(1 * time.Second):
		t.Fatal("Test timed out waiting for error")
	}
}

func TestTimeoutStreamingMetrics(t *testing.T) {
	// Create a streaming agent
	agent := NewStreamingTestAgent("test-streaming", 20*time.Millisecond, 3)

	config := TimeoutConfig{
		Timeout: 200 * time.Millisecond,
	}
	timeoutAgent := NewTimeoutDecorator(agent, config)

	msg := &agenkit.Message{
		Role:    "user",
		Content: "test",
	}

	messageChan, errorChan := timeoutAgent.Stream(context.Background(), msg)

	// Consume all messages
	messageCount := 0
	for {
		select {
		case _, ok := <-messageChan:
			if !ok {
				// Message channel closed - stream complete
				// Check if there's an error
				select {
				case err := <-errorChan:
					if err != nil {
						t.Fatalf("Unexpected error: %v", err)
					}
				default:
					// No error - successful completion
				}

				// Check metrics
				metrics := timeoutAgent.Metrics()
				if metrics.TotalRequests != 1 {
					t.Errorf("Expected 1 total request, got %d", metrics.TotalRequests)
				}
				if metrics.SuccessfulRequests != 1 {
					t.Errorf("Expected 1 successful request, got %d", metrics.SuccessfulRequests)
				}
				if metrics.TimedOutRequests != 0 {
					t.Errorf("Expected 0 timed out requests, got %d", metrics.TimedOutRequests)
				}
				return
			}
			messageCount++
		case err := <-errorChan:
			if err != nil {
				t.Fatalf("Unexpected error: %v", err)
			}
		case <-time.After(1 * time.Second):
			t.Fatal("Test timed out")
		}
	}
}

func TestTimeoutStreamingMethodSpecificTimeout(t *testing.T) {
	// Create a streaming agent
	agent := NewStreamingTestAgent("test-streaming", 100*time.Millisecond, 5)

	config := TimeoutConfig{
		Timeout: 100 * time.Millisecond, // Default timeout (short)
		MethodTimeouts: map[string]time.Duration{
			"long_operation": 600 * time.Millisecond, // Method-specific timeout (long)
		},
	}
	timeoutAgent := NewTimeoutDecorator(agent, config)

	// Test with method-specific timeout
	msg := &agenkit.Message{
		Role:    "user",
		Content: "test",
		Metadata: map[string]interface{}{
			"method": "long_operation",
		},
	}

	messageChan, errorChan := timeoutAgent.Stream(context.Background(), msg)

	// Should complete successfully with longer timeout
	messageCount := 0
	for {
		select {
		case _, ok := <-messageChan:
			if !ok {
				// Message channel closed - check for errors
				select {
				case err := <-errorChan:
					if err != nil {
						t.Fatalf("Expected no error with method-specific timeout, got %v", err)
					}
				default:
					// No error - successful completion
				}
				if messageCount != 5 {
					t.Errorf("Expected 5 messages, got %d", messageCount)
				}
				return
			}
			messageCount++
		case err := <-errorChan:
			if err != nil {
				t.Fatalf("Unexpected error: %v", err)
			}
		case <-time.After(2 * time.Second):
			t.Fatal("Test timed out")
		}
	}
}
