// Command worker serves the Go scraper agent over gRPC.
//
// This is the binary the tree's Dockerfile builds (`go build -o scraper
// ./cmd/worker`) and that docker-compose.yml runs as the `go-scraper` service.
// It did not exist: the Dockerfile and compose file referenced a package that had
// never been written, so `docker-compose up --build` — the only command this
// example's README gives — could not succeed (#857).
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
	"github.com/scttfrdmn/agenkit/examples/research-assistant-scraper/internal/agent"
)

func main() {
	port := flag.Int("port", 50051, "gRPC server port")
	flag.Parse()

	scraper := agent.NewScraperAgent()

	log.Printf("Starting research-assistant scraper %q on port %d", scraper.Name(), *port)
	log.Printf("Capabilities: %v", scraper.Capabilities())

	server, err := grpc.NewGRPCServer(scraper, fmt.Sprintf(":%d", *port))
	if err != nil {
		log.Fatalf("Failed to create gRPC server: %v", err)
	}

	// Start is non-blocking and shuts down when ctx is cancelled, so tie ctx to
	// SIGINT/SIGTERM — docker stop sends SIGTERM.
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	if err := server.Start(ctx); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}

	log.Printf("Scraper listening on :%d", *port)

	<-ctx.Done()
	log.Println("Shutting down scraper...")

	if err := server.Stop(); err != nil {
		log.Printf("Error stopping server: %v", err)
	}

	log.Println("Scraper stopped")
}
