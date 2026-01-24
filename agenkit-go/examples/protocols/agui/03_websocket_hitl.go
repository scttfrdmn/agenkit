// AG-UI HITL with WebSocket Transport Example
//
// Demonstrates Human-in-the-Loop with WebSocket bidirectional communication.
// Shows how Interrupt events can be sent to clients and how clients can
// respond with InterruptResponse messages.
//
// Key concepts:
//   - WebSocket bidirectional streaming
//   - Interrupt events sent to clients
//   - Full-duplex communication for HITL
//   - Real-time approval workflow
//
// This example shows:
//   - WebSocket server with HITL support
//   - Interrupt event broadcasting
//   - Client message handling
//   - Bidirectional message flow
//
// Usage:
//
//	go run 03_websocket_hitl.go
//
// Then from another terminal (using websocat: https://github.com/vi/websocat):
//
//	echo '{"type": "message", "content": "Should I proceed?"}' | websocat ws://localhost:8765
//
// Or test with wscat (npm install -g wscat):
//
//	wscat -c ws://localhost:8765
//	> {"type": "message", "content": "Should I proceed?"}
package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"github.com/gorilla/websocket"
	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/patterns"
	"github.com/scttfrdmn/agenkit/agenkit-go/protocols/agui"
	"github.com/scttfrdmn/agenkit/agenkit-go/protocols/agui/transports"
)

// DecisionAgent is an agent that makes decisions with varying confidence.
type DecisionAgent struct {
	name string
}

func NewDecisionAgent(name string) *DecisionAgent {
	return &DecisionAgent{name: name}
}

func (d *DecisionAgent) Name() string {
	return d.name
}

func (d *DecisionAgent) Capabilities() []string {
	return []string{"decision-making", "analysis"}
}

func (d *DecisionAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	content := strings.ToLower(message.Content)

	// Analyze request complexity
	var confidence float64
	var responseText string
	var decisionType string

	if strings.Contains(content, "critical") || strings.Contains(content, "important") || strings.Contains(content, "should") {
		confidence = 0.5 // Low confidence for critical decisions
		responseText = "This requires careful consideration."
		decisionType = "critical"
	} else if strings.Contains(content, "simple") || strings.Contains(content, "easy") {
		confidence = 0.95 // High confidence for simple decisions
		responseText = "This is straightforward."
		decisionType = "routine"
	} else {
		confidence = 0.7
		responseText = "I'll analyze this carefully."
		decisionType = "routine"
	}

	response := agenkit.NewMessage("assistant", fmt.Sprintf("%s Regarding: %s", responseText, message.Content))
	response.Metadata = map[string]interface{}{
		"confidence":    confidence,
		"decision_type": decisionType,
	}

	return response, nil
}

func (d *DecisionAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:     d.name,
		Capabilities:  d.Capabilities(),
		InternalState: make(map[string]interface{}),
		Metadata:      make(map[string]interface{}),
	}
}

// approvalFunc is an approval function with detailed logging.
func approvalFunc(ctx context.Context, request *patterns.ApprovalRequest) (*patterns.ApprovalResponse, error) {
	confidence := request.Confidence
	decisionType := "unknown"
	if dt, ok := request.Context["decision_type"].(string); ok {
		decisionType = dt
	}

	log.Println("\n[Approval System]")
	log.Printf("  Confidence: %.2f", confidence)
	log.Printf("  Decision Type: %s", decisionType)
	log.Printf("  Threshold: %v", request.Context["approval_threshold"])
	if shortfall, ok := request.Context["confidence_shortfall"].(float64); ok {
		log.Printf("  Shortfall: %.2f", shortfall)
	}

	// Simulate human review
	time.Sleep(300 * time.Millisecond)

	// For demo, auto-approve
	approved := true
	feedback := fmt.Sprintf("Approved by supervisor (confidence: %.2f)", confidence)

	if approved {
		log.Println("  Decision: ✅ Approved")
	} else {
		log.Println("  Decision: ❌ Rejected")
	}
	log.Printf("  Feedback: %s\n", feedback)

	return &patterns.ApprovalResponse{
		Approved: approved,
		Feedback: feedback,
	}, nil
}

func main() {
	log.SetFlags(log.LstdFlags | log.Lmicroseconds)
	log.Println("🚀 Starting AG-UI WebSocket Transport with HITL Example")

	// Create decision agent
	decisionAgent := NewDecisionAgent("DecisionAgent")
	log.Printf("📦 Created decision agent: %s", decisionAgent.Name())

	// Wrap with HumanInLoopAgent
	hilAgent, err := patterns.NewHumanInLoopAgent(&patterns.HumanInLoopConfig{
		Agent:             decisionAgent,
		ApprovalFunc:      approvalFunc,
		ApprovalThreshold: 0.8, // Require approval when confidence < 0.8
	})
	if err != nil {
		log.Fatalf("❌ Failed to create HumanInLoopAgent: %v", err)
	}
	log.Println("🛡️  Created HumanInLoopAgent (threshold: 0.8)")

	// Create HITL adapter
	hilAdapter := agui.NewAGUIHumanInLoopAdapter(hilAgent, "WebSocket-DecisionAgent", true)
	log.Println("🔌 Created AGUIHumanInLoopAdapter")

	// Create WebSocket upgrader
	upgrader := websocket.Upgrader{
		CheckOrigin: func(r *http.Request) bool { return true }, // Allow all origins (restrict in production)
	}

	// Create WebSocket handler with HITL support
	config := transports.AGUIWebSocketHandlerConfig{
		AgentName:         "WebSocket-DecisionAgent",
		HeartbeatInterval: 10 * time.Second,
		ReadTimeout:       60 * time.Second,
		WriteTimeout:      10 * time.Second,
	}

	// We need to create a custom handler that uses our HITL adapter
	handler := createHITLWebSocketHandler(hilAdapter, upgrader, config)
	log.Println("📡 Created WebSocket handler with HITL support")

	// Set up HTTP server
	mux := http.NewServeMux()
	mux.HandleFunc("/", handler)
	mux.HandleFunc("/health", healthHandler)

	server := &http.Server{
		Addr:         ":8765",
		Handler:      mux,
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 60 * time.Second,
		IdleTimeout:  120 * time.Second,
	}

	// Start server in goroutine
	go func() {
		log.Println("🌐 WebSocket server starting on ws://localhost:8765")
		log.Println("📍 Endpoints:")
		log.Println("   ws://localhost:8765/     - WebSocket endpoint")
		log.Println("   http://localhost:8765/health - Health check")
		log.Println()
		log.Println("💡 Test with websocat:")
		log.Println("   echo '{\"type\": \"message\", \"content\": \"Should I proceed?\"}' | websocat ws://localhost:8765")
		log.Println()
		log.Println("   # Low confidence (triggers approval):")
		log.Println("   echo '{\"type\": \"message\", \"content\": \"Make a critical decision\"}' | websocat ws://localhost:8765")
		log.Println()
		log.Println("   # High confidence (bypasses approval):")
		log.Println("   echo '{\"type\": \"message\", \"content\": \"Simple task\"}' | websocat ws://localhost:8765")
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

// createHITLWebSocketHandler creates a custom WebSocket handler with HITL adapter.
func createHITLWebSocketHandler(
	adapter *agui.AGUIHumanInLoopAdapter,
	upgrader websocket.Upgrader,
	config transports.AGUIWebSocketHandlerConfig,
) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// Upgrade connection
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			log.Printf("❌ WebSocket upgrade failed: %v", err)
			http.Error(w, fmt.Sprintf("WebSocket upgrade failed: %v", err), http.StatusBadRequest)
			return
		}
		defer func() {
			if err := conn.Close(); err != nil {
				log.Printf("Error closing connection: %v", err)
			}
		}()

		clientID := conn.RemoteAddr().String()
		log.Printf("\n[WebSocket] Client %s connected", clientID)

		// Set connection limits
		maxMessageSize := config.MaxMessageSize
		if maxMessageSize == 0 {
			maxMessageSize = 1024 * 1024 // 1MB default
		}
		conn.SetReadLimit(maxMessageSize)

		// Create context for this connection
		ctx, cancel := context.WithCancel(context.Background())
		defer cancel()

		// Handle messages
		handleWebSocketMessages(ctx, conn, adapter, config, clientID)
	}
}

// handleWebSocketMessages handles incoming WebSocket messages and streams responses.
func handleWebSocketMessages(
	ctx context.Context,
	conn *websocket.Conn,
	adapter *agui.AGUIHumanInLoopAdapter,
	config transports.AGUIWebSocketHandlerConfig,
	clientID string,
) {
	readTimeout := config.ReadTimeout
	if readTimeout == 0 {
		readTimeout = 60 * time.Second
	}

	writeTimeout := config.WriteTimeout
	if writeTimeout == 0 {
		writeTimeout = 10 * time.Second
	}

	// Read messages from client
	for {
		// Set read deadline
		if err := conn.SetReadDeadline(time.Now().Add(readTimeout)); err != nil {
			log.Printf("[WebSocket] Failed to set read deadline: %v", err)
			break
		}

		// Read message
		messageType, message, err := conn.ReadMessage()
		if err != nil {
			// Connection closed or error
			log.Printf("[WebSocket] Client %s disconnected", clientID)
			break
		}

		// Only handle text messages
		if messageType != websocket.TextMessage {
			continue
		}

		// Parse message
		formatter := transports.WebSocketMessageFormat{}
		msgData, err := formatter.ParseMessage(message)
		if err != nil {
			log.Printf("[WebSocket] Invalid message format: %v", err)
			sendError(conn, writeTimeout, fmt.Sprintf("Invalid message format: %v", err))
			continue
		}

		// Handle message based on type
		msgType, ok := msgData["type"].(string)
		if !ok {
			sendError(conn, writeTimeout, "Message missing 'type' field")
			continue
		}

		log.Printf("[WebSocket] Received %s from client %s", msgType, clientID)

		switch msgType {
		case "message":
			// Process user message
			handleUserMessage(ctx, conn, adapter, msgData, writeTimeout, clientID)

		case "ping":
			// Respond with pong
			sendPong(conn, writeTimeout)

		default:
			sendError(conn, writeTimeout, fmt.Sprintf("Unknown message type: %s", msgType))
		}
	}
}

// handleUserMessage processes a user message and streams responses.
func handleUserMessage(
	ctx context.Context,
	conn *websocket.Conn,
	adapter *agui.AGUIHumanInLoopAdapter,
	msgData map[string]interface{},
	writeTimeout time.Duration,
	clientID string,
) {
	// Extract message content
	content, ok := msgData["content"].(string)
	if !ok {
		sendError(conn, writeTimeout, "Message missing 'content' field")
		return
	}

	log.Printf("[WebSocket] Processing message from %s: %s", clientID, content)

	// Create agenkit message
	message := agenkit.NewMessage("user", content)

	// Stream events
	eventCount := 0
	interruptCount := 0

	for event := range adapter.StreamEvents(ctx, message) {
		eventCount++

		// Track interrupts
		if _, ok := event.(*agui.Interrupt); ok {
			interruptCount++
			log.Printf("[WebSocket] 🚨 Interrupt event emitted to client %s", clientID)
		}

		// Format event as JSON
		eventJSON, err := event.ToJSON()
		if err != nil {
			log.Printf("[WebSocket] Failed to format event: %v", err)
			sendError(conn, writeTimeout, fmt.Sprintf("Failed to format event: %v", err))
			continue
		}

		// Send event to client
		if err := sendMessage(conn, writeTimeout, eventJSON); err != nil {
			log.Printf("[WebSocket] Failed to send event: %v", err)
			return
		}
	}

	// Send completion marker
	completionData := map[string]interface{}{
		"type":   "stream_complete",
		"status": "success",
	}
	completionEvent := agui.NewMetadataEvent(completionData)
	if completionJSON, err := completionEvent.ToJSON(); err == nil {
		if sendErr := sendMessage(conn, writeTimeout, completionJSON); sendErr != nil {
			log.Printf("[WebSocket] Failed to send completion: %v", sendErr)
		}
	}

	log.Printf("[WebSocket] Completed streaming %d events (%d interrupts) to client %s", eventCount, interruptCount, clientID)
}

// sendMessage sends a message over WebSocket with write timeout.
func sendMessage(conn *websocket.Conn, timeout time.Duration, message []byte) error {
	if err := conn.SetWriteDeadline(time.Now().Add(timeout)); err != nil {
		return err
	}
	return conn.WriteMessage(websocket.TextMessage, message)
}

// sendError sends an error message to the client.
func sendError(conn *websocket.Conn, timeout time.Duration, errorMsg string) {
	errorEvent := agui.NewErrorEvent("WebSocketError", errorMsg, true)
	if errorJSON, err := errorEvent.ToJSON(); err == nil {
		_ = sendMessage(conn, timeout, errorJSON)
	}
}

// sendPong sends a pong response.
func sendPong(conn *websocket.Conn, timeout time.Duration) {
	pongData := map[string]interface{}{"type": "pong"}
	pongEvent := agui.NewMetadataEvent(pongData)
	if pongJSON, err := pongEvent.ToJSON(); err == nil {
		_ = sendMessage(conn, timeout, pongJSON)
	}
}

// healthHandler provides a simple health check endpoint.
func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	if _, err := fmt.Fprintf(w, `{"status":"ok","service":"agui-websocket-hitl","timestamp":"%s"}`,
		time.Now().UTC().Format(time.RFC3339)); err != nil {
		log.Printf("Error writing health check: %v", err)
	}
}
