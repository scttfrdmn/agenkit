// Basic example demonstrating the Go protocol adapter.
//
// This example shows:
// - Creating a simple echo agent
// - Exposing it via Unix socket
// - Connecting to it remotely
// - Sending and receiving messages
package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"time"

	"github.com/agenkit/agenkit-go/adapter/local"
	"github.com/agenkit/agenkit-go/adapter/remote"
	"github.com/agenkit/agenkit-go/agenkit"
)

// EchoAgent is a simple agent that echoes back messages.
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

// GreetingAgent returns a personalized greeting.
type GreetingAgent struct{}

func (g *GreetingAgent) Name() string {
	return "greeter"
}

func (g *GreetingAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	greeting := fmt.Sprintf("Hello, %s! Welcome to agenkit-go.", message.Content)
	return agenkit.NewMessage("agent", greeting), nil
}

func (g *GreetingAgent) Capabilities() []string {
	return []string{"greet"}
}

func main() {
	fmt.Println("=== Go Protocol Adapter - Basic Example ===")

	// Create temporary directory for Unix sockets
	tmpDir, err := os.MkdirTemp("", "agenkit-go-example-*")
	if err != nil {
		log.Fatal(err)
	}
	defer os.RemoveAll(tmpDir)

	ctx := context.Background()

	// Example 1: Echo agent with Unix socket
	fmt.Println("1. Echo Agent - Unix Socket")
	fmt.Println("-" + "--------------------------------------------")

	// Start echo server
	echoAgent := &EchoAgent{}
	echoSocket := filepath.Join(tmpDir, "echo.sock")
	echoServer, err := local.NewLocalAgent(echoAgent, fmt.Sprintf("unix://%s", echoSocket))
	if err != nil {
		log.Fatal(err)
	}

	if err := echoServer.Start(ctx); err != nil {
		log.Fatal(err)
	}

	// Give server a moment to start
	time.Sleep(100 * time.Millisecond)

	// Connect remote client
	remoteEcho, err := remote.NewRemoteAgent("echo", fmt.Sprintf("unix://%s", echoSocket), 5*time.Second)
	if err != nil {
		log.Fatal(err)
	}

	// Send messages
	messages := []string{"Hello", "How are you?", "Goodbye"}
	for _, content := range messages {
		msg := agenkit.NewMessage("user", content)
		fmt.Printf("User: %s\n", content)

		response, err := remoteEcho.Process(ctx, msg)
		if err != nil {
			log.Fatal(err)
		}

		fmt.Printf("Agent: %s\n\n", response.Content)
	}

	// Stop echo server
	if err := echoServer.Stop(); err != nil {
		log.Fatal(err)
	}

	// Example 2: Greeter agent with TCP
	fmt.Println("\n2. Greeter Agent - TCP")
	fmt.Println("----------------------------------------------")

	// Start greeter server on TCP
	greeterAgent := &GreetingAgent{}
	greeterServer, err := local.NewLocalAgent(greeterAgent, "tcp://127.0.0.1:9876")
	if err != nil {
		log.Fatal(err)
	}

	if err := greeterServer.Start(ctx); err != nil {
		log.Fatal(err)
	}

	// Give server a moment to start
	time.Sleep(100 * time.Millisecond)

	// Connect remote client
	remoteGreeter, err := remote.NewRemoteAgent("greeter", "tcp://127.0.0.1:9876", 5*time.Second)
	if err != nil {
		log.Fatal(err)
	}

	// Send messages
	names := []string{"Alice", "Bob", "Charlie"}
	for _, name := range names {
		msg := agenkit.NewMessage("user", name)
		fmt.Printf("User: %s\n", name)

		response, err := remoteGreeter.Process(ctx, msg)
		if err != nil {
			log.Fatal(err)
		}

		fmt.Printf("Agent: %s\n\n", response.Content)
	}

	// Stop greeter server
	if err := greeterServer.Stop(); err != nil {
		log.Fatal(err)
	}

	// Example 3: Message metadata
	fmt.Println("\n3. Message Metadata")
	fmt.Println("----------------------------------------------")

	// Start echo server again
	echoSocket2 := filepath.Join(tmpDir, "echo2.sock")
	echoServer2, err := local.NewLocalAgent(echoAgent, fmt.Sprintf("unix://%s", echoSocket2))
	if err != nil {
		log.Fatal(err)
	}

	if err := echoServer2.Start(ctx); err != nil {
		log.Fatal(err)
	}

	// Give server a moment to start
	time.Sleep(100 * time.Millisecond)

	remoteEcho2, err := remote.NewRemoteAgent("echo", fmt.Sprintf("unix://%s", echoSocket2), 5*time.Second)
	if err != nil {
		log.Fatal(err)
	}

	// Send message with metadata
	msg := agenkit.NewMessage("user", "Test message").
		WithMetadata("priority", "high").
		WithMetadata("tags", []string{"test", "demo"})

	fmt.Printf("Sending message with metadata:\n")
	fmt.Printf("  Content: %s\n", msg.Content)
	fmt.Printf("  Metadata: %v\n\n", msg.Metadata)

	response, err := remoteEcho2.Process(ctx, msg)
	if err != nil {
		log.Fatal(err)
	}

	fmt.Printf("Received response:\n")
	fmt.Printf("  Content: %s\n", response.Content)
	fmt.Printf("  Role: %s\n", response.Role)
	fmt.Printf("  Timestamp: %s\n", response.Timestamp.Format(time.RFC3339))

	// Stop server
	if err := echoServer2.Stop(); err != nil {
		log.Fatal(err)
	}

	fmt.Println("\nDone!")
}
