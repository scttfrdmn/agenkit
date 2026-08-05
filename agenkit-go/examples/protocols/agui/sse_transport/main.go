// SSE Transport with Human-in-the-Loop Example
//
// Demonstrates AG-UI protocol over HTTP Server-Sent Events (SSE) transport
// with human-in-the-loop approval workflow.
//
// This example shows:
//   - HTTP server with AGUISSEHandler
//   - Browser-friendly SSE streaming
//   - HITL integration with interrupts over SSE
//   - CORS support for web frontends
//   - Real-world deployment pattern
//
// The server exposes:
//   - POST /chat - SSE endpoint for agent communication
//   - GET /health - Health check endpoint
//
// Usage:
//
//	go run 02_sse_transport_hitl.go
//
// Then from another terminal:
//
//	curl -X POST http://localhost:8080/chat \
//	  -H "Content-Type: application/json" \
//	  -d '{"message": "What is 2+2?"}' \
//	  -N
package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/patterns"
	"github.com/scttfrdmn/agenkit/agenkit-go/protocols/agui"
	"github.com/scttfrdmn/agenkit/agenkit-go/protocols/agui/transports"
)

// DemoAgent is an agent that returns responses with configurable confidence.
type DemoAgent struct {
	name              string
	defaultConfidence float64
}

func NewDemoAgent(name string, confidence float64) *DemoAgent {
	return &DemoAgent{
		name:              name,
		defaultConfidence: confidence,
	}
}

func (d *DemoAgent) Name() string {
	return d.name
}

func (d *DemoAgent) Capabilities() []string {
	return []string{"chat", "analysis", "calculation"}
}

func (d *DemoAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	log.Printf("🤖 Agent processing: %s", message.ContentString())

	// Simulate processing time
	time.Sleep(200 * time.Millisecond)

	// Determine confidence based on message content
	confidence := d.defaultConfidence
	content := message.ContentString()

	// High confidence for simple math
	if len(content) < 20 {
		confidence = 0.95
	}
	// Low confidence for complex or unclear requests
	if len(content) > 50 || contains(content, []string{"maybe", "unsure", "risky"}) {
		confidence = 0.4
	}

	response := agenkit.NewMessage("assistant", fmt.Sprintf("Analysis of '%s': This requires careful consideration based on the context and available information.", content))
	response.Metadata = map[string]interface{}{
		"confidence":    confidence,
		"processing_ms": 200,
		"timestamp":     time.Now().UTC().Format(time.RFC3339),
	}

	log.Printf("✅ Response generated (confidence: %.2f)", confidence)
	return response, nil
}

func (d *DemoAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:     d.name,
		Capabilities:  d.Capabilities(),
		InternalState: make(map[string]interface{}),
		Metadata: map[string]interface{}{
			"default_confidence": d.defaultConfidence,
		},
	}
}

// logApprovalFunc logs approval requests and auto-approves after delay.
func logApprovalFunc(ctx context.Context, request *patterns.ApprovalRequest) (*patterns.ApprovalResponse, error) {
	confidence := request.Confidence
	log.Printf("👤 APPROVAL REQUESTED")
	log.Printf("   Confidence: %.2f", confidence)
	log.Printf("   Message: %s", request.Message.ContentString())
	log.Printf("   Agent: %v", request.Context["agent"])
	log.Printf("   Threshold: %v", request.Context["approval_threshold"])

	// Simulate human decision time
	time.Sleep(500 * time.Millisecond)

	// Auto-approve for demo (in production, this would be interactive)
	approved := confidence >= 0.3 // Approve if not extremely low
	if approved {
		log.Println("   ✅ AUTO-APPROVED (confidence acceptable)")
		return &patterns.ApprovalResponse{
			Approved: true,
			Feedback: fmt.Sprintf("Approved - confidence %.2f is acceptable", confidence),
		}, nil
	}

	log.Println("   ❌ AUTO-REJECTED (confidence too low)")
	return &patterns.ApprovalResponse{
		Approved: false,
		Feedback: fmt.Sprintf("Rejected - confidence %.2f is too low", confidence),
	}, nil
}

// healthHandler provides a simple health check endpoint.
func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	if _, err := fmt.Fprintf(w, `{"status":"ok","service":"agui-sse-hitl","timestamp":"%s"}`, time.Now().UTC().Format(time.RFC3339)); err != nil {
		log.Printf("Error writing health check: %v", err)
	}
}

// contains checks if string contains any of the substrings.
func contains(s string, substrs []string) bool {
	for _, substr := range substrs {
		if len(s) >= len(substr) {
			for i := 0; i <= len(s)-len(substr); i++ {
				if s[i:i+len(substr)] == substr {
					return true
				}
			}
		}
	}
	return false
}

func main() {
	log.SetFlags(log.LstdFlags | log.Lmicroseconds)
	log.Println("🚀 Starting AG-UI SSE Transport with HITL Example")

	// Create base agent
	baseAgent := NewDemoAgent("DemoAgent", 0.7)
	log.Printf("📦 Created base agent: %s", baseAgent.Name())

	// Wrap with HumanInLoopAgent
	hilAgent, err := patterns.NewHumanInLoopAgent(&patterns.HumanInLoopConfig{
		Agent:             baseAgent,
		ApprovalFunc:      logApprovalFunc,
		ApprovalThreshold: 0.8, // Require approval when confidence < 0.8
	})
	if err != nil {
		log.Fatalf("❌ Failed to create HumanInLoopAgent: %v", err)
	}
	log.Println("🛡️  Created HumanInLoopAgent (threshold: 0.8)")

	// Create HITL adapter
	hilAdapter := agui.NewAGUIHumanInLoopAdapter(hilAgent, "SSE-HITL-Demo", true)
	log.Println("🔌 Created AGUIHumanInLoopAdapter")

	// Create SSE handler with HITL support
	config := transports.AGUISSEHandlerConfig{
		Adapter:           hilAdapter,    // Use HITL adapter for Interrupt events
		IncludeEventNames: false,         // Standard SSE format
		CORSOrigins:       []string{"*"}, // Allow all origins (restrict in production)
		Timeout:           30 * time.Second,
		PingInterval:      5 * time.Second,
	}

	sseHandler := transports.NewAGUISSEHandler(nil, config) // Agent is nil when Adapter is provided
	log.Println("📡 Created SSE handler with HITL support")

	// Set up HTTP server
	mux := http.NewServeMux()
	mux.Handle("/chat", sseHandler)
	mux.HandleFunc("/health", healthHandler)

	server := &http.Server{
		Addr:         ":8080",
		Handler:      mux,
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 60 * time.Second,
		IdleTimeout:  120 * time.Second,
	}

	// Start server in goroutine
	go func() {
		log.Println("🌐 Server starting on http://localhost:8080")
		log.Println("📍 Endpoints:")
		log.Println("   POST /chat   - SSE streaming endpoint")
		log.Println("   GET  /health - Health check")
		log.Println()
		log.Println("💡 Try it:")
		log.Println("   curl -X POST http://localhost:8080/chat \\")
		log.Println("     -H \"Content-Type: application/json\" \\")
		log.Println("     -d '{\"message\": \"What is 2+2?\"}' \\")
		log.Println("     -N")
		log.Println()
		log.Println("   # High confidence (short message) - bypasses approval:")
		log.Println("   curl -X POST http://localhost:8080/chat \\")
		log.Println("     -H \"Content-Type: application/json\" \\")
		log.Println("     -d '{\"message\": \"Hi\"}' \\")
		log.Println("     -N")
		log.Println()
		log.Println("   # Low confidence (long/risky message) - requires approval:")
		log.Println("   curl -X POST http://localhost:8080/chat \\")
		log.Println("     -H \"Content-Type: application/json\" \\")
		log.Println("     -d '{\"message\": \"This is a risky operation that needs approval\"}' \\")
		log.Println("     -N")
		log.Println()
		log.Println("Press Ctrl+C to stop")
		log.Println()

		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("❌ Server failed: %v", err)
		}
	}()

	// Wait for interrupt signal
	stop := make(chan os.Signal, 1)
	signal.Notify(stop, os.Interrupt, syscall.SIGTERM)
	<-stop

	log.Println("\n🛑 Shutting down server...")

	// Graceful shutdown
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	if err := server.Shutdown(ctx); err != nil {
		log.Printf("❌ Server shutdown error: %v", err)
	}

	log.Println("✅ Server stopped gracefully")
}
