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
	"github.com/scttfrdmn/agenkit/examples/code-review-bot/internal/agent"
)

func main() {
	port := flag.Int("port", 50051, "gRPC server port")
	flag.Parse()

	log.Printf("Starting code review analyzer on port %d", *port)

	// Create analyzer agent
	analyzer := agent.NewAnalyzerAgent()

	// Create gRPC server
	server, err := grpc.NewGRPCServer(analyzer, fmt.Sprintf(":%d", *port))
	if err != nil {
		log.Fatalf("Failed to create server: %v", err)
	}

	// Start the server. Start is non-blocking and takes the context whose
	// cancellation shuts it down, so wire that context to SIGINT/SIGTERM rather
	// than launching it in a goroutine and watching signals separately.
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	if err := server.Start(ctx); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}

	log.Printf("Analyzer agent listening on :%d", *port)

	<-ctx.Done()

	log.Println("Shutting down analyzer agent...")
	if err := server.Stop(); err != nil {
		log.Printf("Error stopping server: %v", err)
	}
}
