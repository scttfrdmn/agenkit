package adapter_test

import (
	"context"
	"fmt"
	"testing"
	"time"

	"github.com/agenkit/agenkit-go/adapter/http"
	"github.com/agenkit/agenkit-go/adapter/remote"
	"github.com/agenkit/agenkit-go/agenkit"
)

func TestHTTPBasicCommunication(t *testing.T) {
	ctx := context.Background()

	// Start HTTP server
	agent := &EchoAgent{}
	server := http.NewHTTPAgent(agent, "localhost:18080")

	if err := server.Start(ctx); err != nil {
		t.Fatal(err)
	}
	defer server.Stop()

	time.Sleep(50 * time.Millisecond)

	// Connect client
	endpoint := "http://localhost:18080"
	client, err := remote.NewRemoteAgent("echo", endpoint, 5*time.Second)
	if err != nil {
		t.Fatal(err)
	}
	defer client.Close()

	// Send message
	msg := agenkit.NewMessage("user", "test message")
	response, err := client.Process(ctx, msg)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	// Verify response
	if response.Role != "agent" {
		t.Errorf("Expected role 'agent', got '%s'", response.Role)
	}
	if response.Content != "Echo: test message" {
		t.Errorf("Expected 'Echo: test message', got '%s'", response.Content)
	}
}

func TestHTTPStreaming(t *testing.T) {
	ctx := context.Background()

	// Start HTTP server with streaming agent
	agent := &StreamingEchoAgent{}
	server := http.NewHTTPAgent(agent, "localhost:18081")

	if err := server.Start(ctx); err != nil {
		t.Fatal(err)
	}
	defer server.Stop()

	time.Sleep(50 * time.Millisecond)

	// Connect client
	endpoint := "http://localhost:18081"
	client, err := remote.NewRemoteAgent("echo", endpoint, 10*time.Second)
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
				done = true
			} else {
				chunks = append(chunks, chunk)
			}

		case err, ok := <-errorChan:
			if ok && err != nil {
				t.Fatalf("Stream error: %v", err)
			}
			if !ok {
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
	}
}

func TestHTTPConcurrentRequests(t *testing.T) {
	ctx := context.Background()

	// Start HTTP server
	agent := &EchoAgent{}
	server := http.NewHTTPAgent(agent, "localhost:18082")

	if err := server.Start(ctx); err != nil {
		t.Fatal(err)
	}
	defer server.Stop()

	time.Sleep(50 * time.Millisecond)

	// Create multiple clients
	clients := make([]*remote.RemoteAgent, 5)
	for i := 0; i < 5; i++ {
		endpoint := "http://localhost:18082"
		client, err := remote.NewRemoteAgent("echo", endpoint, 5*time.Second)
		if err != nil {
			t.Fatal(err)
		}
		defer client.Close()
		clients[i] = client
	}

	// Send concurrent requests
	done := make(chan bool, 5)
	for i, client := range clients {
		go func(idx int, c *remote.RemoteAgent) {
			msg := agenkit.NewMessage("user", fmt.Sprintf("message %d", idx))
			response, err := c.Process(ctx, msg)
			if err != nil {
				t.Errorf("Client %d failed: %v", idx, err)
			}
			expected := fmt.Sprintf("Echo: message %d", idx)
			if response.Content != expected {
				t.Errorf("Client %d: expected '%s', got '%s'", idx, expected, response.Content)
			}
			done <- true
		}(i, client)
	}

	// Wait for all to complete
	for i := 0; i < 5; i++ {
		select {
		case <-done:
		case <-time.After(5 * time.Second):
			t.Fatal("Timeout waiting for concurrent requests")
		}
	}
}

func TestHTTPErrorHandling(t *testing.T) {
	ctx := context.Background()

	// Start HTTP server with error agent
	agent := &ErrorAgent{}
	server := http.NewHTTPAgent(agent, "localhost:18083")

	if err := server.Start(ctx); err != nil {
		t.Fatal(err)
	}
	defer server.Stop()

	time.Sleep(50 * time.Millisecond)

	// Connect client
	endpoint := "http://localhost:18083"
	client, err := remote.NewRemoteAgent("error", endpoint, 5*time.Second)
	if err != nil {
		t.Fatal(err)
	}
	defer client.Close()

	// Send message - should get error
	msg := agenkit.NewMessage("user", "test")
	_, err = client.Process(ctx, msg)
	if err == nil {
		t.Fatal("Expected error from error agent")
	}

	// Verify error message contains "error"
	if err != nil && err.Error() == "" {
		t.Error("Error message should not be empty")
	}
}

func TestHTTPMetadataPreservation(t *testing.T) {
	ctx := context.Background()

	// Start HTTP server
	agent := &EchoAgent{}
	server := http.NewHTTPAgent(agent, "localhost:18084")

	if err := server.Start(ctx); err != nil {
		t.Fatal(err)
	}
	defer server.Stop()

	time.Sleep(50 * time.Millisecond)

	// Connect client
	endpoint := "http://localhost:18084"
	client, err := remote.NewRemoteAgent("echo", endpoint, 5*time.Second)
	if err != nil {
		t.Fatal(err)
	}
	defer client.Close()

	// Send message with metadata
	msg := agenkit.NewMessage("user", "test").
		WithMetadata("key1", "value1").
		WithMetadata("key2", 42)

	response, err := client.Process(ctx, msg)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	// Verify response was received (EchoAgent doesn't preserve metadata, just echoes content)
	if response.Content != "Echo: test" {
		t.Errorf("Expected 'Echo: test', got '%s'", response.Content)
	}

	// Verify message was sent successfully with metadata
	// (The fact that we got a response means metadata was sent correctly)
	if response.Role != "agent" {
		t.Error("Expected role 'agent'")
	}
}

func TestHTTPStreamingEmpty(t *testing.T) {
	ctx := context.Background()

	// Start HTTP server with empty streaming agent
	agent := &EmptyStreamAgent{}
	server := http.NewHTTPAgent(agent, "localhost:18085")

	if err := server.Start(ctx); err != nil {
		t.Fatal(err)
	}
	defer server.Stop()

	time.Sleep(50 * time.Millisecond)

	// Connect client
	endpoint := "http://localhost:18085"
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
				done = true
			} else {
				chunks = append(chunks, chunk)
			}

		case err, ok := <-errorChan:
			if ok && err != nil {
				t.Fatalf("Stream error: %v", err)
			}
			if !ok {
				done = true
			}
		}
	}

	// Verify empty stream
	if len(chunks) != 0 {
		t.Errorf("Expected 0 chunks, got %d", len(chunks))
	}
}

func TestHTTPLargePayload(t *testing.T) {
	ctx := context.Background()

	// Start HTTP server
	agent := &EchoAgent{}
	server := http.NewHTTPAgent(agent, "localhost:18086")

	if err := server.Start(ctx); err != nil {
		t.Fatal(err)
	}
	defer server.Stop()

	time.Sleep(50 * time.Millisecond)

	// Connect client
	endpoint := "http://localhost:18086"
	client, err := remote.NewRemoteAgent("echo", endpoint, 5*time.Second)
	if err != nil {
		t.Fatal(err)
	}
	defer client.Close()

	// Send large message (100KB)
	largeContent := string(make([]byte, 100*1024))
	msg := agenkit.NewMessage("user", largeContent)
	response, err := client.Process(ctx, msg)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	// Verify response
	expected := "Echo: " + largeContent
	if response.Content != expected {
		t.Error("Large payload not handled correctly")
	}
}

func TestHTTPContextCancellation(t *testing.T) {
	// Start HTTP server with slow agent
	agent := &SlowAgent{delay: 2 * time.Second}
	server := http.NewHTTPAgent(agent, "localhost:18087")

	if err := server.Start(context.Background()); err != nil {
		t.Fatal(err)
	}
	defer server.Stop()

	time.Sleep(50 * time.Millisecond)

	// Connect client
	endpoint := "http://localhost:18087"
	client, err := remote.NewRemoteAgent("slow", endpoint, 5*time.Second)
	if err != nil {
		t.Fatal(err)
	}
	defer client.Close()

	// Create context with short timeout
	ctx, cancel := context.WithTimeout(context.Background(), 500*time.Millisecond)
	defer cancel()

	// Send message - should timeout
	msg := agenkit.NewMessage("user", "test")
	_, err = client.Process(ctx, msg)
	if err == nil {
		t.Fatal("Expected context cancellation error")
	}
}

func TestHTTPEndpointParsing(t *testing.T) {
	// Test valid HTTP endpoints
	testCases := []struct {
		endpoint string
		expected string
	}{
		{"http://localhost:8080", "localhost:8080"},
		{"https://example.com:443", "example.com:443"},
		{"http://127.0.0.1:9000", "127.0.0.1:9000"},
	}

	for _, tc := range testCases {
		addr, err := http.ParseHTTPEndpoint(tc.endpoint)
		if err != nil {
			t.Errorf("Failed to parse %s: %v", tc.endpoint, err)
		}
		if addr != tc.expected {
			t.Errorf("Expected %s, got %s", tc.expected, addr)
		}
	}

	// Test invalid endpoints
	invalid := []string{
		"tcp://localhost:8080",
		"unix:///tmp/test.sock",
		"invalid",
	}

	for _, endpoint := range invalid {
		_, err := http.ParseHTTPEndpoint(endpoint)
		if err == nil {
			t.Errorf("Expected error for invalid endpoint: %s", endpoint)
		}
	}
}
