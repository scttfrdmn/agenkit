// Package local provides the server-side wrapper for exposing local agents.
package local

import (
	"context"
	"encoding/binary"
	"fmt"
	"io"
	"log"
	"net"
	"os"
	"sync"

	"github.com/agenkit/agenkit-go/adapter/codec"
	"github.com/agenkit/agenkit-go/adapter/errors"
	"github.com/agenkit/agenkit-go/adapter/transport"
	"github.com/agenkit/agenkit-go/agenkit"
)

// LocalAgent is a server-side wrapper for exposing a local agent over the protocol adapter.
type LocalAgent struct {
	agent       agenkit.Agent
	endpoint    string
	listener    net.Listener
	running     bool
	mu          sync.Mutex
	wg          sync.WaitGroup
	connections map[net.Conn]bool
	connMu      sync.Mutex
}

// NewLocalAgent creates a new local agent server.
//
// Args:
//   - agent: The local agent to expose
//   - endpoint: Endpoint URL (e.g., "unix:///tmp/agent.sock" or "tcp://host:port")
func NewLocalAgent(agent agenkit.Agent, endpoint string) (*LocalAgent, error) {
	if endpoint == "" {
		return nil, fmt.Errorf("endpoint must be provided")
	}

	return &LocalAgent{
		agent:       agent,
		endpoint:    endpoint,
		running:     false,
		connections: make(map[net.Conn]bool),
	}, nil
}

// Start starts the agent server.
func (l *LocalAgent) Start(ctx context.Context) error {
	l.mu.Lock()
	defer l.mu.Unlock()

	if l.running {
		return fmt.Errorf("server is already running")
	}

	// Create listener based on endpoint type
	var listener net.Listener
	var err error

	if len(l.endpoint) >= 7 && l.endpoint[:7] == "unix://" {
		socketPath := l.endpoint[7:]
		listener, err = transport.CreateUnixSocketServer(socketPath)
		if err != nil {
			return err
		}
		log.Printf("Agent '%s' listening on %s\n", l.agent.Name(), socketPath)

	} else if len(l.endpoint) >= 6 && l.endpoint[:6] == "tcp://" {
		tcpPart := l.endpoint[6:]
		// Find last colon to split host:port
		lastColon := -1
		for i := len(tcpPart) - 1; i >= 0; i-- {
			if tcpPart[i] == ':' {
				lastColon = i
				break
			}
		}
		if lastColon == -1 {
			return fmt.Errorf("invalid TCP endpoint format: %s", l.endpoint)
		}
		host := tcpPart[:lastColon]
		portStr := tcpPart[lastColon+1:]
		port := 0
		if _, err := fmt.Sscanf(portStr, "%d", &port); err != nil {
			return fmt.Errorf("invalid port in TCP endpoint: %s", l.endpoint)
		}
		listener, err = transport.CreateTCPServer(host, port)
		if err != nil {
			return err
		}
		log.Printf("Agent '%s' listening on %s:%d\n", l.agent.Name(), host, port)

	} else {
		return fmt.Errorf("unsupported endpoint format: %s", l.endpoint)
	}

	l.listener = listener
	l.running = true

	// Start accepting connections
	l.wg.Add(1)
	go l.acceptConnections(ctx)

	return nil
}

// Stop stops the agent server.
func (l *LocalAgent) Stop() error {
	l.mu.Lock()
	defer l.mu.Unlock()

	if !l.running {
		return nil
	}

	l.running = false

	// Close listener
	if l.listener != nil {
		l.listener.Close()
		l.listener = nil
	}

	// Close all active connections
	l.connMu.Lock()
	for conn := range l.connections {
		conn.Close()
	}
	l.connMu.Unlock()

	// Clean up Unix socket file
	if len(l.endpoint) >= 7 && l.endpoint[:7] == "unix://" {
		socketPath := l.endpoint[7:]
		if err := os.Remove(socketPath); err != nil && !os.IsNotExist(err) {
			log.Printf("Failed to remove socket file: %v\n", err)
		}
	}

	// Wait for all client handlers to finish
	l.wg.Wait()

	log.Printf("Agent '%s' stopped\n", l.agent.Name())
	return nil
}

// acceptConnections accepts incoming client connections.
func (l *LocalAgent) acceptConnections(ctx context.Context) {
	defer l.wg.Done()

	for l.running {
		conn, err := l.listener.Accept()
		if err != nil {
			if l.running {
				log.Printf("Accept error: %v\n", err)
			}
			continue
		}

		l.wg.Add(1)
		go l.handleClient(ctx, conn)
	}
}

// handleClient handles a client connection.
func (l *LocalAgent) handleClient(ctx context.Context, conn net.Conn) {
	defer l.wg.Done()
	defer conn.Close()

	// Register connection
	l.connMu.Lock()
	l.connections[conn] = true
	l.connMu.Unlock()

	// Unregister connection when done
	defer func() {
		l.connMu.Lock()
		delete(l.connections, conn)
		l.connMu.Unlock()
	}()

	log.Printf("Client connected: %v\n", conn.RemoteAddr())

	for l.running {
		// Read length prefix (4 bytes, big-endian)
		var length uint32
		if err := binary.Read(conn, binary.BigEndian, &length); err != nil {
			// Don't log expected disconnection errors
			if err != io.EOF && !l.isExpectedDisconnect(err) {
				log.Printf("Error reading length prefix: %v\n", err)
			}
			break
		}

		// Read payload
		payload := make([]byte, length)
		if _, err := io.ReadFull(conn, payload); err != nil {
			log.Printf("Error reading payload: %v\n", err)
			break
		}

		// Decode request
		request, err := codec.DecodeBytes(payload)
		if err != nil {
			log.Printf("Error decoding request: %v\n", err)
			l.sendError(conn, "unknown", "INVALID_MESSAGE", err.Error(), nil)
			break
		}

		// Check method
		method, ok := request.Payload["method"].(string)
		if !ok {
			log.Printf("Missing method in request\n")
			l.sendError(conn, request.ID, "INVALID_MESSAGE", "missing method", nil)
			break
		}

		// Handle method
		if method == "stream" {
			l.handleStreamRequest(ctx, conn, request)
		} else {
			responseBytes, err := l.processRequest(ctx, payload)
			if err != nil {
				log.Printf("Error processing request: %v\n", err)
				l.sendError(conn, request.ID, "INTERNAL_ERROR", err.Error(), nil)
				break
			}

			// Send response
			if err := l.sendFramed(conn, responseBytes); err != nil {
				log.Printf("Error sending response: %v\n", err)
				break
			}
		}
	}

	log.Printf("Client disconnected\n")
}

// processRequest processes a single request.
func (l *LocalAgent) processRequest(ctx context.Context, requestBytes []byte) ([]byte, error) {
	// Decode request
	request, err := codec.DecodeBytes(requestBytes)
	if err != nil {
		return nil, err
	}

	if request.Type != codec.TypeRequest {
		return nil, errors.NewInvalidMessageError(
			fmt.Sprintf("expected 'request' but got '%s'", request.Type),
			map[string]interface{}{"request": request},
		)
	}

	method, ok := request.Payload["method"].(string)
	if !ok {
		return nil, errors.NewInvalidMessageError("missing method", nil)
	}

	// Handle different methods
	if method == "process" {
		// Decode input message
		messageData, ok := request.Payload["message"].(map[string]interface{})
		if !ok {
			return nil, errors.NewInvalidMessageError("invalid message format", nil)
		}

		msgData := codec.MessageData{
			Role:      messageData["role"].(string),
			Content:   messageData["content"].(string),
			Metadata:  messageData["metadata"].(map[string]interface{}),
			Timestamp: messageData["timestamp"].(string),
		}

		inputMessage, err := codec.DecodeMessage(msgData)
		if err != nil {
			return nil, err
		}

		// Process through agent
		outputMessage, err := l.agent.Process(ctx, inputMessage)
		if err != nil {
			errorEnv := codec.CreateErrorEnvelope(request.ID, "AGENT_ERROR", err.Error(), nil)
			return codec.EncodeBytes(errorEnv)
		}

		// Create response
		payload := map[string]interface{}{
			"message": codec.EncodeMessage(outputMessage),
		}
		response := codec.CreateResponseEnvelope(request.ID, payload)
		return codec.EncodeBytes(response)
	}

	return nil, errors.NewInvalidMessageError(fmt.Sprintf("unknown method: %s", method), nil)
}

// handleStreamRequest processes a streaming request.
func (l *LocalAgent) handleStreamRequest(ctx context.Context, conn net.Conn, request *codec.Envelope) {
	if request.Type != codec.TypeRequest {
		l.sendError(conn, request.ID, "INVALID_MESSAGE",
			fmt.Sprintf("expected 'request' but got '%s'", request.Type), nil)
		return
	}

	method, ok := request.Payload["method"].(string)
	if !ok || method != "stream" {
		l.sendError(conn, request.ID, "INVALID_MESSAGE",
			fmt.Sprintf("expected 'stream' but got '%s'", method), nil)
		return
	}

	// Decode input message
	messageData, ok := request.Payload["message"].(map[string]interface{})
	if !ok {
		l.sendError(conn, request.ID, "INVALID_MESSAGE", "invalid message format", nil)
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
		l.sendError(conn, request.ID, "INVALID_MESSAGE", err.Error(), nil)
		return
	}

	// Check if agent supports streaming
	streamingAgent, ok := l.agent.(agenkit.StreamingAgent)
	if !ok {
		l.sendError(conn, request.ID, "NOT_IMPLEMENTED", "agent does not support streaming", nil)
		return
	}

	// Stream through agent
	messageChan, errorChan := streamingAgent.Stream(ctx, inputMessage)

	// Track channel closures
	messageChanClosed := false
	errorChanClosed := false

	for {
		select {
		case chunk, ok := <-messageChan:
			if !ok {
				// Message channel closed
				messageChanClosed = true
				if errorChanClosed {
					// Both channels closed - stream complete
					endEnv := codec.CreateStreamEndEnvelope(request.ID)
					endBytes, _ := codec.EncodeBytes(endEnv)
					l.sendFramed(conn, endBytes)
					return
				}
				// Set messageChan to nil to disable this case
				messageChan = nil
				continue
			}

			// Send chunk
			chunkEnv := codec.CreateStreamChunkEnvelope(request.ID, codec.EncodeMessage(chunk))
			chunkBytes, err := codec.EncodeBytes(chunkEnv)
			if err != nil {
				log.Printf("Error encoding stream chunk: %v\n", err)
				return
			}

			if err := l.sendFramed(conn, chunkBytes); err != nil {
				log.Printf("Error sending stream chunk: %v\n", err)
				return
			}

		case err, ok := <-errorChan:
			if ok && err != nil {
				l.sendError(conn, request.ID, "STREAM_ERROR", err.Error(), nil)
				return
			}
			if !ok {
				// Error channel closed
				errorChanClosed = true
				if messageChanClosed {
					// Both channels closed - stream complete
					endEnv := codec.CreateStreamEndEnvelope(request.ID)
					endBytes, _ := codec.EncodeBytes(endEnv)
					l.sendFramed(conn, endBytes)
					return
				}
				// Set errorChan to nil to disable this case
				errorChan = nil
				continue
			}

		case <-ctx.Done():
			l.sendError(conn, request.ID, "CANCELLED", "context cancelled", nil)
			return
		}
	}
}

// sendFramed sends a framed message over the connection.
func (l *LocalAgent) sendFramed(conn net.Conn, data []byte) error {
	// Write length prefix (4 bytes, big-endian)
	length := uint32(len(data))
	if err := binary.Write(conn, binary.BigEndian, length); err != nil {
		return err
	}

	// Write payload
	if _, err := conn.Write(data); err != nil {
		return err
	}

	return nil
}

// sendError sends an error response to the client.
func (l *LocalAgent) sendError(conn net.Conn, requestID, errorCode, errorMessage string, details map[string]interface{}) {
	errorEnv := codec.CreateErrorEnvelope(requestID, errorCode, errorMessage, details)
	errorBytes, _ := codec.EncodeBytes(errorEnv)
	l.sendFramed(conn, errorBytes)
}

// isExpectedDisconnect checks if an error is an expected disconnection.
func (l *LocalAgent) isExpectedDisconnect(err error) bool {
	if err == nil {
		return false
	}
	// Check for "use of closed network connection" error
	errStr := err.Error()
	return errStr == "use of closed network connection" ||
		// Also check if server is shutting down
		!l.running
}
