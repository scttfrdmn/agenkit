package main

import (
	"flag"
	"log"
	"os"
	"os/signal"
	"syscall"

	agenkit "github.com/agenkit/agenkit-go"
	"github.com/agenkit/agenkit-go/adapters/go/grpc"
	"github.com/agenkit/customer-support-worker/internal/agent"
)

func main() {
	// Parse command-line flags
	port := flag.Int("port", 50051, "gRPC server port")
	flag.Parse()

	log.Printf("Starting Customer Support Go Worker on port %d", *port)

	// Create specialist agent
	specialist := agent.NewSpecialistAgent()

	log.Printf("Specialist agent initialized: %s", specialist.Name())
	log.Printf("Capabilities: %v", specialist.Capabilities())

	// Create gRPC server
	server, err := grpc.NewGRPCServer(specialist, *port)
	if err != nil {
		log.Fatalf("Failed to create gRPC server: %v", err)
	}

	// Start server in goroutine
	go func() {
		log.Printf("gRPC server listening on :%d", *port)
		if err := server.Start(); err != nil {
			log.Fatalf("Failed to start server: %v", err)
		}
	}()

	// Wait for interrupt signal
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	<-sigChan
	log.Println("Shutting down server...")

	if err := server.Stop(); err != nil {
		log.Printf("Error stopping server: %v", err)
	}

	log.Println("Server stopped")
}
