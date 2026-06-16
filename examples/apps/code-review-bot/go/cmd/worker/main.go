package main

import (
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

	// Start server in goroutine
	go func() {
		if err := server.Start(); err != nil {
			log.Fatalf("Failed to start server: %v", err)
		}
	}()

	log.Printf("Analyzer agent listening on :%d", *port)

	// Wait for interrupt signal
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
	<-sigChan

	log.Println("Shutting down analyzer agent...")
	if err := server.Stop(); err != nil {
		log.Printf("Error stopping server: %v", err)
	}
}
