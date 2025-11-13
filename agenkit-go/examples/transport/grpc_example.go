// gRPC Transport Example
//
// This example demonstrates the gRPC transport for Agenkit, showing:
// - Setting up gRPC server and client
// - Regular request/response communication
// - Streaming responses
// - Concurrent clients
// - Metadata handling
// - Error handling and recovery
//
// WHY USE GRPC?
// ==============
//
// gRPC is ideal when you need:
//
// 1. **High Performance**: gRPC uses HTTP/2 and Protocol Buffers for efficient
//    binary encoding, making it significantly faster than JSON-based protocols.
//
// 2. **Strong Typing**: Protocol Buffers provide strongly-typed schemas that are
//    validated at compile time, reducing runtime errors.
//
// 3. **Bidirectional Streaming**: Built-in support for client streaming, server
//    streaming, and bidirectional streaming over a single connection.
//
// 4. **Language Interoperability**: gRPC has native support for many languages,
//    making it perfect for polyglot microservices.
//
// 5. **Built-in Features**: Native support for authentication, load balancing,
//    retries, timeouts, and health checks.
//
// 6. **Connection Multiplexing**: HTTP/2 enables multiple concurrent RPC calls
//    over a single TCP connection.
//
// WHEN TO USE EACH TRANSPORT:
// ============================
//
// Use **gRPC** when:
// - You need high-performance RPC for microservices
// - You're building polyglot systems (Python, Go, Java, etc.)
// - You want strong typing and code generation
// - You need advanced features like streaming, retries, load balancing
// - Performance and scalability are critical
//
// Use **WebSocket** when:
// - You need real-time bidirectional communication
// - You're building browser-based applications
// - You want simpler deployment (works through HTTP proxies)
//
// Use **HTTP** when:
// - You need simple REST APIs
// - You want maximum compatibility
// - You're exposing public APIs
//
// Use **TCP/Unix Sockets** when:
// - You need raw socket communication
// - You're building internal tools
// - You don't need gRPC's advanced features

package main

import (
	"context"
	"fmt"
	"log"
	"sync"
	"time"

	"github.com/agenkit/agenkit-go/adapter/grpc"
	"github.com/agenkit/agenkit-go/adapter/remote"
	"github.com/agenkit/agenkit-go/adapter/transport"
	"github.com/agenkit/agenkit-go/agenkit"
)

// EchoAgent is a simple agent that echoes back messages.
type EchoAgent struct{}

func (e *EchoAgent) Name() string {
	return "echo"
}

func (e *EchoAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	return agenkit.NewMessage("agent", "Echo: "+message.Content).
		WithMetadata("original", message.Content), nil
}

func (e *EchoAgent) Capabilities() []string {
	return []string{"echo"}
}

// StreamingEchoAgent is an echo agent that streams response word-by-word.
type StreamingEchoAgent struct{}

func (s *StreamingEchoAgent) Name() string {
	return "streaming_echo"
}

func (s *StreamingEchoAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	return agenkit.NewMessage("agent", "Echo: "+message.Content), nil
}

func (s *StreamingEchoAgent) Stream(ctx context.Context, message *agenkit.Message) (<-chan *agenkit.Message, <-chan error) {
	messageChan := make(chan *agenkit.Message)
	errorChan := make(chan error, 1)

	go func() {
		defer close(messageChan)
		defer close(errorChan)

		// Split content into words
		words := splitWords(message.Content)

		for i, word := range words {
			select {
			case <-ctx.Done():
				errorChan <- ctx.Err()
				return
			case <-time.After(100 * time.Millisecond): // Simulate processing delay
				msg := agenkit.NewMessage("agent", word).
					WithMetadata("word_index", i).
					WithMetadata("total_words", len(words))

				select {
				case messageChan <- msg:
				case <-ctx.Done():
					errorChan <- ctx.Err()
					return
				}
			}
		}
	}()

	return messageChan, errorChan
}

func (s *StreamingEchoAgent) Capabilities() []string {
	return []string{"echo", "stream"}
}

// MetadataAgent processes and returns metadata.
type MetadataAgent struct{}

func (m *MetadataAgent) Name() string {
	return "metadata"
}

func (m *MetadataAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	metadata := message.Metadata
	if metadata == nil {
		metadata = make(map[string]interface{})
	}

	// Add response metadata
	responseMetadata := map[string]interface{}{
		"received_at":    time.Now().Unix(),
		"message_length": len(message.Content),
		"user_metadata":  metadata,
		"processed_by":   m.Name(),
	}

	response := agenkit.NewMessage("agent", "Processed: "+message.Content)
	for k, v := range responseMetadata {
		response.WithMetadata(k, v)
	}

	return response, nil
}

func (m *MetadataAgent) Capabilities() []string {
	return []string{"metadata"}
}

// Helper function to split string into words
func splitWords(s string) []string {
	var words []string
	var word []rune

	for _, r := range s {
		if r == ' ' || r == '\t' || r == '\n' {
			if len(word) > 0 {
				words = append(words, string(word))
				word = nil
			}
		} else {
			word = append(word, r)
		}
	}

	if len(word) > 0 {
		words = append(words, string(word))
	}

	return words
}

// scenario1BasicCommunication demonstrates basic gRPC communication.
//
// WHY: Demonstrate the simplest gRPC usage pattern - unary RPC where
// the client sends a single request and receives a single response.
// This is the foundation of gRPC communication.
func scenario1BasicCommunication() {
	fmt.Println("=" + repeat("=", 69))
	fmt.Println("SCENARIO 1: Basic gRPC Communication")
	fmt.Println("=" + repeat("=", 69))
	fmt.Println()
	fmt.Println("Starting gRPC server on localhost:50051...")

	ctx := context.Background()

	// Create and start gRPC server
	agent := &EchoAgent{}
	server, err := grpc.NewGRPCServer(agent, "localhost:50051")
	if err != nil {
		log.Fatalf("Failed to create server: %v", err)
	}

	if err := server.Start(); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
	defer server.Stop()

	// Give server time to start
	time.Sleep(200 * time.Millisecond)

	fmt.Println("Server started! Creating client...")
	fmt.Println()

	// Create gRPC transport
	trans, err := transport.NewGRPCTransport("grpc://localhost:50051")
	if err != nil {
		log.Fatalf("Failed to create transport: %v", err)
	}

	if err := trans.Connect(ctx); err != nil {
		log.Fatalf("Failed to connect: %v", err)
	}
	defer trans.Close()

	// Create remote agent using the transport
	remoteAgent := remote.NewRemoteAgentWithTransport("echo", trans, 5*time.Second)
	defer remoteAgent.Close()

	// Send messages
	messages := []string{
		"Hello, gRPC!",
		"This is fast and efficient.",
		"Protocol Buffers are awesome!",
	}

	for _, msgContent := range messages {
		fmt.Printf("User: %s\n", msgContent)
		message := agenkit.NewMessage("user", msgContent)
		response, err := remoteAgent.Process(ctx, message)
		if err != nil {
			log.Fatalf("Failed to process message: %v", err)
		}

		fmt.Printf("Agent: %s\n", response.Content)
		fmt.Printf("Metadata: %v\n\n", response.Metadata)
	}

	fmt.Println("Benefits demonstrated:")
	fmt.Println("  - Simple request/response pattern")
	fmt.Println("  - Efficient binary encoding (Protocol Buffers)")
	fmt.Println("  - Type-safe communication")
	fmt.Println()
}

// scenario2StreamingResponses demonstrates streaming over gRPC.
//
// WHY: Show how gRPC efficiently handles streaming data. Unlike HTTP
// where you'd need SSE or polling, gRPC has native streaming support
// with HTTP/2, making it perfect for real-time data delivery.
func scenario2StreamingResponses() {
	fmt.Println("=" + repeat("=", 69))
	fmt.Println("SCENARIO 2: Streaming Responses over gRPC")
	fmt.Println("=" + repeat("=", 69))
	fmt.Println()
	fmt.Println("Starting gRPC server on localhost:50052...")

	ctx := context.Background()

	// Create and start gRPC server
	agent := &StreamingEchoAgent{}
	server, err := grpc.NewGRPCServer(agent, "localhost:50052")
	if err != nil {
		log.Fatalf("Failed to create server: %v", err)
	}

	if err := server.Start(); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
	defer server.Stop()

	// Give server time to start
	time.Sleep(200 * time.Millisecond)

	fmt.Println("Server started! Creating client...")
	fmt.Println()

	// Create gRPC transport
	trans, err := transport.NewGRPCTransport("grpc://localhost:50052")
	if err != nil {
		log.Fatalf("Failed to create transport: %v", err)
	}

	if err := trans.Connect(ctx); err != nil {
		log.Fatalf("Failed to connect: %v", err)
	}
	defer trans.Close()

	// Create remote agent
	remoteAgent := remote.NewRemoteAgentWithTransport("streaming_echo", trans, 10*time.Second)
	defer remoteAgent.Close()

	// Test non-streaming first
	fmt.Println("--- Non-Streaming Mode ---")
	message := agenkit.NewMessage("user", "The quick brown fox jumps")
	fmt.Printf("User: %s\n", message.Content)
	response, err := remoteAgent.Process(ctx, message)
	if err != nil {
		log.Fatalf("Failed to process message: %v", err)
	}
	fmt.Printf("Agent: %s\n\n", response.Content)

	time.Sleep(500 * time.Millisecond)

	// Test streaming
	fmt.Println("--- Streaming Mode ---")
	message = agenkit.NewMessage("user", "gRPC streaming is efficient and fast")
	fmt.Printf("User: %s\n", message.Content)
	fmt.Print("Agent: ")

	startTime := time.Now()
	messageChan, errorChan := remoteAgent.Stream(ctx, message)

	for {
		select {
		case chunk, ok := <-messageChan:
			if !ok {
				// Channel closed, streaming complete
				elapsed := time.Since(startTime).Seconds()
				fmt.Printf("\n\nStreaming completed in %.2fs\n", elapsed)
				goto streamDone
			}
			fmt.Printf("%s ", chunk.Content)

		case err, ok := <-errorChan:
			if ok && err != nil {
				log.Fatalf("Streaming error: %v", err)
			}
		}
	}

streamDone:
	fmt.Println()
	fmt.Println("Benefits demonstrated:")
	fmt.Println("  - Native streaming support over HTTP/2")
	fmt.Println("  - Low latency for real-time data")
	fmt.Println("  - Single connection for entire stream")
	fmt.Println("  - Efficient for large responses")
	fmt.Println()
}

// scenario3ConcurrentClients demonstrates multiple concurrent clients.
//
// WHY: Demonstrate gRPC's ability to handle multiple concurrent requests
// efficiently. HTTP/2 connection multiplexing allows many concurrent RPCs
// over a single TCP connection, reducing overhead.
func scenario3ConcurrentClients() {
	fmt.Println("=" + repeat("=", 69))
	fmt.Println("SCENARIO 3: Multiple Concurrent Clients")
	fmt.Println("=" + repeat("=", 69))
	fmt.Println()
	fmt.Println("Starting gRPC server on localhost:50053...")

	ctx := context.Background()

	// Create and start gRPC server
	agent := &EchoAgent{}
	server, err := grpc.NewGRPCServer(agent, "localhost:50053")
	if err != nil {
		log.Fatalf("Failed to create server: %v", err)
	}

	if err := server.Start(); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
	defer server.Stop()

	// Give server time to start
	time.Sleep(200 * time.Millisecond)

	fmt.Println("Server started! Creating multiple concurrent clients...")
	fmt.Println()

	// Create multiple clients
	numClients := 10

	sendRequest := func(clientID int, wg *sync.WaitGroup) {
		defer wg.Done()

		// Each client creates its own transport
		trans, err := transport.NewGRPCTransport("grpc://localhost:50053")
		if err != nil {
			log.Printf("Client %d: Failed to create transport: %v", clientID, err)
			return
		}

		if err := trans.Connect(ctx); err != nil {
			log.Printf("Client %d: Failed to connect: %v", clientID, err)
			return
		}
		defer trans.Close()

		remoteAgent := remote.NewRemoteAgentWithTransport("echo", trans, 5*time.Second)
		defer remoteAgent.Close()

		message := agenkit.NewMessage("user", fmt.Sprintf("Message from client %d", clientID))

		start := time.Now()
		response, err := remoteAgent.Process(ctx, message)
		elapsed := time.Since(start)

		if err != nil {
			log.Printf("Client %d: Error: %v", clientID, err)
			return
		}

		fmt.Printf("Client %2d: %s (took %.1fms)\n", clientID, response.Content, elapsed.Seconds()*1000)
	}

	// Send concurrent requests
	startTime := time.Now()
	var wg sync.WaitGroup
	wg.Add(numClients)

	for i := 0; i < numClients; i++ {
		go sendRequest(i, &wg)
	}

	wg.Wait()
	totalTime := time.Since(startTime)

	fmt.Printf("\nAll %d clients completed in %.2fs\n", numClients, totalTime.Seconds())
	fmt.Printf("Average time per request: %.1fms\n", (totalTime.Seconds()/float64(numClients))*1000)

	fmt.Println()
	fmt.Println("Benefits demonstrated:")
	fmt.Println("  - Connection multiplexing over HTTP/2")
	fmt.Println("  - Efficient handling of concurrent requests")
	fmt.Println("  - Low per-request overhead")
	fmt.Println("  - Scalable for many clients")
	fmt.Println()
}

// scenario4MetadataHandling demonstrates metadata handling.
//
// WHY: Show how gRPC preserves and propagates metadata through calls.
// This is useful for tracing, authentication, request context, and
// passing additional information without modifying the message schema.
func scenario4MetadataHandling() {
	fmt.Println("=" + repeat("=", 69))
	fmt.Println("SCENARIO 4: Metadata Handling")
	fmt.Println("=" + repeat("=", 69))
	fmt.Println()
	fmt.Println("Starting gRPC server on localhost:50054...")

	ctx := context.Background()

	// Create and start gRPC server
	agent := &MetadataAgent{}
	server, err := grpc.NewGRPCServer(agent, "localhost:50054")
	if err != nil {
		log.Fatalf("Failed to create server: %v", err)
	}

	if err := server.Start(); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
	defer server.Stop()

	// Give server time to start
	time.Sleep(200 * time.Millisecond)

	fmt.Println("Server started! Creating client...")
	fmt.Println()

	// Create gRPC transport
	trans, err := transport.NewGRPCTransport("grpc://localhost:50054")
	if err != nil {
		log.Fatalf("Failed to create transport: %v", err)
	}

	if err := trans.Connect(ctx); err != nil {
		log.Fatalf("Failed to connect: %v", err)
	}
	defer trans.Close()

	// Create remote agent
	remoteAgent := remote.NewRemoteAgentWithTransport("metadata", trans, 5*time.Second)
	defer remoteAgent.Close()

	// Send messages with metadata
	testCases := []struct {
		content  string
		metadata map[string]interface{}
	}{
		{
			content: "Request with user ID",
			metadata: map[string]interface{}{
				"user_id": "user123",
				"session": "abc-def",
			},
		},
		{
			content: "Request with trace ID",
			metadata: map[string]interface{}{
				"trace_id": "trace-456",
				"priority": "high",
			},
		},
		{
			content: "Request with custom headers",
			metadata: map[string]interface{}{
				"custom":  "value",
				"version": "1.0",
			},
		},
	}

	for i, test := range testCases {
		fmt.Printf("--- Test %d ---\n", i+1)
		fmt.Printf("User: %s\n", test.content)
		fmt.Printf("Input metadata: %v\n", test.metadata)

		message := agenkit.NewMessage("user", test.content)
		for k, v := range test.metadata {
			message.WithMetadata(k, v)
		}

		response, err := remoteAgent.Process(ctx, message)
		if err != nil {
			log.Fatalf("Failed to process message: %v", err)
		}

		fmt.Printf("Agent: %s\n", response.Content)
		fmt.Printf("Response metadata: %v\n\n", response.Metadata)
	}

	fmt.Println("Benefits demonstrated:")
	fmt.Println("  - Metadata propagation through gRPC calls")
	fmt.Println("  - Useful for tracing, authentication, context")
	fmt.Println("  - Preserved across the call chain")
	fmt.Println()
}

// scenario5ErrorHandling demonstrates error handling and recovery.
//
// WHY: Demonstrate how gRPC errors are handled gracefully, with proper
// error codes and details. gRPC has rich error handling with standard
// status codes, making it easier to handle failures properly.
func scenario5ErrorHandling() {
	fmt.Println("=" + repeat("=", 69))
	fmt.Println("SCENARIO 5: Error Handling and Recovery")
	fmt.Println("=" + repeat("=", 69))
	fmt.Println()

	ctx := context.Background()

	// Test 1: Connection to unavailable server
	fmt.Println("--- Test 1: Connection to unavailable server ---")
	func() {
		trans, err := transport.NewGRPCTransport("grpc://localhost:59999")
		if err != nil {
			fmt.Printf("ERROR during setup: %v\n", err)
			return
		}

		if err := trans.Connect(ctx); err != nil {
			fmt.Printf("ERROR: %v\n", err)
			return
		}
		defer trans.Close()

		remoteAgent := remote.NewRemoteAgentWithTransport("echo", trans, 2*time.Second)
		defer remoteAgent.Close()

		message := agenkit.NewMessage("user", "Hello")

		// This should work initially (gRPC channels are lazy)
		fmt.Println("Connected to gRPC channel (lazy connection)")

		// But the actual RPC will fail
		timeoutCtx, cancel := context.WithTimeout(ctx, 2*time.Second)
		defer cancel()

		response, err := remoteAgent.Process(timeoutCtx, message)
		if err != nil {
			fmt.Printf("ERROR: %v\n", err)
		} else {
			fmt.Printf("Unexpected success: %s\n", response.Content)
		}
	}()
	fmt.Println()

	// Test 2: Server shutdown during communication
	fmt.Println("--- Test 2: Server shutdown during communication ---")
	agent := &EchoAgent{}
	server, err := grpc.NewGRPCServer(agent, "localhost:50055")
	if err != nil {
		log.Fatalf("Failed to create server: %v", err)
	}

	if err := server.Start(); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
	fmt.Println("Server started")

	// Give server time to start
	time.Sleep(200 * time.Millisecond)

	func() {
		trans, err := transport.NewGRPCTransport("grpc://localhost:50055")
		if err != nil {
			log.Printf("Failed to create transport: %v", err)
			return
		}

		if err := trans.Connect(ctx); err != nil {
			log.Printf("Failed to connect: %v", err)
			return
		}
		defer trans.Close()

		remoteAgent := remote.NewRemoteAgentWithTransport("echo", trans, 2*time.Second)
		defer remoteAgent.Close()

		// Send successful request
		message := agenkit.NewMessage("user", "First request")
		response, err := remoteAgent.Process(ctx, message)
		if err != nil {
			fmt.Printf("ERROR: %v\n", err)
		} else {
			fmt.Printf("Success: %s\n", response.Content)
		}

		// Stop server
		fmt.Println("Stopping server...")
		server.Stop()
		time.Sleep(500 * time.Millisecond)

		// Try to send another request
		fmt.Println("Attempting request to stopped server...")
		timeoutCtx, cancel := context.WithTimeout(ctx, 2*time.Second)
		defer cancel()

		message = agenkit.NewMessage("user", "Second request")
		response, err = remoteAgent.Process(timeoutCtx, message)
		if err != nil {
			fmt.Printf("ERROR: %v\n", err)
		} else {
			fmt.Printf("Unexpected success: %s\n", response.Content)
		}
	}()
	fmt.Println()

	// Test 3: Retry and recovery
	fmt.Println("--- Test 3: Retry and recovery ---")
	server, err = grpc.NewGRPCServer(agent, "localhost:50056")
	if err != nil {
		log.Fatalf("Failed to create server: %v", err)
	}

	if err := server.Start(); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
	defer server.Stop()
	fmt.Println("Server started")

	// Give server time to start
	time.Sleep(200 * time.Millisecond)

	func() {
		trans, err := transport.NewGRPCTransport("grpc://localhost:50056")
		if err != nil {
			log.Printf("Failed to create transport: %v", err)
			return
		}

		if err := trans.Connect(ctx); err != nil {
			log.Printf("Failed to connect: %v", err)
			return
		}
		defer trans.Close()

		remoteAgent := remote.NewRemoteAgentWithTransport("echo", trans, 2*time.Second)
		defer remoteAgent.Close()

		// Implement simple retry logic
		maxRetries := 3
		for attempt := 0; attempt < maxRetries; attempt++ {
			timeoutCtx, cancel := context.WithTimeout(ctx, 2*time.Second)

			message := agenkit.NewMessage("user", fmt.Sprintf("Attempt %d", attempt+1))
			response, err := remoteAgent.Process(timeoutCtx, message)
			cancel()

			if err == nil {
				fmt.Printf("Success on attempt %d: %s\n", attempt+1, response.Content)
				break
			}

			fmt.Printf("Attempt %d failed: %v\n", attempt+1, err)
			if attempt < maxRetries-1 {
				fmt.Println("Retrying...")
				time.Sleep(500 * time.Millisecond)
			} else {
				fmt.Println("Max retries reached")
			}
		}
	}()

	fmt.Println()
	fmt.Println("Benefits demonstrated:")
	fmt.Println("  - Graceful error handling with gRPC status codes")
	fmt.Println("  - Clear error messages and details")
	fmt.Println("  - Support for retry patterns")
	fmt.Println("  - Connection state awareness")
	fmt.Println()
}

func main() {
	fmt.Println()
	fmt.Println("╔" + repeat("═", 68) + "╗")
	fmt.Println("║" + repeat(" ", 23) + "gRPC Transport Demo" + repeat(" ", 26) + "║")
	fmt.Println("╚" + repeat("═", 68) + "╝")
	fmt.Println()

	// Run scenarios
	scenario1BasicCommunication()
	time.Sleep(1 * time.Second)

	scenario2StreamingResponses()
	time.Sleep(1 * time.Second)

	scenario3ConcurrentClients()
	time.Sleep(1 * time.Second)

	scenario4MetadataHandling()
	time.Sleep(1 * time.Second)

	scenario5ErrorHandling()

	// Print summary
	fmt.Println("=" + repeat("=", 69))
	fmt.Println("SUMMARY")
	fmt.Println("=" + repeat("=", 69))
	fmt.Println()
	fmt.Println("gRPC Benefits Demonstrated:")
	fmt.Println("  ✓ High-performance binary protocol (Protocol Buffers)")
	fmt.Println("  ✓ Strong typing and schema validation")
	fmt.Println("  ✓ Native streaming support (Scenario 2)")
	fmt.Println("  ✓ Efficient concurrent handling (Scenario 3)")
	fmt.Println("  ✓ Metadata propagation (Scenario 4)")
	fmt.Println("  ✓ Rich error handling (Scenario 5)")
	fmt.Println("  ✓ HTTP/2 connection multiplexing")
	fmt.Println("  ✓ Language interoperability")
	fmt.Println()
	fmt.Println("gRPC is perfect for:")
	fmt.Println("  • High-performance microservices")
	fmt.Println("  • Polyglot system architectures")
	fmt.Println("  • Internal APIs requiring low latency")
	fmt.Println("  • Streaming data (real-time updates, AI responses)")
	fmt.Println("  • Service-to-service communication")
	fmt.Println()
	fmt.Println("Performance characteristics:")
	fmt.Println("  • ~10x faster than JSON over HTTP for binary data")
	fmt.Println("  • Lower CPU usage due to efficient encoding")
	fmt.Println("  • Reduced network bandwidth")
	fmt.Println("  • Better support for high concurrency")
	fmt.Println()
	fmt.Println("For browser-based apps, consider WebSocket.")
	fmt.Println("For public REST APIs, consider HTTP.")
	fmt.Println("For maximum performance in controlled environments, use gRPC.")
	fmt.Println()
}

// Helper function to repeat a string n times
func repeat(s string, n int) string {
	result := ""
	for i := 0; i < n; i++ {
		result += s
	}
	return result
}
