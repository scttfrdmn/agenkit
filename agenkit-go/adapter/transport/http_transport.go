package transport

import (
	"bufio"
	"bytes"
	"context"
	"crypto/tls"
	"fmt"
	"io"
	"net"
	"net/http"
	"strings"
	"sync"

	"github.com/quic-go/quic-go/http3"
	"golang.org/x/net/http2"

	"github.com/agenkit/agenkit-go/adapter/codec"
	"github.com/agenkit/agenkit-go/adapter/errors"
)

// HTTPVersion represents the HTTP protocol version.
type HTTPVersion int

const (
	// HTTP1 uses HTTP/1.1
	HTTP1 HTTPVersion = iota
	// HTTP2 uses HTTP/2 (h2 for TLS, h2c for cleartext)
	HTTP2
	// HTTP3 uses HTTP/3 over QUIC
	HTTP3
)

// HTTPTransport implements transport over HTTP with support for HTTP/1.1, HTTP/2, and HTTP/3.
type HTTPTransport struct {
	baseURL string
	version HTTPVersion
	client  *http.Client
	mu      sync.Mutex

	// For non-streaming responses
	pendingResponse []byte

	// For streaming responses
	streamReader *bufio.Reader
	streamConn   io.ReadCloser
}

// NewHTTPTransport creates a new HTTP transport with auto-detected protocol version.
// URL schemes:
//   - http:// or https:// -> HTTP/1.1 (with automatic HTTP/2 upgrade for HTTPS)
//   - h2c:// -> HTTP/2 cleartext
//   - h3:// -> HTTP/3 over QUIC
func NewHTTPTransport(baseURL string) *HTTPTransport {
	// Ensure base URL doesn't end with /
	baseURL = strings.TrimRight(baseURL, "/")

	// Detect protocol version from URL scheme
	version := HTTP1
	normalizedURL := baseURL

	if strings.HasPrefix(baseURL, "h2c://") {
		version = HTTP2
		normalizedURL = "http://" + baseURL[6:]
	} else if strings.HasPrefix(baseURL, "h3://") {
		version = HTTP3
		normalizedURL = "https://" + baseURL[5:]
	}

	return newHTTPTransportWithVersion(normalizedURL, version)
}

// newHTTPTransportWithVersion creates an HTTP transport with explicit protocol version.
func newHTTPTransportWithVersion(baseURL string, version HTTPVersion) *HTTPTransport {
	var client *http.Client

	switch version {
	case HTTP2:
		// HTTP/2 Cleartext (h2c) support
		transport := &http.Transport{
			DialContext: func(ctx context.Context, network, addr string) (net.Conn, error) {
				return (&net.Dialer{}).DialContext(ctx, network, addr)
			},
		}
		http2.ConfigureTransport(transport)

		client = &http.Client{
			Transport: &h2cTransport{transport: transport},
		}

	case HTTP3:
		// HTTP/3 over QUIC
		client = &http.Client{
			Transport: &http3.Transport{
				TLSClientConfig: &tls.Config{
					// For benchmarks and local testing with self-signed certificates
					// Production deployments should use proper CA-signed certificates
					InsecureSkipVerify: true,
				},
			},
		}

	default:
		// HTTP/1.1 (with automatic HTTP/2 upgrade for HTTPS)
		transport := &http.Transport{
			TLSClientConfig: &tls.Config{
				InsecureSkipVerify: false,
			},
		}
		// Enable HTTP/2 support for HTTPS connections
		http2.ConfigureTransport(transport)

		client = &http.Client{
			Transport: transport,
		}
	}

	return &HTTPTransport{
		baseURL: baseURL,
		version: version,
		client:  client,
	}
}

// h2cTransport wraps an http.Transport to force HTTP/2 cleartext.
type h2cTransport struct {
	transport *http.Transport
}

func (t *h2cTransport) RoundTrip(req *http.Request) (*http.Response, error) {
	req.URL.Scheme = "http"
	req.Proto = "HTTP/2.0"
	req.ProtoMajor = 2
	req.ProtoMinor = 0
	return t.transport.RoundTrip(req)
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
