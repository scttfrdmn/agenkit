// Test client for integration testing
package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"time"

	"github.com/agenkit/agenkit-go/adapter/remote"
	"github.com/agenkit/agenkit-go/agenkit"
)

func main() {
	url := flag.String("url", "http://localhost:8080", "Server URL")
	message := flag.String("message", "Hello", "Message to send")
	flag.Parse()

	// Create remote agent client
	client := remote.NewRemoteAgent(*url)

	// Create message
	msg := agenkit.NewMessage("user", *message)

	// Send message with timeout
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	response, err := client.Process(ctx, msg)
	if err != nil {
		log.Fatalf("Failed to process message: %v", err)
	}

	// Print response (will be parsed by Python test)
	fmt.Printf("Response: %s\n", response.Content)
	if lang, ok := response.Metadata["language"]; ok {
		fmt.Printf("Language: %v\n", lang)
	}
	if original, ok := response.Metadata["original"]; ok {
		fmt.Printf("Original: %v\n", original)
	}
}
