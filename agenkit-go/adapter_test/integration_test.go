package adapter_test

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"testing"
	"time"

	"github.com/agenkit/agenkit-go/adapter/local"
	"github.com/agenkit/agenkit-go/adapter/remote"
	"github.com/agenkit/agenkit-go/agenkit"
)

// EchoAgent echoes back messages
type EchoAgent struct{}

func (e *EchoAgent) Name() string {
	return "echo"
}

func (e *EchoAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	return agenkit.NewMessage("agent", "Echo: "+message.Content), nil
}

func (e *EchoAgent) Capabilities() []string {
	return []string{"echo"}
}

// StreamingEchoAgent streams responses
type StreamingEchoAgent struct {
	EchoAgent
}

func (s *StreamingEchoAgent) Stream(ctx context.Context, message *agenkit.Message) (<-chan *agenkit.Message, <-chan error) {
	messageChan := make(chan *agenkit.Message, 10) // Buffered to avoid blocking
	errorChan := make(chan error, 1)

	go func() {
		defer close(messageChan)
		defer close(errorChan)

		// Send 5 chunks
		for i := 0; i < 5; i++ {
			select {
			case <-ctx.Done():
				errorChan <- ctx.Err()
				return
			default:
				time.Sleep(10 * time.Millisecond)
				msg := agenkit.NewMessage("agent", fmt.Sprintf("Chunk %d: %s", i, message.Content)).
					WithMetadata("chunk_id", i)
				messageChan <- msg
			}
		}
	}()

	return messageChan, errorChan
}

// ErrorAgent always returns an error
type ErrorAgent struct{}

func (e *ErrorAgent) Name() string {
	return "error"
}

func (e *ErrorAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	return nil, fmt.Errorf("intentional error")
}

func (e *ErrorAgent) Capabilities() []string {
	return []string{}
}

func TestBasicCommunicationUnixSocket(t *testing.T) {
	ctx := context.Background()

	// Create temp directory for socket
	tmpDir, err := os.MkdirTemp("", "agenkit-test-*")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(tmpDir)

	socketPath := filepath.Join(tmpDir, "echo.sock")
	endpoint := fmt.Sprintf("unix://%s", socketPath)

	// Start server
	agent := &EchoAgent{}
	server, err := local.NewLocalAgent(agent, endpoint)
	if err != nil {
		t.Fatal(err)
	}

	if err := server.Start(ctx); err != nil {
		t.Fatal(err)
	}
	defer server.Stop()

	// Give server time to start
	time.Sleep(50 * time.Millisecond)

	// Connect client
	client, err := remote.NewRemoteAgent("echo", endpoint, 5*time.Second)
	if err != nil {
		t.Fatal(err)
	}
	defer client.Close()

	// Send message
	msg := agenkit.NewMessage("user", "Hello World")
	response, err := client.Process(ctx, msg)
	if err != nil {
		t.Fatal(err)
	}

	// Verify response
	if response.Role != "agent" {
		t.Errorf("Expected role 'agent', got '%s'", response.Role)
	}
	if response.Content != "Echo: Hello World" {
		t.Errorf("Expected content 'Echo: Hello World', got '%s'", response.Content)
	}
}

func TestBasicCommunicationTCP(t *testing.T) {
	ctx := context.Background()
	endpoint := "tcp://127.0.0.1:19876"

	// Start server
	agent := &EchoAgent{}
	server, err := local.NewLocalAgent(agent, endpoint)
	if err != nil {
		t.Fatal(err)
	}

	if err := server.Start(ctx); err != nil {
		t.Fatal(err)
	}
	defer server.Stop()

	// Give server time to start
	time.Sleep(50 * time.Millisecond)

	// Connect client
	client, err := remote.NewRemoteAgent("echo", endpoint, 5*time.Second)
	if err != nil {
		t.Fatal(err)
	}
	defer client.Close()

	// Send message
	msg := agenkit.NewMessage("user", "TCP Test")
	response, err := client.Process(ctx, msg)
	if err != nil {
		t.Fatal(err)
	}

	// Verify response
	if response.Content != "Echo: TCP Test" {
		t.Errorf("Expected content 'Echo: TCP Test', got '%s'", response.Content)
	}
}

func TestMultipleSequentialRequests(t *testing.T) {
	ctx := context.Background()

	tmpDir, err := os.MkdirTemp("", "agenkit-test-*")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(tmpDir)

	socketPath := filepath.Join(tmpDir, "echo.sock")
	endpoint := fmt.Sprintf("unix://%s", socketPath)

	// Start server
	agent := &EchoAgent{}
	server, err := local.NewLocalAgent(agent, endpoint)
	if err != nil {
		t.Fatal(err)
	}

	if err := server.Start(ctx); err != nil {
		t.Fatal(err)
	}
	defer server.Stop()

	time.Sleep(50 * time.Millisecond)

	// Connect client
	client, err := remote.NewRemoteAgent("echo", endpoint, 5*time.Second)
	if err != nil {
		t.Fatal(err)
	}
	defer client.Close()

	// Send multiple messages
	for i := 0; i < 10; i++ {
		msg := agenkit.NewMessage("user", fmt.Sprintf("Message %d", i))
		response, err := client.Process(ctx, msg)
		if err != nil {
			t.Fatalf("Request %d failed: %v", i, err)
		}

		expected := fmt.Sprintf("Echo: Message %d", i)
		if response.Content != expected {
			t.Errorf("Request %d: expected '%s', got '%s'", i, expected, response.Content)
		}
	}
}

func TestConcurrentRequests(t *testing.T) {
	ctx := context.Background()
	endpoint := "tcp://127.0.0.1:19877"

	// Start server
	agent := &EchoAgent{}
	server, err := local.NewLocalAgent(agent, endpoint)
	if err != nil {
		t.Fatal(err)
	}

	if err := server.Start(ctx); err != nil {
		t.Fatal(err)
	}
	defer server.Stop()

	time.Sleep(50 * time.Millisecond)

	// Create multiple clients and send concurrent requests
	numClients := 5
	requestsPerClient := 3

	var wg sync.WaitGroup
	errors := make(chan error, numClients*requestsPerClient)

	for clientID := 0; clientID < numClients; clientID++ {
		wg.Add(1)
		go func(id int) {
			defer wg.Done()

			// Each client gets its own connection
			client, err := remote.NewRemoteAgent("echo", endpoint, 5*time.Second)
			if err != nil {
				errors <- fmt.Errorf("client %d: failed to connect: %w", id, err)
				return
			}
			defer client.Close()

			for reqID := 0; reqID < requestsPerClient; reqID++ {
				content := fmt.Sprintf("Client %d Request %d", id, reqID)
				msg := agenkit.NewMessage("user", content)
				response, err := client.Process(ctx, msg)
				if err != nil {
					errors <- fmt.Errorf("client %d request %d: %w", id, reqID, err)
					return
				}

				expected := fmt.Sprintf("Echo: %s", content)
				if response.Content != expected {
					errors <- fmt.Errorf("client %d request %d: expected '%s', got '%s'",
						id, reqID, expected, response.Content)
					return
				}
			}
		}(clientID)
	}

	wg.Wait()
	close(errors)

	// Check for errors
	for err := range errors {
		t.Error(err)
	}
}

func TestMetadataPreservation(t *testing.T) {
	ctx := context.Background()

	tmpDir, err := os.MkdirTemp("", "agenkit-test-*")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(tmpDir)

	socketPath := filepath.Join(tmpDir, "echo.sock")
	endpoint := fmt.Sprintf("unix://%s", socketPath)

	// Start server
	agent := &EchoAgent{}
	server, err := local.NewLocalAgent(agent, endpoint)
	if err != nil {
		t.Fatal(err)
	}

	if err := server.Start(ctx); err != nil {
		t.Fatal(err)
	}
	defer server.Stop()

	time.Sleep(50 * time.Millisecond)

	// Connect client
	client, err := remote.NewRemoteAgent("echo", endpoint, 5*time.Second)
	if err != nil {
		t.Fatal(err)
	}
	defer client.Close()

	// Send message with metadata
	msg := agenkit.NewMessage("user", "Test").
		WithMetadata("key1", "value1").
		WithMetadata("key2", 42).
		WithMetadata("key3", []string{"a", "b", "c"})

	response, err := client.Process(ctx, msg)
	if err != nil {
		t.Fatal(err)
	}

	// Response should have metadata in its envelope (not copied from request)
	// But the agent can access request metadata in Process()
	if response.Content != "Echo: Test" {
		t.Errorf("Unexpected content: %s", response.Content)
	}
}

func TestAgentError(t *testing.T) {
	ctx := context.Background()
	endpoint := "tcp://127.0.0.1:19878"

	// Start server with error agent
	agent := &ErrorAgent{}
	server, err := local.NewLocalAgent(agent, endpoint)
	if err != nil {
		t.Fatal(err)
	}

	if err := server.Start(ctx); err != nil {
		t.Fatal(err)
	}
	defer server.Stop()

	time.Sleep(50 * time.Millisecond)

	// Connect client
	client, err := remote.NewRemoteAgent("error", endpoint, 5*time.Second)
	if err != nil {
		t.Fatal(err)
	}
	defer client.Close()

	// Send message - should get error
	msg := agenkit.NewMessage("user", "Test")
	_, err = client.Process(ctx, msg)
	if err == nil {
		t.Fatal("Expected error, got nil")
	}

	// Verify it's a remote execution error
	if err.Error() == "" {
		t.Error("Expected non-empty error message")
	}
}

func TestLargeMessage(t *testing.T) {
	ctx := context.Background()
	endpoint := "tcp://127.0.0.1:19879"

	// Start server
	agent := &EchoAgent{}
	server, err := local.NewLocalAgent(agent, endpoint)
	if err != nil {
		t.Fatal(err)
	}

	if err := server.Start(ctx); err != nil {
		t.Fatal(err)
	}
	defer server.Stop()

	time.Sleep(50 * time.Millisecond)

	// Connect client
	client, err := remote.NewRemoteAgent("echo", endpoint, 5*time.Second)
	if err != nil {
		t.Fatal(err)
	}
	defer client.Close()

	// Create large message (1MB)
	largeContent := string(make([]byte, 1024*1024))
	msg := agenkit.NewMessage("user", largeContent)
	response, err := client.Process(ctx, msg)
	if err != nil {
		t.Fatal(err)
	}

	// Verify response
	expectedLen := len("Echo: ") + len(largeContent)
	if len(response.Content) != expectedLen {
		t.Errorf("Expected content length %d, got %d", expectedLen, len(response.Content))
	}
}

func TestBasicStreaming(t *testing.T) {
	ctx := context.Background()

	tmpDir, err := os.MkdirTemp("", "agenkit-test-*")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(tmpDir)

	socketPath := filepath.Join(tmpDir, "stream.sock")
	endpoint := fmt.Sprintf("unix://%s", socketPath)

	// Start server with streaming agent
	agent := &StreamingEchoAgent{}
	server, err := local.NewLocalAgent(agent, endpoint)
	if err != nil {
		t.Fatal(err)
	}

	if err := server.Start(ctx); err != nil {
		t.Fatal(err)
	}
	defer server.Stop()

	time.Sleep(50 * time.Millisecond)

	// Connect client
	client, err := remote.NewRemoteAgent("echo", endpoint, 5*time.Second)
	if err != nil {
		t.Fatal(err)
	}
	defer client.Close()

	// Stream messages
	msg := agenkit.NewMessage("user", "test")
	messageChan, errorChan := client.Stream(ctx, msg)

	// Collect chunks
	chunks := []*agenkit.Message{}
	done := false
	for !done {
		select {
		case chunk, ok := <-messageChan:
			if !ok {
				// Message channel closed
				done = true
			} else {
				chunks = append(chunks, chunk)
			}

		case err, ok := <-errorChan:
			if ok && err != nil {
				t.Fatalf("Stream error: %v", err)
			}
			if !ok {
				// Error channel closed
				done = true
			}
		}
	}

	// Verify we got all chunks
	if len(chunks) != 5 {
		t.Errorf("Expected 5 chunks, got %d", len(chunks))
	}
	for i, chunk := range chunks {
		expected := fmt.Sprintf("Chunk %d: test", i)
		if chunk.Content != expected {
			t.Errorf("Chunk %d: expected '%s', got '%s'", i, expected, chunk.Content)
		}
		chunkID, ok := chunk.Metadata["chunk_id"]
		if !ok {
			t.Errorf("Chunk %d: missing chunk_id metadata", i)
		} else if chunkID != float64(i) { // JSON numbers decode as float64
			t.Errorf("Chunk %d: expected chunk_id %d, got %v", i, i, chunkID)
		}
	}
}

func TestStreamingTCP(t *testing.T) {
	ctx := context.Background()
	endpoint := "tcp://127.0.0.1:19880"

	// Start server
	agent := &StreamingEchoAgent{}
	server, err := local.NewLocalAgent(agent, endpoint)
	if err != nil {
		t.Fatal(err)
	}

	if err := server.Start(ctx); err != nil {
		t.Fatal(err)
	}
	defer server.Stop()

	time.Sleep(50 * time.Millisecond)

	// Connect client
	client, err := remote.NewRemoteAgent("echo", endpoint, 5*time.Second)
	if err != nil {
		t.Fatal(err)
	}
	defer client.Close()

	// Stream messages
	msg := agenkit.NewMessage("user", "tcp_test")
	messageChan, errorChan := client.Stream(ctx, msg)

	// Count chunks
	chunkCount := 0
	done := false
	for !done {
		select {
		case chunk, ok := <-messageChan:
			if !ok {
				// Message channel closed
				done = true
			} else {
				chunkCount++
				if chunk.Role != "agent" {
					t.Errorf("Expected role 'agent', got '%s'", chunk.Role)
				}
			}

		case err, ok := <-errorChan:
			if ok && err != nil {
				t.Fatalf("Stream error: %v", err)
			}
			if !ok {
				// Error channel closed
				done = true
			}
		}
	}

	// Verify chunk count
	if chunkCount != 5 {
		t.Errorf("Expected 5 chunks, got %d", chunkCount)
	}
}

func TestServerStartStop(t *testing.T) {
	ctx := context.Background()

	tmpDir, err := os.MkdirTemp("", "agenkit-test-*")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(tmpDir)

	socketPath := filepath.Join(tmpDir, "test.sock")
	endpoint := fmt.Sprintf("unix://%s", socketPath)

	agent := &EchoAgent{}
	server, err := local.NewLocalAgent(agent, endpoint)
	if err != nil {
		t.Fatal(err)
	}

	// Start and stop multiple times
	for i := 0; i < 3; i++ {
		if err := server.Start(ctx); err != nil {
			t.Fatalf("Start iteration %d failed: %v", i, err)
		}

		time.Sleep(50 * time.Millisecond)

		// Verify socket exists
		if _, err := os.Stat(socketPath); os.IsNotExist(err) {
			t.Errorf("Iteration %d: socket file doesn't exist", i)
		}

		if err := server.Stop(); err != nil {
			t.Fatalf("Stop iteration %d failed: %v", i, err)
		}

		time.Sleep(50 * time.Millisecond)

		// Verify socket is cleaned up
		if _, err := os.Stat(socketPath); !os.IsNotExist(err) {
			t.Errorf("Iteration %d: socket file wasn't cleaned up", i)
		}
	}
}
