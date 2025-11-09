// Package remote provides the client-side proxy for remote agents.
package remote

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/agenkit/agenkit-go/adapter/codec"
	"github.com/agenkit/agenkit-go/adapter/errors"
	"github.com/agenkit/agenkit-go/adapter/transport"
	"github.com/agenkit/agenkit-go/agenkit"
)

// RemoteAgent is a client-side proxy for a remote agent.
// It implements the Agent interface and forwards all calls to a remote agent
// over the protocol adapter.
type RemoteAgent struct {
	name      string
	endpoint  string
	transport transport.Transport
	timeout   time.Duration
	connected bool
	mu        sync.Mutex // Serialize requests on same connection
}

// NewRemoteAgent creates a new remote agent client.
//
// Args:
//   - name: Name of the remote agent
//   - endpoint: Endpoint URL (e.g., "unix:///tmp/agent.sock" or "tcp://host:port")
//   - timeout: Request timeout (0 for default 30s)
func NewRemoteAgent(name, endpoint string, timeout time.Duration) (*RemoteAgent, error) {
	if endpoint == "" {
		return nil, fmt.Errorf("endpoint must be provided")
	}

	trans, err := transport.ParseEndpoint(endpoint)
	if err != nil {
		return nil, err
	}

	if timeout == 0 {
		timeout = 30 * time.Second
	}

	return &RemoteAgent{
		name:      name,
		endpoint:  endpoint,
		transport: trans,
		timeout:   timeout,
		connected: false,
	}, nil
}

// NewRemoteAgentWithTransport creates a new remote agent client with a custom transport.
func NewRemoteAgentWithTransport(name string, trans transport.Transport, timeout time.Duration) *RemoteAgent {
	if timeout == 0 {
		timeout = 30 * time.Second
	}

	return &RemoteAgent{
		name:      name,
		transport: trans,
		timeout:   timeout,
		connected: false,
	}
}

// ensureConnected ensures the transport is connected.
func (r *RemoteAgent) ensureConnected(ctx context.Context) error {
	if !r.connected {
		if err := r.transport.Connect(ctx); err != nil {
			return err
		}
		r.connected = true
	}
	return nil
}

// Name returns the agent name.
func (r *RemoteAgent) Name() string {
	return r.name
}

// Process processes a message through the remote agent.
func (r *RemoteAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	if err := r.ensureConnected(ctx); err != nil {
		return nil, err
	}

	// Create request envelope
	payload := map[string]interface{}{
		"message": codec.EncodeMessage(message),
	}
	request := codec.CreateRequestEnvelope("process", r.name, payload)

	// Serialize requests on same connection
	r.mu.Lock()
	defer r.mu.Unlock()

	// Create timeout context
	timeoutCtx, cancel := context.WithTimeout(ctx, r.timeout)
	defer cancel()

	// Send request
	requestBytes, err := codec.EncodeBytes(request)
	if err != nil {
		return nil, fmt.Errorf("failed to encode request: %w", err)
	}

	if err := r.transport.SendFramed(timeoutCtx, requestBytes); err != nil {
		return nil, err
	}

	// Receive response
	responseBytes, err := r.transport.ReceiveFramed(timeoutCtx)
	if err != nil {
		if ctx.Err() == context.DeadlineExceeded {
			return nil, errors.NewAgentTimeoutError(r.name, r.timeout.Seconds())
		}
		return nil, err
	}

	response, err := codec.DecodeBytes(responseBytes)
	if err != nil {
		return nil, err
	}

	// Handle response
	if response.Type == codec.TypeError {
		payload := response.Payload
		errorMessage, _ := payload["error_message"].(string)
		errorDetails, _ := payload["error_details"].(map[string]interface{})
		return nil, errors.NewRemoteExecutionError(r.name, errorMessage, errorDetails)
	}

	if response.Type != codec.TypeResponse {
		return nil, errors.NewInvalidMessageError(
			fmt.Sprintf("expected 'response' but got '%s'", response.Type),
			map[string]interface{}{"response": response},
		)
	}

	// Decode message
	messageData, ok := response.Payload["message"].(map[string]interface{})
	if !ok {
		return nil, errors.NewInvalidMessageError("invalid message format in response", nil)
	}

	// Convert map to MessageData
	msgData := codec.MessageData{
		Role:      messageData["role"].(string),
		Content:   messageData["content"].(string),
		Metadata:  messageData["metadata"].(map[string]interface{}),
		Timestamp: messageData["timestamp"].(string),
	}

	return codec.DecodeMessage(msgData)
}

// Stream streams responses from the remote agent.
func (r *RemoteAgent) Stream(ctx context.Context, message *agenkit.Message) (<-chan *agenkit.Message, <-chan error) {
	messageChan := make(chan *agenkit.Message)
	errorChan := make(chan error, 1)

	go func() {
		defer close(messageChan)
		defer close(errorChan)

		if err := r.ensureConnected(ctx); err != nil {
			errorChan <- err
			return
		}

		// Create stream request envelope
		payload := map[string]interface{}{
			"message": codec.EncodeMessage(message),
		}
		request := codec.CreateRequestEnvelope("stream", r.name, payload)

		// Serialize requests on same connection
		r.mu.Lock()
		defer r.mu.Unlock()

		// Create timeout context
		timeoutCtx, cancel := context.WithTimeout(ctx, r.timeout)
		defer cancel()

		// Send request
		requestBytes, err := codec.EncodeBytes(request)
		if err != nil {
			errorChan <- fmt.Errorf("failed to encode request: %w", err)
			return
		}

		if err := r.transport.SendFramed(timeoutCtx, requestBytes); err != nil {
			errorChan <- err
			return
		}

		// Receive stream chunks
		for {
			responseBytes, err := r.transport.ReceiveFramed(timeoutCtx)
			if err != nil {
				if ctx.Err() == context.DeadlineExceeded {
					errorChan <- errors.NewAgentTimeoutError(r.name, r.timeout.Seconds())
				} else {
					errorChan <- err
				}
				return
			}

			response, err := codec.DecodeBytes(responseBytes)
			if err != nil {
				errorChan <- err
				return
			}

			// Handle response type
			switch response.Type {
			case codec.TypeError:
				payload := response.Payload
				errorMessage, _ := payload["error_message"].(string)
				errorDetails, _ := payload["error_details"].(map[string]interface{})
				errorChan <- errors.NewRemoteExecutionError(r.name, errorMessage, errorDetails)
				return

			case codec.TypeStreamChunk:
				// Decode chunk message
				messageData, ok := response.Payload["message"].(map[string]interface{})
				if !ok {
					errorChan <- errors.NewInvalidMessageError("invalid message format in stream chunk", nil)
					return
				}

				// Convert map to MessageData
				msgData := codec.MessageData{
					Role:      messageData["role"].(string),
					Content:   messageData["content"].(string),
					Metadata:  messageData["metadata"].(map[string]interface{}),
					Timestamp: messageData["timestamp"].(string),
				}

				chunk, err := codec.DecodeMessage(msgData)
				if err != nil {
					errorChan <- err
					return
				}

				select {
				case messageChan <- chunk:
				case <-ctx.Done():
					errorChan <- ctx.Err()
					return
				}

			case codec.TypeStreamEnd:
				// Stream complete
				return

			default:
				errorChan <- errors.NewInvalidMessageError(
					fmt.Sprintf("expected 'stream_chunk' or 'stream_end' but got '%s'", response.Type),
					map[string]interface{}{"response": response},
				)
				return
			}
		}
	}()

	return messageChan, errorChan
}

// Capabilities returns the agent capabilities.
// Note: Capability querying not yet implemented in v0.1.0.
func (r *RemoteAgent) Capabilities() []string {
	return []string{}
}

// Close closes the connection to the remote agent.
func (r *RemoteAgent) Close() error {
	if r.connected {
		err := r.transport.Close()
		r.connected = false
		return err
	}
	return nil
}
