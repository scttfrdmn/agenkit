package transport

import (
	"bufio"
	"bytes"
	"context"
	"fmt"
	"io"
	"net/http"
	"strings"
	"sync"

	"github.com/agenkit/agenkit-go/adapter/codec"
	"github.com/agenkit/agenkit-go/adapter/errors"
)

// HTTPTransport implements transport over HTTP.
type HTTPTransport struct {
	baseURL string
	client  *http.Client
	mu      sync.Mutex

	// For non-streaming responses
	pendingResponse []byte

	// For streaming responses
	streamReader *bufio.Reader
	streamConn   io.ReadCloser
}

// NewHTTPTransport creates a new HTTP transport.
func NewHTTPTransport(baseURL string) *HTTPTransport {
	// Ensure base URL doesn't end with /
	baseURL = strings.TrimRight(baseURL, "/")

	return &HTTPTransport{
		baseURL: baseURL,
		client:  &http.Client{},
	}
}

// Connect establishes connection to HTTP endpoint.
// For HTTP, this is a no-op as connections are per-request.
func (t *HTTPTransport) Connect(ctx context.Context) error {
	// Test connectivity by making a HEAD request
	req, err := http.NewRequestWithContext(ctx, "HEAD", t.baseURL+"/health", nil)
	if err != nil {
		return errors.NewConnectionError(fmt.Sprintf("failed to create request to %s", t.baseURL), err)
	}

	resp, err := t.client.Do(req)
	if err != nil {
		return errors.NewConnectionError(fmt.Sprintf("failed to connect to %s", t.baseURL), err)
	}
	defer resp.Body.Close()

	// Any response means server is reachable
	return nil
}

// SendFramed sends a request over HTTP and receives the response.
// For HTTP, this sends a POST request to /process endpoint.
func (t *HTTPTransport) SendFramed(ctx context.Context, data []byte) error {
	t.mu.Lock()
	defer t.mu.Unlock()

	// Decode the envelope to determine the method
	envelope, err := codec.DecodeBytes(data)
	if err != nil {
		return errors.NewConnectionError("failed to decode request", err)
	}

	method, ok := envelope.Payload["method"].(string)
	if !ok {
		return errors.NewInvalidMessageError("missing method in payload", nil)
	}

	var endpoint string
	switch method {
	case "process":
		endpoint = "/process"
	case "stream":
		endpoint = "/stream"
	default:
		return errors.NewInvalidMessageError(fmt.Sprintf("unsupported method: %s", method), nil)
	}

	// Create HTTP request
	req, err := http.NewRequestWithContext(ctx, "POST", t.baseURL+endpoint, bytes.NewReader(data))
	if err != nil {
		return errors.NewConnectionError("failed to create HTTP request", err)
	}

	req.Header.Set("Content-Type", "application/json")

	// For streaming requests, we need to keep the response body open
	if method == "stream" {
		req.Header.Set("Accept", "text/event-stream")

		resp, err := t.client.Do(req)
		if err != nil {
			return errors.NewConnectionError("failed to send HTTP request", err)
		}

		if resp.StatusCode != http.StatusOK {
			defer resp.Body.Close()
			body, _ := io.ReadAll(resp.Body)
			return errors.NewConnectionError(fmt.Sprintf("HTTP error %d: %s", resp.StatusCode, string(body)), nil)
		}

		// Keep connection open for streaming
		t.streamConn = resp.Body
		t.streamReader = bufio.NewReader(resp.Body)
		return nil
	}

	// For non-streaming, send request and store response
	resp, err := t.client.Do(req)
	if err != nil {
		return errors.NewConnectionError("failed to send HTTP request", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return errors.NewConnectionError(fmt.Sprintf("HTTP error %d: %s", resp.StatusCode, string(body)), nil)
	}

	// Read and store the response for ReceiveFramed
	t.pendingResponse, err = io.ReadAll(resp.Body)
	if err != nil {
		return errors.NewConnectionError("failed to read HTTP response", err)
	}

	return nil
}

// ReceiveFramed receives a response over HTTP.
// For HTTP, this reads the response body.
func (t *HTTPTransport) ReceiveFramed(ctx context.Context) ([]byte, error) {
	t.mu.Lock()
	defer t.mu.Unlock()

	// If we're in streaming mode, read SSE events
	if t.streamReader != nil {
		return t.readSSEEvent()
	}

	// For non-streaming, return the pending response
	if t.pendingResponse != nil {
		response := t.pendingResponse
		t.pendingResponse = nil
		return response, nil
	}

	return nil, errors.NewConnectionError("no pending response", nil)
}

// readSSEEvent reads a single Server-Sent Event from the stream.
func (t *HTTPTransport) readSSEEvent() ([]byte, error) {
	var eventData []byte

	for {
		line, err := t.streamReader.ReadBytes('\n')
		if err != nil {
			if err == io.EOF {
				// Clean up stream
				if t.streamConn != nil {
					t.streamConn.Close()
					t.streamConn = nil
					t.streamReader = nil
				}
				return nil, errors.NewConnectionError("stream ended", io.EOF)
			}
			return nil, errors.NewConnectionError("failed to read SSE event", err)
		}

		line = bytes.TrimSpace(line)

		// Empty line signals end of event
		if len(line) == 0 {
			if len(eventData) > 0 {
				return eventData, nil
			}
			continue
		}

		// Parse SSE line
		if bytes.HasPrefix(line, []byte("data: ")) {
			data := bytes.TrimPrefix(line, []byte("data: "))
			eventData = append(eventData, data...)
		}
		// Ignore other SSE fields (id:, event:, retry:)
	}
}

// Close closes the HTTP connection.
func (t *HTTPTransport) Close() error {
	t.mu.Lock()
	defer t.mu.Unlock()

	if t.streamConn != nil {
		err := t.streamConn.Close()
		t.streamConn = nil
		t.streamReader = nil
		return err
	}
	return nil
}

// IsConnected returns whether the transport is connected.
// For HTTP, we consider it always connected if client is initialized.
func (t *HTTPTransport) IsConnected() bool {
	return t.client != nil
}
