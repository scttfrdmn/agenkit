// Package http provides HTTP server implementation for the protocol adapter.
package http

import (
	"context"
	"crypto/tls"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"strings"
	"sync"

	"github.com/quic-go/quic-go/http3"
	"golang.org/x/net/http2"
	"golang.org/x/net/http2/h2c"

	"github.com/agenkit/agenkit-go/adapter/codec"
	"github.com/agenkit/agenkit-go/agenkit"
)

// ServerOptions configures HTTP server behavior.
type ServerOptions struct {
	// EnableHTTP2 enables HTTP/2 support (both h2 and h2c)
	EnableHTTP2 bool
	// EnableHTTP3 enables HTTP/3 over QUIC (requires TLS)
	EnableHTTP3 bool
	// TLSConfig for HTTPS, HTTP/2 over TLS, and HTTP/3
	TLSConfig *tls.Config
	// HTTP3Addr is the UDP address for HTTP/3 (defaults to HTTP addr)
	HTTP3Addr string
}

// HTTPAgent is an HTTP server wrapper for exposing agents over HTTP.
type HTTPAgent struct {
	agent   agenkit.Agent
	server  *http.Server
	http3Server *http3.Server
	mux     *http.ServeMux
	mu      sync.Mutex
	options ServerOptions
}

// NewHTTPAgent creates a new HTTP agent server with default options (HTTP/1.1 only).
//
// Args:
//   - agent: The local agent to expose
//   - addr: HTTP server address (e.g., "localhost:8080")
func NewHTTPAgent(agent agenkit.Agent, addr string) *HTTPAgent {
	return NewHTTPAgentWithOptions(agent, addr, ServerOptions{
		EnableHTTP2: false,
		EnableHTTP3: false,
	})
}

// NewHTTPAgentWithOptions creates a new HTTP agent server with custom options.
//
// Args:
//   - agent: The local agent to expose
//   - addr: HTTP server address (e.g., "localhost:8080")
//   - options: Server configuration options
func NewHTTPAgentWithOptions(agent agenkit.Agent, addr string, options ServerOptions) *HTTPAgent {
	mux := http.NewServeMux()
	h := &HTTPAgent{
		agent:   agent,
		mux:     mux,
		options: options,
	}

	// Register handlers
	mux.HandleFunc("/health", h.handleHealth)
	mux.HandleFunc("/process", h.handleProcess)
	mux.HandleFunc("/stream", h.handleStream)

	// Configure HTTP/1.1 and HTTP/2 server
	var handler http.Handler = mux
	if options.EnableHTTP2 {
		// Wrap handler with h2c for HTTP/2 cleartext support
		handler = h2c.NewHandler(mux, &http2.Server{})
	}

	h.server = &http.Server{
		Addr:      addr,
		Handler:   handler,
		TLSConfig: options.TLSConfig,
	}

	// Configure HTTP/2 over TLS if TLS is enabled
	if options.TLSConfig != nil {
		http2.ConfigureServer(h.server, &http2.Server{})
	}

	// Configure HTTP/3 server if enabled
	if options.EnableHTTP3 {
		http3Addr := options.HTTP3Addr
		if http3Addr == "" {
			http3Addr = addr
		}

		h.http3Server = &http3.Server{
			Addr:      http3Addr,
			Handler:   mux,
			TLSConfig: options.TLSConfig,
		}
	}

	return h
}

// Start starts the HTTP server (and HTTP/3 if enabled).
func (h *HTTPAgent) Start(ctx context.Context) error {
	h.mu.Lock()
	defer h.mu.Unlock()

	protocol := "http"
	if h.server.TLSConfig != nil {
		protocol = "https"
	}
	if h.options.EnableHTTP2 {
		protocol += " (HTTP/2)"
	}
	if h.options.EnableHTTP3 {
		protocol += " + HTTP/3"
	}

	log.Printf("Agent '%s' listening on %s://%s\n", h.agent.Name(), protocol, h.server.Addr)

	// Start HTTP/1.1 or HTTP/2 server in background
	go func() {
		var err error
		if h.server.TLSConfig != nil {
			// HTTPS with TLS
			err = h.server.ListenAndServeTLS("", "")
		} else {
			// HTTP (cleartext)
			err = h.server.ListenAndServe()
		}
		if err != nil && err != http.ErrServerClosed {
			log.Printf("HTTP server error: %v\n", err)
		}
	}()

	// Start HTTP/3 server in background if enabled
	if h.http3Server != nil {
		log.Printf("Agent '%s' HTTP/3 listening on %s (UDP)\n", h.agent.Name(), h.http3Server.Addr)
		go func() {
			ln, err := net.ListenPacket("udp", h.http3Server.Addr)
			if err != nil {
				log.Printf("HTTP/3 server listen error: %v\n", err)
				return
			}
			if err := h.http3Server.Serve(ln); err != nil && err != http.ErrServerClosed {
				log.Printf("HTTP/3 server error: %v\n", err)
			}
		}()
	}

	return nil
}

// Stop stops the HTTP server (and HTTP/3 if enabled).
func (h *HTTPAgent) Stop() error {
	h.mu.Lock()
	defer h.mu.Unlock()

	log.Printf("Agent '%s' stopped\n", h.agent.Name())

	ctx, cancel := context.WithTimeout(context.Background(), 5*1000*1000*1000) // 5 seconds
	defer cancel()

	// Shutdown HTTP/1.1 or HTTP/2 server
	if err := h.server.Shutdown(ctx); err != nil {
		return err
	}

	// Close HTTP/3 server if running
	if h.http3Server != nil {
		if err := h.http3Server.Close(); err != nil {
			return err
		}
	}

	return nil
}

// handleHealth handles health check requests.
func (h *HTTPAgent) handleHealth(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodHead && r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}
	w.WriteHeader(http.StatusOK)
}

// handleProcess handles process requests.
func (h *HTTPAgent) handleProcess(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Read request body
	body, err := io.ReadAll(r.Body)
	if err != nil {
		h.sendError(w, "unknown", "INVALID_REQUEST", "failed to read request body", nil)
		return
	}
	defer r.Body.Close()

	// Decode request envelope
	envelope, err := codec.DecodeBytes(body)
	if err != nil {
		h.sendError(w, "unknown", "INVALID_MESSAGE", "failed to decode request", nil)
		return
	}

	// Extract message
	messageData, ok := envelope.Payload["message"].(map[string]interface{})
	if !ok {
		h.sendError(w, envelope.ID, "INVALID_MESSAGE", "invalid message format", nil)
		return
	}

	msgData := codec.MessageData{
		Role:      messageData["role"].(string),
		Content:   messageData["content"].(string),
		Metadata:  messageData["metadata"].(map[string]interface{}),
		Timestamp: messageData["timestamp"].(string),
	}

	inputMessage, err := codec.DecodeMessage(msgData)
	if err != nil {
		h.sendError(w, envelope.ID, "INVALID_MESSAGE", err.Error(), nil)
		return
	}

	// Process message through agent
	result, err := h.agent.Process(r.Context(), inputMessage)
	if err != nil {
		h.sendError(w, envelope.ID, "EXECUTION_ERROR", err.Error(), nil)
		return
	}

	// Create response envelope
	responsePayload := map[string]interface{}{
		"message": codec.EncodeMessage(result),
	}
	response := codec.CreateResponseEnvelope(envelope.ID, responsePayload)

	// Send response
	responseBytes, err := codec.EncodeBytes(response)
	if err != nil {
		h.sendError(w, envelope.ID, "INTERNAL_ERROR", "failed to encode response", nil)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write(responseBytes)
}

// handleStream handles streaming requests.
func (h *HTTPAgent) handleStream(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Check if agent supports streaming
	streamingAgent, ok := h.agent.(agenkit.StreamingAgent)
	if !ok {
		h.sendError(w, "unknown", "NOT_IMPLEMENTED", "agent does not support streaming", nil)
		return
	}

	// Read request body
	body, err := io.ReadAll(r.Body)
	if err != nil {
		h.sendError(w, "unknown", "INVALID_REQUEST", "failed to read request body", nil)
		return
	}
	defer r.Body.Close()

	// Decode request envelope
	envelope, err := codec.DecodeBytes(body)
	if err != nil {
		h.sendError(w, "unknown", "INVALID_MESSAGE", "failed to decode request", nil)
		return
	}

	// Extract message
	messageData, ok := envelope.Payload["message"].(map[string]interface{})
	if !ok {
		h.sendError(w, envelope.ID, "INVALID_MESSAGE", "invalid message format", nil)
		return
	}

	msgData := codec.MessageData{
		Role:      messageData["role"].(string),
		Content:   messageData["content"].(string),
		Metadata:  messageData["metadata"].(map[string]interface{}),
		Timestamp: messageData["timestamp"].(string),
	}

	inputMessage, err := codec.DecodeMessage(msgData)
	if err != nil {
		h.sendError(w, envelope.ID, "INVALID_MESSAGE", err.Error(), nil)
		return
	}

	// Set headers for SSE
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")

	flusher, ok := w.(http.Flusher)
	if !ok {
		h.sendError(w, envelope.ID, "INTERNAL_ERROR", "streaming not supported", nil)
		return
	}

	// Start streaming
	messageChan, errorChan := streamingAgent.Stream(r.Context(), inputMessage)

	// Track channel closures
	messageChanClosed := false
	errorChanClosed := false

	for {
		select {
		case chunk, ok := <-messageChan:
			if !ok {
				messageChanClosed = true
				if errorChanClosed {
					// Both channels closed - stream complete
					endEnv := codec.CreateStreamEndEnvelope(envelope.ID)
					h.sendSSEEvent(w, envelope.ID, "stream_end", endEnv)
					flusher.Flush()
					return
				}
				messageChan = nil
				continue
			}

			// Send chunk as SSE
			chunkEnv := codec.CreateStreamChunkEnvelope(envelope.ID, codec.EncodeMessage(chunk))
			h.sendSSEEvent(w, envelope.ID, "stream_chunk", chunkEnv)
			flusher.Flush()

		case err, ok := <-errorChan:
			if ok && err != nil {
				h.sendSSEError(w, envelope.ID, "STREAM_ERROR", err.Error())
				flusher.Flush()
				return
			}
			if !ok {
				errorChanClosed = true
				if messageChanClosed {
					// Both channels closed - stream complete
					endEnv := codec.CreateStreamEndEnvelope(envelope.ID)
					h.sendSSEEvent(w, envelope.ID, "stream_end", endEnv)
					flusher.Flush()
					return
				}
				errorChan = nil
				continue
			}

		case <-r.Context().Done():
			h.sendSSEError(w, envelope.ID, "CANCELLED", "request cancelled")
			flusher.Flush()
			return
		}
	}
}

// sendSSEEvent sends a Server-Sent Event.
func (h *HTTPAgent) sendSSEEvent(w http.ResponseWriter, id, eventType string, data interface{}) {
	if data != nil {
		jsonData, _ := json.Marshal(data)
		fmt.Fprintf(w, "data: %s\n\n", jsonData)
	} else {
		fmt.Fprintf(w, "data: {\"type\":\"%s\",\"id\":\"%s\"}\n\n", eventType, id)
	}
}

// sendSSEError sends an error as Server-Sent Event.
func (h *HTTPAgent) sendSSEError(w http.ResponseWriter, id, errorCode, errorMessage string) {
	errorEnv := codec.CreateErrorEnvelope(id, errorCode, errorMessage, nil)
	jsonData, _ := json.Marshal(errorEnv)
	fmt.Fprintf(w, "data: %s\n\n", jsonData)
}

// sendError sends an error response.
func (h *HTTPAgent) sendError(w http.ResponseWriter, id, errorCode, errorMessage string, details map[string]interface{}) {
	envelope := codec.CreateErrorEnvelope(id, errorCode, errorMessage, details)
	responseBytes, _ := codec.EncodeBytes(envelope)

	w.Header().Set("Content-Type", "application/json")

	// Map error codes to HTTP status codes
	statusCode := http.StatusInternalServerError
	switch errorCode {
	case "INVALID_MESSAGE", "INVALID_REQUEST":
		statusCode = http.StatusBadRequest
	case "NOT_IMPLEMENTED":
		statusCode = http.StatusNotImplemented
	case "AGENT_NOT_FOUND":
		statusCode = http.StatusNotFound
	}

	w.WriteHeader(statusCode)
	w.Write(responseBytes)
}

// ParseHTTPEndpoint parses an HTTP endpoint string.
// Format: http://host:port or https://host:port
func ParseHTTPEndpoint(endpoint string) (string, error) {
	if !strings.HasPrefix(endpoint, "http://") && !strings.HasPrefix(endpoint, "https://") {
		return "", fmt.Errorf("invalid HTTP endpoint: %s", endpoint)
	}

	// Extract address (remove http:// or https://)
	var addr string
	if strings.HasPrefix(endpoint, "https://") {
		addr = endpoint[8:]
	} else {
		addr = endpoint[7:]
	}

	return addr, nil
}
