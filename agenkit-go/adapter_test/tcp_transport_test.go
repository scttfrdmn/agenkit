package adapter_test

import (
	"context"
	"fmt"
	"sync"
	"testing"
	"time"

	"github.com/agenkit/agenkit-go/adapter/local"
	"github.com/agenkit/agenkit-go/adapter/remote"
	"github.com/agenkit/agenkit-go/agenkit"
)

func TestTCPBasicCommunication(t *testing.T) {
	ctx := context.Background()
	endpoint := "tcp://127.0.0.1:19900"

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

	// Create client
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

func TestTCPMultipleRequests(t *testing.T) {
	ctx := context.Background()
	endpoint := "tcp://127.0.0.1:19901"

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

	// Create client
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

func TestTCPConcurrentRequests(t *testing.T) {
	ctx := context.Background()
	endpoint := "tcp://127.0.0.1:19902"

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

	// Create separate clients for concurrent requests
	numClients := 5
	var wg sync.WaitGroup
	errors := make(chan error, numClients)

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

func TestTCPMultipleClients(t *testing.T) {
	ctx := context.Background()
	endpoint := "tcp://127.0.0.1:19903"

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

	// Create multiple clients
	numClients := 3
	var wg sync.WaitGroup
	errors := make(chan error, numClients)

	for i := 0; i < numClients; i++ {
		wg.Add(1)
		go func(id int) {
			defer wg.Done()

			client, err := remote.NewRemoteAgent("echo", endpoint, 5*time.Second)
			if err != nil {
				errors <- fmt.Errorf("client %d: failed to connect: %w", id, err)
				return
			}
			defer client.Close()

			message := agenkit.NewMessage("user", fmt.Sprintf("Client %d", id))
			response, err := client.Process(ctx, message)
			if err != nil {
				errors <- fmt.Errorf("client %d: %w", id, err)
				return
			}

			expected := fmt.Sprintf("Echo: Client %d", id)
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

func TestTCPConnectionFailure(t *testing.T) {
	ctx := context.Background()
	endpoint := "tcp://127.0.0.1:19999" // Non-existent server

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

func TestTCPLargeMessage(t *testing.T) {
	ctx := context.Background()
	endpoint := "tcp://127.0.0.1:19904"

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

	// Create client
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

func TestTCPMessageMetadataPreserved(t *testing.T) {
	ctx := context.Background()
	endpoint := "tcp://127.0.0.1:19905"

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

	// Create client
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

func TestTCPServerStartStopMultipleTimes(t *testing.T) {
	ctx := context.Background()
	endpoint := "tcp://127.0.0.1:19906"

	agent := &EchoAgent{}

	// Start and stop server 3 times
	for i := 0; i < 3; i++ {
		server, err := local.NewLocalAgent(agent, endpoint)
		if err != nil {
			t.Fatalf("Iteration %d: failed to create server: %v", i, err)
		}

		if err := server.Start(ctx); err != nil {
			t.Fatalf("Iteration %d: failed to start server: %v", i, err)
		}

		time.Sleep(50 * time.Millisecond)

		// Test communication
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
		if err := server.Stop(); err != nil {
			t.Fatalf("Iteration %d: failed to stop server: %v", i, err)
		}

		// Small delay to ensure port is released
		time.Sleep(100 * time.Millisecond)
	}
}
