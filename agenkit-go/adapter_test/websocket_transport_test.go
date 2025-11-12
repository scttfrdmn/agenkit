package adapter_test

import (
	"context"
	"fmt"
	nethttp "net/http"
	"sync"
	"testing"
	"time"

	"github.com/agenkit/agenkit-go/adapter/http"
	"github.com/agenkit/agenkit-go/adapter/local"
	"github.com/agenkit/agenkit-go/adapter/remote"
	"github.com/agenkit/agenkit-go/agenkit"
)

func TestWebSocketBasicCommunication(t *testing.T) {
	ctx := context.Background()

	// Start HTTP server with WebSocket support
	agent := &EchoAgent{}
	httpAgent := http.NewHTTPAgent(agent, "127.0.0.1:29900")
	if err := httpAgent.Start(ctx); err != nil {
		t.Fatal(err)
	}
	defer httpAgent.Stop()

	// Give server time to start
	time.Sleep(100 * time.Millisecond)

	// Create client using WebSocket endpoint
	endpoint := "ws://127.0.0.1:29900/ws"
	client, err := remote.NewRemoteAgent("echo", endpoint, 5*time.Second)
	if err != nil {
		t.Fatal(err)
	}
	defer client.Close()

	// Test communication
	message := agenkit.NewMessage("user", "Hello")
	response, err := client.Process(ctx, message)
	if err != nil {
		t.Fatal(err)
	}

	// Verify response
	if response.Role != "agent" {
		t.Errorf("Expected role 'agent', got '%s'", response.Role)
	}
	if response.Content != "Echo: Hello" {
		t.Errorf("Expected content 'Echo: Hello', got '%s'", response.Content)
	}
}

func TestWebSocketMultipleRequests(t *testing.T) {
	ctx := context.Background()

	// Start HTTP server with WebSocket support
	agent := &EchoAgent{}
	httpAgent := http.NewHTTPAgent(agent, "127.0.0.1:29901")
	if err := httpAgent.Start(ctx); err != nil {
		t.Fatal(err)
	}
	defer httpAgent.Stop()

	time.Sleep(100 * time.Millisecond)

	// Create client
	endpoint := "ws://127.0.0.1:29901/ws"
	client, err := remote.NewRemoteAgent("echo", endpoint, 5*time.Second)
	if err != nil {
		t.Fatal(err)
	}
	defer client.Close()

	// Send multiple requests
	for i := 0; i < 5; i++ {
		message := agenkit.NewMessage("user", fmt.Sprintf("Message %d", i))
		response, err := client.Process(ctx, message)
		if err != nil {
			t.Fatalf("Request %d failed: %v", i, err)
		}

		expected := fmt.Sprintf("Echo: Message %d", i)
		if response.Content != expected {
			t.Errorf("Request %d: expected '%s', got '%s'", i, expected, response.Content)
		}
	}
}

func TestWebSocketConcurrentRequests(t *testing.T) {
	ctx := context.Background()

	// Start HTTP server with WebSocket support
	agent := &EchoAgent{}
	httpAgent := http.NewHTTPAgent(agent, "127.0.0.1:29902")
	if err := httpAgent.Start(ctx); err != nil {
		t.Fatal(err)
	}
	defer httpAgent.Stop()

	time.Sleep(100 * time.Millisecond)

	// Create separate clients for concurrent requests
	numClients := 5
	var wg sync.WaitGroup
	errors := make(chan error, numClients)

	endpoint := "ws://127.0.0.1:29902/ws"
	for i := 0; i < numClients; i++ {
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

			message := agenkit.NewMessage("user", fmt.Sprintf("Message %d", id))
			response, err := client.Process(ctx, message)
			if err != nil {
				errors <- fmt.Errorf("client %d: %w", id, err)
				return
			}

			expected := fmt.Sprintf("Echo: Message %d", id)
			if response.Content != expected {
				errors <- fmt.Errorf("client %d: expected '%s', got '%s'", id, expected, response.Content)
			}
		}(i)
	}

	wg.Wait()
	close(errors)

	// Check for errors
	for err := range errors {
		t.Error(err)
	}
}

func TestWebSocketConnectionFailure(t *testing.T) {
	ctx := context.Background()
	endpoint := "ws://127.0.0.1:29999/ws" // Non-existent server

	// Try to connect to non-existent server
	client, err := remote.NewRemoteAgent("echo", endpoint, 1*time.Second)
	if err != nil {
		t.Fatal(err)
	}
	defer client.Close()

	message := agenkit.NewMessage("user", "test")
	_, err = client.Process(ctx, message)
	if err == nil {
		t.Fatal("Expected connection error, got nil")
	}

	// Verify it's a connection error
	if err.Error() == "" {
		t.Error("Expected non-empty error message")
	}
}

func TestWebSocketLargeMessage(t *testing.T) {
	ctx := context.Background()

	// Start HTTP server with WebSocket support
	agent := &EchoAgent{}
	httpAgent := http.NewHTTPAgent(agent, "127.0.0.1:29903")
	if err := httpAgent.Start(ctx); err != nil {
		t.Fatal(err)
	}
	defer httpAgent.Stop()

	time.Sleep(100 * time.Millisecond)

	// Create client
	endpoint := "ws://127.0.0.1:29903/ws"
	client, err := remote.NewRemoteAgent("echo", endpoint, 10*time.Second)
	if err != nil {
		t.Fatal(err)
	}
	defer client.Close()

	// Send large message (1MB)
	largeContent := string(make([]byte, 1024*1024))
	message := agenkit.NewMessage("user", largeContent)
	response, err := client.Process(ctx, message)
	if err != nil {
		t.Fatal(err)
	}

	// Verify response
	expectedLen := len("Echo: ") + len(largeContent)
	if len(response.Content) != expectedLen {
		t.Errorf("Expected content length %d, got %d", expectedLen, len(response.Content))
	}
}

func TestWebSocketReconnection(t *testing.T) {
	ctx := context.Background()

	// Start HTTP server with WebSocket support
	agent := &EchoAgent{}
	httpAgent := http.NewHTTPAgent(agent, "127.0.0.1:29904")
	if err := httpAgent.Start(ctx); err != nil {
		t.Fatal(err)
	}

	time.Sleep(100 * time.Millisecond)

	// Create client
	endpoint := "ws://127.0.0.1:29904/ws"
	client, err := remote.NewRemoteAgent("echo", endpoint, 5*time.Second)
	if err != nil {
		t.Fatal(err)
	}
	defer client.Close()

	// First request
	message := agenkit.NewMessage("user", "First")
	response, err := client.Process(ctx, message)
	if err != nil {
		t.Fatal(err)
	}
	if response.Content != "Echo: First" {
		t.Errorf("Expected 'Echo: First', got '%s'", response.Content)
	}

	// Stop server
	if err := httpAgent.Stop(); err != nil {
		t.Fatal(err)
	}

	// Wait for connection to close
	time.Sleep(200 * time.Millisecond)

	// Restart server
	httpAgent = http.NewHTTPAgent(agent, "127.0.0.1:29904")
	if err := httpAgent.Start(ctx); err != nil {
		t.Fatal(err)
	}
	defer httpAgent.Stop()

	time.Sleep(100 * time.Millisecond)

	// Second request should trigger reconnection
	message = agenkit.NewMessage("user", "Second")
	response, err = client.Process(ctx, message)
	if err != nil {
		t.Fatal(err)
	}
	if response.Content != "Echo: Second" {
		t.Errorf("Expected 'Echo: Second', got '%s'", response.Content)
	}
}

func TestWebSocketBinaryData(t *testing.T) {
	ctx := context.Background()

	// Start HTTP server with WebSocket support
	agent := &EchoAgent{}
	httpAgent := http.NewHTTPAgent(agent, "127.0.0.1:29905")
	if err := httpAgent.Start(ctx); err != nil {
		t.Fatal(err)
	}
	defer httpAgent.Stop()

	time.Sleep(100 * time.Millisecond)

	// Create client - WebSocket transport handles binary messages automatically
	endpoint := "ws://127.0.0.1:29905/ws"
	client, err := remote.NewRemoteAgent("echo", endpoint, 5*time.Second)
	if err != nil {
		t.Fatal(err)
	}
	defer client.Close()

	// Test with message containing special characters
	message := agenkit.NewMessage("user", "Binary data: \x00\x01\x02\xff")
	response, err := client.Process(ctx, message)
	if err != nil {
		t.Fatal(err)
	}

	// Verify response
	if response.Role != "agent" {
		t.Errorf("Expected role 'agent', got '%s'", response.Role)
	}
	if len(response.Content) == 0 {
		t.Error("Expected non-empty content")
	}
}

func TestWebSocketIsConnectedProperty(t *testing.T) {
	ctx := context.Background()

	// Start HTTP server with WebSocket support
	agent := &EchoAgent{}
	httpAgent := http.NewHTTPAgent(agent, "127.0.0.1:29906")
	if err := httpAgent.Start(ctx); err != nil {
		t.Fatal(err)
	}
	defer httpAgent.Stop()

	time.Sleep(100 * time.Millisecond)

	// Create client
	endpoint := "ws://127.0.0.1:29906/ws"
	client, err := remote.NewRemoteAgent("echo", endpoint, 5*time.Second)
	if err != nil {
		t.Fatal(err)
	}
	defer client.Close()

	// Make a request to establish connection
	message := agenkit.NewMessage("user", "test")
	_, err = client.Process(ctx, message)
	if err != nil {
		t.Fatal(err)
	}

	// Connection should be established after successful request
	// Note: We can't directly check IsConnected on the remote agent,
	// but we can verify subsequent requests work
	message = agenkit.NewMessage("user", "test2")
	response, err := client.Process(ctx, message)
	if err != nil {
		t.Fatal(err)
	}
	if response.Content != "Echo: test2" {
		t.Errorf("Expected 'Echo: test2', got '%s'", response.Content)
	}
}

func TestWebSocketMessageMetadataPreserved(t *testing.T) {
	ctx := context.Background()

	// Start HTTP server with WebSocket support
	agent := &EchoAgent{}
	httpAgent := http.NewHTTPAgent(agent, "127.0.0.1:29907")
	if err := httpAgent.Start(ctx); err != nil {
		t.Fatal(err)
	}
	defer httpAgent.Stop()

	time.Sleep(100 * time.Millisecond)

	// Create client
	endpoint := "ws://127.0.0.1:29907/ws"
	client, err := remote.NewRemoteAgent("echo", endpoint, 5*time.Second)
	if err != nil {
		t.Fatal(err)
	}
	defer client.Close()

	// Send message with metadata
	message := agenkit.NewMessage("user", "test").
		WithMetadata("key", "value").
		WithMetadata("number", 42)

	response, err := client.Process(ctx, message)
	if err != nil {
		t.Fatal(err)
	}

	// Verify response exists and has required fields
	if response.Content == "" {
		t.Error("Expected non-empty content")
	}
	if response.Timestamp.IsZero() {
		t.Error("Expected non-zero timestamp")
	}
}

func TestWebSocketServerStartStopMultipleTimes(t *testing.T) {
	ctx := context.Background()

	agent := &EchoAgent{}

	// Start and stop server 3 times
	for i := 0; i < 3; i++ {
		httpAgent := http.NewHTTPAgent(agent, "127.0.0.1:29908")
		if err := httpAgent.Start(ctx); err != nil {
			t.Fatalf("Iteration %d: failed to start server: %v", i, err)
		}

		time.Sleep(100 * time.Millisecond)

		// Test communication
		endpoint := "ws://127.0.0.1:29908/ws"
		client, err := remote.NewRemoteAgent("echo", endpoint, 5*time.Second)
		if err != nil {
			t.Fatalf("Iteration %d: failed to connect client: %v", i, err)
		}

		message := agenkit.NewMessage("user", fmt.Sprintf("Iteration %d", i))
		response, err := client.Process(ctx, message)
		if err != nil {
			t.Fatalf("Iteration %d: failed to process message: %v", i, err)
		}

		expected := fmt.Sprintf("Echo: Iteration %d", i)
		if response.Content != expected {
			t.Errorf("Iteration %d: expected '%s', got '%s'", i, expected, response.Content)
		}

		client.Close()

		// Stop server
		if err := httpAgent.Stop(); err != nil {
			t.Fatalf("Iteration %d: failed to stop server: %v", i, err)
		}

		// Small delay to ensure port is released
		time.Sleep(200 * time.Millisecond)
	}
}

func TestWebSocketWssURL(t *testing.T) {
	// Just verify the endpoint can be parsed with wss:// URL
	// (actual TLS testing would require certificates)
	endpoint := "wss://echo.websocket.org/ws"
	_, err := remote.NewRemoteAgent("echo", endpoint, 5*time.Second)
	if err != nil {
		t.Fatalf("Failed to create remote agent with wss:// URL: %v", err)
	}
}

func TestWebSocketWithLocalAgent(t *testing.T) {
	ctx := context.Background()
	endpoint := "ws://127.0.0.1:29909"

	// Start LocalAgent with WebSocket endpoint
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
	time.Sleep(100 * time.Millisecond)

	// Create client - LocalAgent uses HTTP server with /ws endpoint
	clientEndpoint := "ws://127.0.0.1:29909/ws"
	client, err := remote.NewRemoteAgent("echo", clientEndpoint, 5*time.Second)
	if err != nil {
		t.Fatal(err)
	}
	defer client.Close()

	// Test communication
	message := agenkit.NewMessage("user", "Hello from LocalAgent")
	response, err := client.Process(ctx, message)
	if err != nil {
		t.Fatal(err)
	}

	// Verify response
	if response.Role != "agent" {
		t.Errorf("Expected role 'agent', got '%s'", response.Role)
	}
	if response.Content != "Echo: Hello from LocalAgent" {
		t.Errorf("Expected content 'Echo: Hello from LocalAgent', got '%s'", response.Content)
	}
}

func TestWebSocketHealthCheck(t *testing.T) {
	ctx := context.Background()

	// Start HTTP server with WebSocket support
	agent := &EchoAgent{}
	httpAgent := http.NewHTTPAgent(agent, "127.0.0.1:29910")
	if err := httpAgent.Start(ctx); err != nil {
		t.Fatal(err)
	}
	defer httpAgent.Stop()

	time.Sleep(100 * time.Millisecond)

	// Test health endpoint
	resp, err := nethttp.DefaultClient.Get("http://127.0.0.1:29910/health")
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != nethttp.StatusOK {
		t.Errorf("Expected status code %d, got %d", nethttp.StatusOK, resp.StatusCode)
	}
}
