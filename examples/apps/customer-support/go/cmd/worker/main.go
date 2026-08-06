package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"os"
	"os/signal"
	"syscall"

	"github.com/scttfrdmn/agenkit/agenkit-go/adapter/grpc"
	"github.com/scttfrdmn/agenkit/examples/customer-support-worker/internal/agent"
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
	server, err := grpc.NewGRPCServer(specialist, fmt.Sprintf(":%d", *port))
	if err != nil {
		log.Fatalf("Failed to create gRPC server: %v", err)
	}

	// Start the server. Start is non-blocking and takes the context whose
	// cancellation shuts it down, so wire that context to SIGINT/SIGTERM rather
	// than launching it in a goroutine and watching signals separately.
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	if err := server.Start(ctx); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
	log.Printf("gRPC server listening on :%d", *port)

	<-ctx.Done()
	log.Println("Shutting down server...")

	if err := server.Stop(); err != nil {
		log.Printf("Error stopping server: %v", err)
	}

	log.Println("Server stopped")
}
