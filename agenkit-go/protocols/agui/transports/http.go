// Package transports provides transport implementations for AG-UI protocol.
//
// HTTP/SSE Transport implements Server-Sent Events (SSE) for streaming AG-UI
// events over HTTP. Compatible with any HTTP framework (net/http, gin, echo, etc.).
package transports

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/protocols/agui"
)

// AGUIEventStreamer is an interface for streaming AG-UI events.
// Both AGUIAdapter and AGUIHumanInLoopAdapter implement this interface.
type AGUIEventStreamer interface {
	StreamEventsWithConfig(ctx context.Context, message *agenkit.Message, config agui.StreamEventsConfig) <-chan agui.AGUIEvent
	AgentName() string
}

// SSEFormatter formats AG-UI events as Server-Sent Events (SSE).
//
// SSE format:
//
//	data: {"event_type": "text_message_chunk", ...}\n\n
//
// With event name:
//
//	event: text_message_chunk
//	data: {...}\n\n
type SSEFormatter struct{}

// FormatEvent formats an AG-UI event as SSE message.
//
// Example:
//
//	event := agui.NewTextMessageChunk("msg-1", "Hello")
//	sse := SSEFormatter{}.FormatEvent(event, false)
//	// Returns: "data: {\"event_type\":\"text_message_chunk\",...}\n\n"
func (f *SSEFormatter) FormatEvent(event agui.AGUIEvent, includeEventName bool) (string, error) {
	eventJSON, err := event.ToJSON()
	if err != nil {
		return "", fmt.Errorf("failed to serialize event: %w", err)
	}

	if includeEventName {
		eventName := event.GetEventType()
		return fmt.Sprintf("event: %s\ndata: %s\n\n", eventName, string(eventJSON)), nil
	}

	return fmt.Sprintf("data: %s\n\n", string(eventJSON)), nil
}

// FormatComment formats an SSE comment (keeps connection alive).
func (f *SSEFormatter) FormatComment(comment string) string {
	return fmt.Sprintf(": %s\n\n", comment)
}

// FormatRetry formats an SSE retry directive.
func (f *SSEFormatter) FormatRetry(milliseconds int) string {
	return fmt.Sprintf("retry: %d\n\n", milliseconds)
}

// AGUISSEHandlerConfig holds configuration for SSE handler
type AGUISSEHandlerConfig struct {
	// Optional agent name override
	AgentName string

	// Optional pre-created adapter (for HITL support)
	// If provided, Agent parameter to NewAGUISSEHandler is ignored
	// Can be *agui.AGUIAdapter or *agui.AGUIHumanInLoopAdapter
	Adapter AGUIEventStreamer

	// Include "event:" lines in SSE output
	IncludeEventNames bool

	// CORS allowed origins (nil = no CORS)
	CORSOrigins []string

	// Timeout for streaming (0 = no timeout)
	Timeout time.Duration

	// Send ping comments to keep connection alive
	PingInterval time.Duration
}

// AGUISSEHandler is an http.Handler that streams AG-UI events via SSE.
//
// Usage:
//
//	handler := NewAGUISSEHandler(agent, AGUISSEHandlerConfig{})
//	http.Handle("/chat", handler)
//
// Request body (JSON):
//
//	{
//	    "message": "User message text",
//	    "message_id": "optional-msg-id"
//	}
//
// Response:
//
//	Content-Type: text/event-stream
//	Cache-Control: no-cache
//	Connection: keep-alive
//
//	data: {"event_type":"metadata",...}
//
//	data: {"event_type":"text_message_start",...}
//
//	...
type AGUISSEHandler struct {
	adapter           AGUIEventStreamer
	includeEventNames bool
	corsOrigins       []string
	timeout           time.Duration
	pingInterval      time.Duration
	formatter         SSEFormatter
}

// NewAGUISSEHandler creates a new SSE handler for an agent.
//
// If config.Adapter is provided, it will be used instead of creating a new one.
// This allows using AGUIHumanInLoopAdapter for HITL support.
func NewAGUISSEHandler(agent agenkit.Agent, config AGUISSEHandlerConfig) *AGUISSEHandler {
	var adapter AGUIEventStreamer

	if config.Adapter != nil {
		// Use provided adapter (e.g., AGUIHumanInLoopAdapter)
		adapter = config.Adapter
	} else {
		// Create standard adapter
		adapterConfig := agui.AGUIAdapterConfig{
			AgentName: config.AgentName,
		}
		adapter = agui.NewAGUIAdapterWithConfig(agent, adapterConfig)
	}

	return &AGUISSEHandler{
		adapter:           adapter,
		includeEventNames: config.IncludeEventNames,
		corsOrigins:       config.CORSOrigins,
		timeout:           config.Timeout,
		pingInterval:      config.PingInterval,
		formatter:         SSEFormatter{},
	}
}

// ServeHTTP handles HTTP requests and streams SSE events.
func (h *AGUISSEHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	// Only accept POST requests
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Set CORS headers if configured
	if len(h.corsOrigins) > 0 {
		origin := r.Header.Get("Origin")
		for _, allowed := range h.corsOrigins {
			if origin == allowed || allowed == "*" {
				w.Header().Set("Access-Control-Allow-Origin", origin)
				w.Header().Set("Access-Control-Allow-Methods", "POST, OPTIONS")
				w.Header().Set("Access-Control-Allow-Headers", "Content-Type")
				break
			}
		}
	}

	// Handle OPTIONS preflight
	if r.Method == http.MethodOptions {
		w.WriteHeader(http.StatusOK)
		return
	}

	// Parse request body
	var reqBody struct {
		Message   string `json:"message"`
		MessageID string `json:"message_id,omitempty"`
	}

	if err := json.NewDecoder(r.Body).Decode(&reqBody); err != nil {
		http.Error(w, fmt.Sprintf("Invalid JSON: %v", err), http.StatusBadRequest)
		return
	}

	// Create message
	message := agenkit.NewMessage("user", reqBody.Message)

	// Set SSE headers
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")
	w.Header().Set("X-Accel-Buffering", "no") // Disable nginx buffering

	// Get flusher
	flusher, ok := w.(http.Flusher)
	if !ok {
		http.Error(w, "Streaming not supported", http.StatusInternalServerError)
		return
	}

	// Create context with timeout if configured
	ctx := r.Context()
	if h.timeout > 0 {
		var cancel context.CancelFunc
		ctx, cancel = context.WithTimeout(ctx, h.timeout)
		defer cancel()
	}

	// Start ping goroutine if configured
	var pingDone chan struct{}
	if h.pingInterval > 0 {
		pingDone = make(chan struct{})
		go h.sendPings(w, flusher, pingDone)
		defer close(pingDone)
	}

	// Stream events
	config := agui.StreamEventsConfig{
		MessageID:    reqBody.MessageID,
		EmitMetadata: true,
	}

	for event := range h.adapter.StreamEventsWithConfig(ctx, message, config) {
		// Format event as SSE
		sseData, err := h.formatter.FormatEvent(event, h.includeEventNames)
		if err != nil {
			// Log error and continue
			comment := h.formatter.FormatComment(fmt.Sprintf("error: %v", err))
			if _, writeErr := io.WriteString(w, comment); writeErr != nil {
				return
			}
			flusher.Flush()
			continue
		}

		// Write event
		if _, err := io.WriteString(w, sseData); err != nil {
			return
		}
		flusher.Flush()

		// Check for context cancellation
		select {
		case <-ctx.Done():
			comment := h.formatter.FormatComment("stream_cancelled")
			_, _ = io.WriteString(w, comment)
			flusher.Flush()
			return
		default:
		}
	}

	// Send completion comment
	comment := h.formatter.FormatComment("stream_complete")
	_, _ = io.WriteString(w, comment)
	flusher.Flush()
}

// sendPings sends periodic ping comments to keep connection alive
func (h *AGUISSEHandler) sendPings(w io.Writer, flusher http.Flusher, done chan struct{}) {
	ticker := time.NewTicker(h.pingInterval)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			ping := h.formatter.FormatComment("ping")
			if _, err := io.WriteString(w, ping); err != nil {
				return
			}
			flusher.Flush()
		case <-done:
			return
		}
	}
}

// StreamSSEEvents streams AG-UI events directly to a writer.
//
// This is a lower-level function for custom integrations.
//
// Example:
//
//	adapter := agui.NewAGUIAdapter(agent)
//	message := agenkit.NewMessage("user", "Hello")
//	StreamSSEEvents(ctx, w, adapter, message, false)
func StreamSSEEvents(
	ctx context.Context,
	w io.Writer,
	adapter *agui.AGUIAdapter,
	message *agenkit.Message,
	includeEventNames bool,
) error {
	formatter := SSEFormatter{}

	for event := range adapter.StreamEvents(ctx, message) {
		sseData, err := formatter.FormatEvent(event, includeEventNames)
		if err != nil {
			return fmt.Errorf("failed to format event: %w", err)
		}

		if _, err := io.WriteString(w, sseData); err != nil {
			return fmt.Errorf("failed to write SSE data: %w", err)
		}

		// Flush if writer supports it
		if flusher, ok := w.(http.Flusher); ok {
			flusher.Flush()
		}
	}

	// Send completion comment
	comment := formatter.FormatComment("stream_complete")
	if _, err := io.WriteString(w, comment); err != nil {
		return fmt.Errorf("failed to write completion: %w", err)
	}

	if flusher, ok := w.(http.Flusher); ok {
		flusher.Flush()
	}

	return nil
}

// CreateSSEHandler is a convenience function to create an SSE handler with default config.
//
// Example:
//
//	handler := CreateSSEHandler(agent)
//	http.Handle("/chat", handler)
func CreateSSEHandler(agent agenkit.Agent) http.Handler {
	return NewAGUISSEHandler(agent, AGUISSEHandlerConfig{})
}

// CreateSSEHandlerFunc creates an http.HandlerFunc for SSE streaming.
//
// This is useful for quick integration with standard net/http.
//
// Example:
//
//	http.HandleFunc("/chat", CreateSSEHandlerFunc(agent))
func CreateSSEHandlerFunc(agent agenkit.Agent) http.HandlerFunc {
	handler := CreateSSEHandler(agent)
	return handler.ServeHTTP
}
