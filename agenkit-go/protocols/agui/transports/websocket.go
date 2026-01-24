package transports

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"sync"
	"time"

	"github.com/gorilla/websocket"
	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/protocols/agui"
)

// WebSocketMessageFormat handles formatting AG-UI events for WebSocket transmission.
type WebSocketMessageFormat struct{}

// FormatEvent formats an AG-UI event as WebSocket message (JSON string).
func (f *WebSocketMessageFormat) FormatEvent(event agui.AGUIEvent) ([]byte, error) {
	return event.ToJSON()
}

// ParseMessage parses WebSocket message (JSON) to map.
func (f *WebSocketMessageFormat) ParseMessage(message []byte) (map[string]interface{}, error) {
	var result map[string]interface{}
	if err := json.Unmarshal(message, &result); err != nil {
		return nil, fmt.Errorf("invalid JSON in WebSocket message: %w", err)
	}
	return result, nil
}

// AGUIWebSocketHandlerConfig holds configuration for WebSocket handler
type AGUIWebSocketHandlerConfig struct {
	// Optional agent name override
	AgentName string

	// Send heartbeat events
	HeartbeatInterval time.Duration

	// Timeout for read operations
	ReadTimeout time.Duration

	// Timeout for write operations
	WriteTimeout time.Duration

	// Maximum message size (bytes)
	MaxMessageSize int64
}

// AGUIWebSocketHandler handles WebSocket connections for AG-UI protocol.
//
// Provides bidirectional communication with automatic event streaming
// and message processing.
//
// Usage:
//
//	upgrader := websocket.Upgrader{
//	    CheckOrigin: func(r *http.Request) bool { return true },
//	}
//	handler := NewAGUIWebSocketHandler(agent, upgrader, AGUIWebSocketHandlerConfig{})
//	http.Handle("/chat", handler)
//
// Client message format (JSON):
//
//	{
//	    "type": "message",
//	    "content": "User message text"
//	}
//
// Server sends AG-UI events as JSON:
//
//	{
//	    "event_type": "text_message_chunk",
//	    "message_id": "msg-123",
//	    "content": "Hello",
//	    ...
//	}
type AGUIWebSocketHandler struct {
	adapter           *agui.AGUIAdapter
	upgrader          websocket.Upgrader
	heartbeatInterval time.Duration
	readTimeout       time.Duration
	writeTimeout      time.Duration
	maxMessageSize    int64
	formatter         WebSocketMessageFormat
}

// NewAGUIWebSocketHandler creates a new WebSocket handler.
func NewAGUIWebSocketHandler(
	agent agenkit.Agent,
	upgrader websocket.Upgrader,
	config AGUIWebSocketHandlerConfig,
) *AGUIWebSocketHandler {
	adapterConfig := agui.AGUIAdapterConfig{
		AgentName: config.AgentName,
	}
	adapter := agui.NewAGUIAdapterWithConfig(agent, adapterConfig)

	// Set defaults
	heartbeatInterval := config.HeartbeatInterval
	if heartbeatInterval == 0 {
		heartbeatInterval = 30 * time.Second
	}

	readTimeout := config.ReadTimeout
	if readTimeout == 0 {
		readTimeout = 60 * time.Second
	}

	writeTimeout := config.WriteTimeout
	if writeTimeout == 0 {
		writeTimeout = 10 * time.Second
	}

	maxMessageSize := config.MaxMessageSize
	if maxMessageSize == 0 {
		maxMessageSize = 1024 * 1024 // 1MB
	}

	return &AGUIWebSocketHandler{
		adapter:           adapter,
		upgrader:          upgrader,
		heartbeatInterval: heartbeatInterval,
		readTimeout:       readTimeout,
		writeTimeout:      writeTimeout,
		maxMessageSize:    maxMessageSize,
		formatter:         WebSocketMessageFormat{},
	}
}

// ServeHTTP handles HTTP upgrade to WebSocket.
func (h *AGUIWebSocketHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	// Upgrade connection
	conn, err := h.upgrader.Upgrade(w, r, nil)
	if err != nil {
		http.Error(w, fmt.Sprintf("WebSocket upgrade failed: %v", err), http.StatusBadRequest)
		return
	}
	defer func() { _ = conn.Close() }()

	// Handle WebSocket connection
	h.handleConnection(conn)
}

// handleConnection manages a WebSocket connection lifecycle
func (h *AGUIWebSocketHandler) handleConnection(conn *websocket.Conn) {
	// Set connection limits
	conn.SetReadLimit(h.maxMessageSize)

	// Create context for this connection
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// Start heartbeat goroutine
	var wg sync.WaitGroup
	wg.Add(1)
	go func() {
		defer wg.Done()
		h.sendHeartbeats(ctx, conn)
	}()

	// Read messages from client
	for {
		// Set read deadline
		if err := conn.SetReadDeadline(time.Now().Add(h.readTimeout)); err != nil {
			break
		}

		// Read message
		messageType, message, err := conn.ReadMessage()
		if err != nil {
			// Connection closed or error
			break
		}

		// Only handle text messages
		if messageType != websocket.TextMessage {
			continue
		}

		// Parse message
		msgData, err := h.formatter.ParseMessage(message)
		if err != nil {
			// Send error response
			_ = h.sendError(conn, fmt.Sprintf("Invalid message format: %v", err))
			continue
		}

		// Handle message based on type
		msgType, ok := msgData["type"].(string)
		if !ok {
			_ = h.sendError(conn, "Message missing 'type' field")
			continue
		}

		switch msgType {
		case "message":
			// Process user message
			h.handleUserMessage(ctx, conn, msgData)

		case "ping":
			// Respond with pong
			_ = h.sendPong(conn)

		default:
			_ = h.sendError(conn, fmt.Sprintf("Unknown message type: %s", msgType))
		}
	}

	// Cancel context to stop heartbeats
	cancel()
	wg.Wait()
}

// handleUserMessage processes a user message and streams responses
func (h *AGUIWebSocketHandler) handleUserMessage(
	ctx context.Context,
	conn *websocket.Conn,
	msgData map[string]interface{},
) {
	// Extract message content
	content, ok := msgData["content"].(string)
	if !ok {
		_ = h.sendError(conn, "Message missing 'content' field")
		return
	}

	// Create agenkit message
	message := agenkit.NewMessage("user", content)

	// Stream events
	for event := range h.adapter.StreamEvents(ctx, message) {
		// Format event
		eventJSON, err := h.formatter.FormatEvent(event)
		if err != nil {
			_ = h.sendError(conn, fmt.Sprintf("Failed to format event: %v", err))
			continue
		}

		// Send event
		if err := h.sendMessage(conn, eventJSON); err != nil {
			// Connection closed or write error
			return
		}
	}

	// Send completion marker
	completion := map[string]string{
		"type":   "stream_complete",
		"status": "success",
	}
	completionJSON, _ := json.Marshal(completion)
	_ = h.sendMessage(conn, completionJSON)
}

// sendHeartbeats sends periodic heartbeat events
func (h *AGUIWebSocketHandler) sendHeartbeats(ctx context.Context, conn *websocket.Conn) {
	ticker := time.NewTicker(h.heartbeatInterval)
	defer ticker.Stop()

	sequence := int64(0)
	for {
		select {
		case <-ticker.C:
			sequence++
			heartbeat := agui.NewHeartbeatEvent(sequence)
			heartbeatJSON, err := h.formatter.FormatEvent(heartbeat)
			if err != nil {
				return
			}
			if err := h.sendMessage(conn, heartbeatJSON); err != nil {
				return
			}

		case <-ctx.Done():
			return
		}
	}
}

// sendMessage sends a message over WebSocket with write timeout
func (h *AGUIWebSocketHandler) sendMessage(conn *websocket.Conn, message []byte) error {
	if err := conn.SetWriteDeadline(time.Now().Add(h.writeTimeout)); err != nil {
		return err
	}
	return conn.WriteMessage(websocket.TextMessage, message)
}

// sendError sends an error message to the client
func (h *AGUIWebSocketHandler) sendError(conn *websocket.Conn, errorMsg string) error {
	errorEvent := agui.NewErrorEvent("WebSocketError", errorMsg, true)
	errorJSON, err := h.formatter.FormatEvent(errorEvent)
	if err != nil {
		return err
	}
	return h.sendMessage(conn, errorJSON)
}

// sendPong sends a pong response
func (h *AGUIWebSocketHandler) sendPong(conn *websocket.Conn) error {
	pong := map[string]string{"type": "pong"}
	pongJSON, _ := json.Marshal(pong)
	return h.sendMessage(conn, pongJSON)
}

// CreateWebSocketHandler creates a WebSocket handler with default config.
//
// Example:
//
//	upgrader := websocket.Upgrader{
//	    CheckOrigin: func(r *http.Request) bool { return true },
//	}
//	handler := CreateWebSocketHandler(agent, upgrader)
//	http.Handle("/chat", handler)
func CreateWebSocketHandler(agent agenkit.Agent, upgrader websocket.Upgrader) http.Handler {
	return NewAGUIWebSocketHandler(agent, upgrader, AGUIWebSocketHandlerConfig{})
}

// CreateWebSocketHandlerFunc creates an http.HandlerFunc for WebSocket streaming.
//
// Example:
//
//	upgrader := websocket.Upgrader{CheckOrigin: func(r *http.Request) bool { return true }}
//	http.HandleFunc("/chat", CreateWebSocketHandlerFunc(agent, upgrader))
func CreateWebSocketHandlerFunc(agent agenkit.Agent, upgrader websocket.Upgrader) http.HandlerFunc {
	handler := CreateWebSocketHandler(agent, upgrader)
	return handler.ServeHTTP
}

// StreamWebSocketEvents streams AG-UI events over an existing WebSocket connection.
//
// This is a lower-level function for custom integrations.
//
// Example:
//
//	adapter := agui.NewAGUIAdapter(agent)
//	message := agenkit.NewMessage("user", "Hello")
//	StreamWebSocketEvents(ctx, conn, adapter, message)
func StreamWebSocketEvents(
	ctx context.Context,
	conn *websocket.Conn,
	adapter *agui.AGUIAdapter,
	message *agenkit.Message,
) error {
	formatter := WebSocketMessageFormat{}
	writeTimeout := 10 * time.Second

	for event := range adapter.StreamEvents(ctx, message) {
		eventJSON, err := formatter.FormatEvent(event)
		if err != nil {
			return fmt.Errorf("failed to format event: %w", err)
		}

		if err := conn.SetWriteDeadline(time.Now().Add(writeTimeout)); err != nil {
			return fmt.Errorf("failed to set write deadline: %w", err)
		}

		if err := conn.WriteMessage(websocket.TextMessage, eventJSON); err != nil {
			return fmt.Errorf("failed to write message: %w", err)
		}
	}

	return nil
}
