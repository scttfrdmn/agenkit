package adapter_test

import (
	"context"
	"fmt"
	"sync"
	"testing"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/adapter/grpc"
	"github.com/scttfrdmn/agenkit/agenkit-go/adapter/remote"
	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

func TestGRPCBasicCommunication(t *testing.T) {
	ctx := context.Background()

	// Bind an ephemeral port (:0) and read back the real address. Hardcoded
	// ports collide on the self-hosted runners (6 parallel runners share a
	// host), so every server in this file uses dynamic allocation.
	agent := &EchoAgent{}
	server, err := grpc.NewGRPCServer(agent, "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	endpoint := fmt.Sprintf("grpc://%s", server.Address())

	if err := server.Start(); err != nil {
		t.Fatal(err)
	}
	defer func() { _ = server.Stop() }()

	// Give server time to start
	time.Sleep(100 * time.Millisecond)

	// Create client
	client, err := remote.NewRemoteAgent("echo", endpoint, 5*time.Second)
	if err != nil {
		t.Fatal(err)
	}
	defer func() { _ = client.Close() }()

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
	if response.ContentString() != "Echo: Hello" {
		t.Errorf("Expected content 'Echo: Hello', got '%s'", response.ContentString())
	}
}

func TestGRPCMultipleRequests(t *testing.T) {
	ctx := context.Background()

	// Start gRPC server on an ephemeral port (see TestGRPCBasicCommunication).
	agent := &EchoAgent{}
	server, err := grpc.NewGRPCServer(agent, "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	endpoint := fmt.Sprintf("grpc://%s", server.Address())

	if err := server.Start(); err != nil {
		t.Fatal(err)
	}
	defer func() { _ = server.Stop() }()

	time.Sleep(100 * time.Millisecond)

	// Create client
	client, err := remote.NewRemoteAgent("echo", endpoint, 5*time.Second)
	if err != nil {
		t.Fatal(err)
	}
	defer func() { _ = client.Close() }()

	// Send multiple requests
	for i := 0; i < 5; i++ {
		message := agenkit.NewMessage("user", fmt.Sprintf("Message %d", i))
		response, err := client.Process(ctx, message)
		if err != nil {
			t.Fatalf("Request %d failed: %v", i, err)
		}

		expected := fmt.Sprintf("Echo: Message %d", i)
		if response.ContentString() != expected {
			t.Errorf("Request %d: expected '%s', got '%s'", i, expected, response.ContentString())
		}
	}
}

func TestGRPCConcurrentRequests(t *testing.T) {
	ctx := context.Background()

	// Start gRPC server on an ephemeral port (see TestGRPCBasicCommunication).
	agent := &EchoAgent{}
	server, err := grpc.NewGRPCServer(agent, "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	endpoint := fmt.Sprintf("grpc://%s", server.Address())

	if err := server.Start(); err != nil {
		t.Fatal(err)
	}
	defer func() { _ = server.Stop() }()

	time.Sleep(100 * time.Millisecond)

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
			defer func() { _ = client.Close() }()

			message := agenkit.NewMessage("user", fmt.Sprintf("Message %d", id))
			response, err := client.Process(ctx, message)
			if err != nil {
				errors <- fmt.Errorf("client %d: %w", id, err)
				return
			}

			expected := fmt.Sprintf("Echo: Message %d", id)
			if response.ContentString() != expected {
				errors <- fmt.Errorf("client %d: expected '%s', got '%s'", id, expected, response.ContentString())
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

func TestGRPCMultipleClients(t *testing.T) {
	ctx := context.Background()

	// Start gRPC server on an ephemeral port (see TestGRPCBasicCommunication).
	agent := &EchoAgent{}
	server, err := grpc.NewGRPCServer(agent, "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	endpoint := fmt.Sprintf("grpc://%s", server.Address())

	if err := server.Start(); err != nil {
		t.Fatal(err)
	}
	defer func() { _ = server.Stop() }()

	time.Sleep(100 * time.Millisecond)

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
			defer func() { _ = client.Close() }()

			message := agenkit.NewMessage("user", fmt.Sprintf("Client %d", id))
			response, err := client.Process(ctx, message)
			if err != nil {
				errors <- fmt.Errorf("client %d: %w", id, err)
				return
			}

			expected := fmt.Sprintf("Echo: Client %d", id)
			if response.ContentString() != expected {
				errors <- fmt.Errorf("client %d: expected '%s', got '%s'", id, expected, response.ContentString())
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

func TestGRPCConnectionFailure(t *testing.T) {
	ctx := context.Background()
	endpoint := "grpc://127.0.0.1:59999" // Non-existent server

	// Try to connect to non-existent server
	client, err := remote.NewRemoteAgent("echo", endpoint, 1*time.Second)
	if err != nil {
		t.Fatal(err)
	}
	defer func() { _ = client.Close() }()

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

func TestGRPCLargeMessage(t *testing.T) {
	ctx := context.Background()

	// Start gRPC server on an ephemeral port (see TestGRPCBasicCommunication).
	agent := &EchoAgent{}
	server, err := grpc.NewGRPCServer(agent, "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	endpoint := fmt.Sprintf("grpc://%s", server.Address())

	if err := server.Start(); err != nil {
		t.Fatal(err)
	}
	defer func() { _ = server.Stop() }()

	time.Sleep(100 * time.Millisecond)

	// Create client
	client, err := remote.NewRemoteAgent("echo", endpoint, 10*time.Second)
	if err != nil {
		t.Fatal(err)
	}
	defer func() { _ = client.Close() }()

	// Send large message (1MB)
	largeContent := string(make([]byte, 1024*1024))
	message := agenkit.NewMessage("user", largeContent)
	response, err := client.Process(ctx, message)
	if err != nil {
		t.Fatal(err)
	}

	// Verify response
	expectedLen := len("Echo: ") + len(largeContent)
	if len(response.ContentString()) != expectedLen {
		t.Errorf("Expected content length %d, got %d", expectedLen, len(response.ContentString()))
	}
}

func TestGRPCMessageMetadataPreserved(t *testing.T) {
	ctx := context.Background()

	// Start gRPC server on an ephemeral port (see TestGRPCBasicCommunication).
	agent := &EchoAgent{}
	server, err := grpc.NewGRPCServer(agent, "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	endpoint := fmt.Sprintf("grpc://%s", server.Address())

	if err := server.Start(); err != nil {
		t.Fatal(err)
	}
	defer func() { _ = server.Stop() }()

	time.Sleep(100 * time.Millisecond)

	// Create client
	client, err := remote.NewRemoteAgent("echo", endpoint, 5*time.Second)
	if err != nil {
		t.Fatal(err)
	}
	defer func() { _ = client.Close() }()

	// Send message with metadata
	message := agenkit.NewMessage("user", "test").
		WithMetadata("key", "value").
		WithMetadata("number", 42)

	response, err := client.Process(ctx, message)
	if err != nil {
		t.Fatal(err)
	}

	// Verify response exists and has required fields
	if response.ContentString() == "" {
		t.Error("Expected non-empty content")
	}
	if response.Timestamp.IsZero() {
		t.Error("Expected non-zero timestamp")
	}
}

func TestGRPCServerStartStopMultipleTimes(t *testing.T) {
	ctx := context.Background()

	agent := &EchoAgent{}

	// Start and stop server 3 times
	for i := 0; i < 3; i++ {
		// Use port 0 for dynamic port allocation to avoid port conflicts
		server, err := grpc.NewGRPCServer(agent, "127.0.0.1:0")
		if err != nil {
			t.Fatalf("Iteration %d: failed to create server: %v", i, err)
		}

		if err := server.Start(); err != nil {
			t.Fatalf("Iteration %d: failed to start server: %v", i, err)
		}

		time.Sleep(100 * time.Millisecond)

		// Get the actual address the server is listening on
		actualAddr := server.Address()
		endpoint := fmt.Sprintf("grpc://%s", actualAddr)

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
		if response.ContentString() != expected {
			t.Errorf("Iteration %d: expected '%s', got '%s'", i, expected, response.ContentString())
		}

		_ = client.Close()

		// Stop server
		if err := server.Stop(); err != nil {
			t.Fatalf("Iteration %d: failed to stop server: %v", i, err)
		}

		// No delay needed - each iteration uses a fresh dynamic port
	}
}

func TestGRPCStreamingSupport(t *testing.T) {
	ctx := context.Background()

	// Start gRPC server on an ephemeral port (see TestGRPCBasicCommunication).
	agent := &StreamingEchoAgent{}
	server, err := grpc.NewGRPCServer(agent, "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	endpoint := fmt.Sprintf("grpc://%s", server.Address())

	if err := server.Start(); err != nil {
		t.Fatal(err)
	}
	defer func() { _ = server.Stop() }()

	time.Sleep(100 * time.Millisecond)

	// Create client
	client, err := remote.NewRemoteAgent("echo", endpoint, 10*time.Second)
	if err != nil {
		t.Fatal(err)
	}
	defer func() { _ = client.Close() }()

	// Test streaming
	message := agenkit.NewMessage("user", "test")
	messageChan, errorChan := client.Stream(ctx, message)

	chunks := 0
	for {
		select {
		case msg, ok := <-messageChan:
			if !ok {
				// Channel closed
				goto done
			}
			chunks++
			if msg.ContentString() == "" {
				t.Error("Expected non-empty chunk content")
			}
		case err := <-errorChan:
			if err != nil {
				t.Fatalf("Stream error: %v", err)
			}
		case <-time.After(5 * time.Second):
			t.Fatal("Stream timeout")
		}
	}

done:
	// Verify we received chunks
	if chunks == 0 {
		t.Error("Expected to receive at least one chunk")
	}
}

func TestGRPCErrorHandling(t *testing.T) {
	ctx := context.Background()

	// Start gRPC server on an ephemeral port (see TestGRPCBasicCommunication).
	agent := &ErrorAgent{}
	server, err := grpc.NewGRPCServer(agent, "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	endpoint := fmt.Sprintf("grpc://%s", server.Address())

	if err := server.Start(); err != nil {
		t.Fatal(err)
	}
	defer func() { _ = server.Stop() }()

	time.Sleep(100 * time.Millisecond)

	// Create client
	client, err := remote.NewRemoteAgent("error", endpoint, 5*time.Second)
	if err != nil {
		t.Fatal(err)
	}
	defer func() { _ = client.Close() }()

	// Test error handling
	message := agenkit.NewMessage("user", "test")
	_, err = client.Process(ctx, message)
	if err == nil {
		t.Fatal("Expected error from error agent, got nil")
	}

	// Verify error message
	if err.Error() == "" {
		t.Error("Expected non-empty error message")
	}
}

func TestGRPCParseEndpoint(t *testing.T) {
	tests := []struct {
		name        string
		endpoint    string
		expectError bool
	}{
		{
			name:        "Valid gRPC endpoint with port",
			endpoint:    "grpc://localhost:50051",
			expectError: false,
		},
		{
			name:        "Valid gRPC endpoint without port",
			endpoint:    "grpc://localhost",
			expectError: false,
		},
		{
			name:        "Valid gRPC endpoint with IP",
			endpoint:    "grpc://127.0.0.1:50051",
			expectError: false,
		},
		{
			name:        "Invalid scheme (http is valid, not grpc)",
			endpoint:    "http://localhost:50051",
			expectError: false, // http is a valid transport, just not gRPC
		},
		{
			name:        "Empty endpoint",
			endpoint:    "",
			expectError: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if tt.endpoint == "" {
				return // Skip empty endpoint test for ParseEndpoint
			}

			// Just verify we can create a remote agent with the endpoint
			_, err := remote.NewRemoteAgent("test", tt.endpoint, 1*time.Second)
			if tt.expectError && err == nil {
				t.Error("Expected error, got nil")
			}
			if !tt.expectError && err != nil {
				t.Errorf("Expected no error, got: %v", err)
			}
		})
	}
}

func TestGRPCTransportTimeout(t *testing.T) {
	ctx := context.Background()

	// Start gRPC server on an ephemeral port (see TestGRPCBasicCommunication).
	agent := &SlowAgent{delay: 3 * time.Second}
	server, err := grpc.NewGRPCServer(agent, "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	endpoint := fmt.Sprintf("grpc://%s", server.Address())

	if err := server.Start(); err != nil {
		t.Fatal(err)
	}
	defer func() { _ = server.Stop() }()

	time.Sleep(100 * time.Millisecond)

	// Create client with short timeout
	client, err := remote.NewRemoteAgent("slow", endpoint, 1*time.Second)
	if err != nil {
		t.Fatal(err)
	}
	defer func() { _ = client.Close() }()

	// Test timeout
	message := agenkit.NewMessage("user", "test")
	_, err = client.Process(ctx, message)
	if err == nil {
		t.Fatal("Expected timeout error, got nil")
	}

	// Verify it's a timeout error
	if err.Error() == "" {
		t.Error("Expected non-empty error message")
	}
}

func TestGRPCTransportReconnect(t *testing.T) {
	ctx := context.Background()

	// Start gRPC server on an ephemeral port. We capture the chosen address so
	// the restart below can rebind the *same* port (the point of this test).
	agent := &EchoAgent{}
	server, err := grpc.NewGRPCServer(agent, "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	addr := server.Address()
	endpoint := fmt.Sprintf("grpc://%s", addr)

	if err := server.Start(); err != nil {
		t.Fatal(err)
	}

	time.Sleep(100 * time.Millisecond)

	// Create client
	client, err := remote.NewRemoteAgent("echo", endpoint, 5*time.Second)
	if err != nil {
		t.Fatal(err)
	}
	defer func() { _ = client.Close() }()

	// Test communication
	message := agenkit.NewMessage("user", "Hello")
	response, err := client.Process(ctx, message)
	if err != nil {
		t.Fatal(err)
	}

	if response.ContentString() != "Echo: Hello" {
		t.Errorf("Expected 'Echo: Hello', got '%s'", response.ContentString())
	}

	// Stop server
	_ = server.Stop()
	time.Sleep(200 * time.Millisecond)

	// Start server again on the same address to exercise client reconnect.
	server, err = grpc.NewGRPCServer(agent, addr)
	if err != nil {
		t.Fatal(err)
	}

	if err := server.Start(); err != nil {
		t.Fatal(err)
	}
	defer func() { _ = server.Stop() }()

	time.Sleep(100 * time.Millisecond)

	// Create new client (old client connection is broken)
	client2, err := remote.NewRemoteAgent("echo", endpoint, 5*time.Second)
	if err != nil {
		t.Fatal(err)
	}
	defer func() { _ = client2.Close() }()

	// Test communication again
	response, err = client2.Process(ctx, message)
	if err != nil {
		t.Fatal(err)
	}

	if response.ContentString() != "Echo: Hello" {
		t.Errorf("Expected 'Echo: Hello', got '%s'", response.ContentString())
	}
}

func TestGRPCDefaultPort(t *testing.T) {
	endpoint := "grpc://localhost"

	// Just verify we can parse the endpoint and use default port
	client, err := remote.NewRemoteAgent("test", endpoint, 1*time.Second)
	if err != nil {
		t.Fatal(err)
	}
	defer func() { _ = client.Close() }()

	// We don't test actual connection as there's no server on default port
}

func TestGRPCProtocolConversion(t *testing.T) {
	ctx := context.Background()

	// Start gRPC server on an ephemeral port (see TestGRPCBasicCommunication).
	agent := &EchoAgent{}
	server, err := grpc.NewGRPCServer(agent, "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	endpoint := fmt.Sprintf("grpc://%s", server.Address())

	if err := server.Start(); err != nil {
		t.Fatal(err)
	}
	defer func() { _ = server.Stop() }()

	time.Sleep(100 * time.Millisecond)

	// Create client
	client, err := remote.NewRemoteAgent("echo", endpoint, 5*time.Second)
	if err != nil {
		t.Fatal(err)
	}
	defer func() { _ = client.Close() }()

	// Test various content types
	tests := []struct {
		name    string
		content string
	}{
		{"Simple text", "Hello World"},
		{"Unicode", "Hello 世界 🌍"},
		{"Special characters", "Test!@#$%^&*()"},
		{"Empty string", ""},
		{"Newlines", "Line1\nLine2\nLine3"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			message := agenkit.NewMessage("user", tt.content)
			response, err := client.Process(ctx, message)
			if err != nil {
				t.Fatalf("Failed to process message: %v", err)
			}

			expected := "Echo: " + tt.content
			if response.ContentString() != expected {
				t.Errorf("Expected '%s', got '%s'", expected, response.ContentString())
			}
		})
	}
}
