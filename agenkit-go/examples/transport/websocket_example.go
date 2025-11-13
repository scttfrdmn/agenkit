// WebSocket Transport Example.
//
// This example demonstrates the WebSocket transport for Agenkit, showing:
// - Setting up WebSocket server and client
// - Regular request/response communication
// - Streaming responses
// - Benefits of WebSocket over HTTP
//
// WHY USE WEBSOCKET?
// ==================
//
// WebSocket is ideal when you need:
//
// 1. **Bidirectional Communication**: Unlike HTTP, WebSocket maintains a persistent,
//    full-duplex connection allowing the server to push data to the client.
//
// 2. **Lower Latency**: After the initial handshake, WebSocket communication has
//    minimal overhead compared to HTTP's request/response cycle.
//
// 3. **Single Persistent Connection**: Eliminates the overhead of establishing
//    new connections for each request (as with HTTP).
//
// 4. **Real-time Applications**: Perfect for chat, live updates, streaming data,
//    and interactive applications.
//
// 5. **Better for Streaming**: Natural fit for streaming responses where the server
//    sends multiple chunks over time.
//
// WHEN TO USE EACH TRANSPORT:
// ===========================
//
// Use **WebSocket** when:
// - You need real-time, bidirectional communication
// - You're building interactive or streaming applications
// - You want lower latency for frequent communications
// - You need server-to-client push capabilities
//
// Use **HTTP** when:
// - You need simple request/response patterns
// - You want to leverage HTTP infrastructure (load balancers, caching, etc.)
// - You're exposing agents as REST APIs
// - Firewall/proxy compatibility is a concern
//
// Use **TCP** when:
// - You need maximum performance in a controlled network
// - You're building internal microservices
// - You want direct, low-level communication
// - You don't need HTTP semantics or WebSocket features
//
// Use **Unix Socket** when:
// - Communicating between processes on the same machine
// - You need the highest performance and security
// - You're building local development tools

package main

import (
	"context"
	"fmt"
	"strings"
	"time"

	"github.com/agenkit/agenkit-go/adapter/local"
	"github.com/agenkit/agenkit-go/adapter/remote"
	"github.com/agenkit/agenkit-go/agenkit"
)

// ChatAgent is a simple chat agent that responds to messages.
type ChatAgent struct{}

// Name returns the agent name.
func (c *ChatAgent) Name() string {
	return "chat"
}

// Process processes a single message and returns a complete response.
func (c *ChatAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	userMessage := strings.ToLower(message.Content)

	var response string
	if strings.Contains(userMessage, "hello") || strings.Contains(userMessage, "hi") {
		response = "Hello! I'm a chat agent. How can I help you today?"
	} else if strings.Contains(userMessage, "how are you") {
		response = "I'm doing great! Thanks for asking. How about you?"
	} else if strings.Contains(userMessage, "bye") || strings.Contains(userMessage, "goodbye") {
		response = "Goodbye! Have a great day!"
	} else if strings.Contains(userMessage, "help") {
		response = "I can respond to greetings, check how you're doing, or provide information. Try asking me something!"
	} else {
		response = fmt.Sprintf("You said: '%s'. That's interesting!", message.Content)
	}

	return agenkit.NewMessage("agent", response), nil
}

// Capabilities returns the agent capabilities.
func (c *ChatAgent) Capabilities() []string {
	return []string{}
}

// StoryAgent is an agent that streams a story in chunks.
type StoryAgent struct{}

// Name returns the agent name.
func (s *StoryAgent) Name() string {
	return "story"
}

// Process returns the complete story.
func (s *StoryAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	story := "Once upon a time, in a land of code and data, " +
		"there lived agents who processed messages. " +
		"They communicated over many transports, " +
		"but WebSocket was their favorite for real-time chat. " +
		"The End."
	return agenkit.NewMessage("agent", story), nil
}

// Stream streams the story one sentence at a time.
func (s *StoryAgent) Stream(ctx context.Context, message *agenkit.Message) (<-chan *agenkit.Message, <-chan error) {
	messageChan := make(chan *agenkit.Message)
	errorChan := make(chan error, 1)

	go func() {
		defer close(messageChan)
		defer close(errorChan)

		storyParts := []string{
			"Once upon a time, in a land of code and data,",
			"there lived agents who processed messages.",
			"They communicated over many transports:",
			"HTTP for simplicity, TCP for speed,",
			"Unix sockets for local efficiency,",
			"but WebSocket was their favorite for real-time chat.",
			"The persistent connection kept them together,",
			"and the low latency made conversations flow naturally.",
			"And they all lived happily ever after.",
			"The End.",
		}

		for i, part := range storyParts {
			// Simulate natural typing delay
			time.Sleep(300 * time.Millisecond)

			msg := agenkit.NewMessage("agent", part)
			msg.WithMetadata("part", i+1)
			msg.WithMetadata("total", len(storyParts))

			select {
			case messageChan <- msg:
			case <-ctx.Done():
				errorChan <- ctx.Err()
				return
			}
		}
	}()

	return messageChan, errorChan
}

// Capabilities returns the agent capabilities.
func (s *StoryAgent) Capabilities() []string {
	return []string{"streaming"}
}

// runChatExample demonstrates basic WebSocket request/response.
func runChatExample(ctx context.Context) error {
	printSeparator()
	fmt.Println("EXAMPLE 1: Basic Chat with WebSocket")
	printSeparator()
	fmt.Println()
	fmt.Println("Starting WebSocket server on ws://127.0.0.1:8765...")

	// Create and start server
	chatAgent := &ChatAgent{}
	server, err := local.NewLocalAgent(chatAgent, "ws://127.0.0.1:8765")
	if err != nil {
		return fmt.Errorf("failed to create server: %w", err)
	}

	if err := server.Start(ctx); err != nil {
		return fmt.Errorf("failed to start server: %w", err)
	}
	defer server.Stop()

	// Give server a moment to start
	time.Sleep(500 * time.Millisecond)

	// Create client
	remoteAgent, err := remote.NewRemoteAgent("chat", "ws://127.0.0.1:8765", 30*time.Second)
	if err != nil {
		return fmt.Errorf("failed to create client: %w", err)
	}
	defer remoteAgent.Close()

	fmt.Println("Client connected!")
	fmt.Println()

	// Have a conversation
	conversation := []string{
		"Hello!",
		"How are you?",
		"What can you do?",
		"Tell me something interesting.",
		"Goodbye!",
	}

	for _, userMsg := range conversation {
		fmt.Printf("User: %s\n", userMsg)
		message := agenkit.NewMessage("user", userMsg)
		response, err := remoteAgent.Process(ctx, message)
		if err != nil {
			return fmt.Errorf("process failed: %w", err)
		}
		fmt.Printf("Agent: %s\n\n", response.Content)

		// Small delay between messages
		time.Sleep(500 * time.Millisecond)
	}

	fmt.Println("Server stopped.")
	fmt.Println()
	return nil
}

// runStreamingExample demonstrates WebSocket streaming.
func runStreamingExample(ctx context.Context) error {
	printSeparator()
	fmt.Println("EXAMPLE 2: Streaming Story with WebSocket")
	printSeparator()
	fmt.Println()
	fmt.Println("Starting WebSocket server on ws://127.0.0.1:8766...")

	// Create and start server
	storyAgent := &StoryAgent{}
	server, err := local.NewLocalAgent(storyAgent, "ws://127.0.0.1:8766")
	if err != nil {
		return fmt.Errorf("failed to create server: %w", err)
	}

	if err := server.Start(ctx); err != nil {
		return fmt.Errorf("failed to start server: %w", err)
	}
	defer server.Stop()

	// Give server a moment to start
	time.Sleep(500 * time.Millisecond)

	// Create client
	remoteAgent, err := remote.NewRemoteAgent("story", "ws://127.0.0.1:8766", 30*time.Second)
	if err != nil {
		return fmt.Errorf("failed to create client: %w", err)
	}
	defer remoteAgent.Close()

	fmt.Println("Client connected!")
	fmt.Println()

	// First, get complete story (non-streaming)
	fmt.Println("--- Non-Streaming Mode ---")
	fmt.Println("User: Tell me a story")
	message := agenkit.NewMessage("user", "Tell me a story")
	response, err := remoteAgent.Process(ctx, message)
	if err != nil {
		return fmt.Errorf("process failed: %w", err)
	}
	fmt.Printf("Agent: %s\n\n", response.Content)

	time.Sleep(1 * time.Second)

	// Now, get story via streaming
	fmt.Println("--- Streaming Mode ---")
	fmt.Println("User: Tell me a story (streamed)")
	fmt.Print("Agent: ")

	message = agenkit.NewMessage("user", "Tell me a story")
	messageChan, errorChan := remoteAgent.Stream(ctx, message)

	for {
		select {
		case chunk, ok := <-messageChan:
			if !ok {
				// Channel closed, streaming complete
				fmt.Println()
				goto streamingDone
			}
			fmt.Printf("%s ", chunk.Content)

		case err, ok := <-errorChan:
			if ok && err != nil {
				return fmt.Errorf("streaming error: %w", err)
			}
		}
	}

streamingDone:
	fmt.Println()
	fmt.Println("\nServer stopped.")
	fmt.Println()
	return nil
}

// runConcurrentExample demonstrates concurrent WebSocket connections.
func runConcurrentExample(ctx context.Context) error {
	printSeparator()
	fmt.Println("EXAMPLE 3: Concurrent WebSocket Connections")
	printSeparator()
	fmt.Println()
	fmt.Println("Starting WebSocket server on ws://127.0.0.1:8767...")

	// Create and start server
	chatAgent := &ChatAgent{}
	server, err := local.NewLocalAgent(chatAgent, "ws://127.0.0.1:8767")
	if err != nil {
		return fmt.Errorf("failed to create server: %w", err)
	}

	if err := server.Start(ctx); err != nil {
		return fmt.Errorf("failed to start server: %w", err)
	}
	defer server.Stop()

	// Give server a moment to start
	time.Sleep(500 * time.Millisecond)

	fmt.Println("Creating 5 concurrent clients...")
	fmt.Println()

	// Create multiple clients
	type clientResult struct {
		clientID int
		response string
		err      error
	}

	results := make(chan clientResult, 5)

	for i := 0; i < 5; i++ {
		go func(clientID int) {
			remoteAgent, err := remote.NewRemoteAgent("chat", "ws://127.0.0.1:8767", 30*time.Second)
			if err != nil {
				results <- clientResult{clientID: clientID, err: err}
				return
			}
			defer remoteAgent.Close()

			message := agenkit.NewMessage("user", fmt.Sprintf("Hello from client %d", clientID))
			response, err := remoteAgent.Process(ctx, message)
			if err != nil {
				results <- clientResult{clientID: clientID, err: err}
				return
			}

			results <- clientResult{clientID: clientID, response: response.Content}
		}(i)
	}

	// Collect results
	for i := 0; i < 5; i++ {
		result := <-results
		if result.err != nil {
			return fmt.Errorf("client %d failed: %w", result.clientID, result.err)
		}
		fmt.Printf("Client %d: %s\n", result.clientID, result.response)
	}

	fmt.Println()
	fmt.Println("All clients completed successfully!")
	fmt.Println("Note: WebSocket maintains separate connections for each client,")
	fmt.Println("allowing true concurrent communication.")
	fmt.Println()
	fmt.Println("Server stopped.")
	fmt.Println()
	return nil
}

// runPersistenceExample demonstrates WebSocket connection persistence.
func runPersistenceExample(ctx context.Context) error {
	printSeparator()
	fmt.Println("EXAMPLE 4: Connection Persistence")
	printSeparator()
	fmt.Println()
	fmt.Println("Starting WebSocket server on ws://127.0.0.1:8768...")

	// Create and start server
	chatAgent := &ChatAgent{}
	server, err := local.NewLocalAgent(chatAgent, "ws://127.0.0.1:8768")
	if err != nil {
		return fmt.Errorf("failed to create server: %w", err)
	}

	if err := server.Start(ctx); err != nil {
		return fmt.Errorf("failed to start server: %w", err)
	}
	defer server.Stop()

	// Give server a moment to start
	time.Sleep(500 * time.Millisecond)

	// Create client
	remoteAgent, err := remote.NewRemoteAgent("chat", "ws://127.0.0.1:8768", 30*time.Second)
	if err != nil {
		return fmt.Errorf("failed to create client: %w", err)
	}
	defer remoteAgent.Close()

	fmt.Println("Client connected!")
	fmt.Println()
	fmt.Println("Sending 10 messages over the same persistent connection...")
	fmt.Println()

	// Send multiple messages over the same connection
	for i := 0; i < 10; i++ {
		message := agenkit.NewMessage("user", fmt.Sprintf("Message %d", i+1))
		response, err := remoteAgent.Process(ctx, message)
		if err != nil {
			return fmt.Errorf("process failed: %w", err)
		}
		fmt.Printf("  [%d/10] %s\n", i+1, response.Content)
	}

	fmt.Println()
	fmt.Println("All messages sent over a SINGLE WebSocket connection!")
	fmt.Println("(With HTTP, each request would need a new connection or keep-alive)")
	fmt.Println()
	fmt.Println("Server stopped.")
	fmt.Println()
	return nil
}

// printSeparator prints a separator line.
func printSeparator() {
	fmt.Println("======================================================================")
}

// printHeader prints the main header.
func printHeader() {
	fmt.Println()
	fmt.Println("╔════════════════════════════════════════════════════════════════════╗")
	fmt.Println("║                    WebSocket Transport Demo                        ║")
	fmt.Println("╚════════════════════════════════════════════════════════════════════╝")
	fmt.Println()
}

func main() {
	printHeader()

	ctx := context.Background()

	// Run examples
	if err := runChatExample(ctx); err != nil {
		fmt.Printf("Error in chat example: %v\n", err)
		return
	}

	time.Sleep(1 * time.Second)

	if err := runStreamingExample(ctx); err != nil {
		fmt.Printf("Error in streaming example: %v\n", err)
		return
	}

	time.Sleep(1 * time.Second)

	if err := runConcurrentExample(ctx); err != nil {
		fmt.Printf("Error in concurrent example: %v\n", err)
		return
	}

	time.Sleep(1 * time.Second)

	if err := runPersistenceExample(ctx); err != nil {
		fmt.Printf("Error in persistence example: %v\n", err)
		return
	}

	// Print summary
	printSeparator()
	fmt.Println("SUMMARY")
	printSeparator()
	fmt.Println()
	fmt.Println("WebSocket Benefits Demonstrated:")
	fmt.Println("  ✓ Persistent connection (Example 4)")
	fmt.Println("  ✓ Low-latency communication (All examples)")
	fmt.Println("  ✓ Excellent streaming support (Example 2)")
	fmt.Println("  ✓ Concurrent connections (Example 3)")
	fmt.Println("  ✓ Bidirectional communication capability")
	fmt.Println()
	fmt.Println("WebSocket is perfect for:")
	fmt.Println("  • Real-time applications (chat, live updates)")
	fmt.Println("  • Streaming AI responses (LLM outputs)")
	fmt.Println("  • Interactive agents")
	fmt.Println("  • Long-running conversations")
	fmt.Println()
	fmt.Println("For simple request/response, consider HTTP.")
	fmt.Println("For local inter-process communication, consider Unix sockets.")
	fmt.Println("For maximum performance in controlled networks, consider TCP.")
	fmt.Println()
}
